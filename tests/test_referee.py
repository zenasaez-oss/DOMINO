"""The referee: a bot that misbehaves loses the game, and nothing else breaks."""
import sys
import time
import unittest

from domino.bots import LEVELS, Bot, GreedyBot
from domino.game import Game
from domino.referee import FAULTS, BotFault, ask_bot, play_match


class Honest(GreedyBot):
    pass


class Crashes(GreedyBot):
    def choose(self, view, moves):
        raise ZeroDivisionError("bug in the bot")


class ReturnsNothing(GreedyBot):
    def choose(self, view, moves):
        return None


class ReturnsAWrongMove(GreedyBot):
    def choose(self, view, moves):
        return ((9, 9), "R")


class Hangs(GreedyBot):
    """Busy for 2 s, far past the time limit. (A truly endless loop would also lose, but Python
    can't stop a thread: it would keep using the CPU until the tests end and slow them all down.)"""

    def choose(self, view, moves):
        started = time.perf_counter()
        while time.perf_counter() - started < 2:
            pass
        return moves[0]


class TooSlow(GreedyBot):
    def choose(self, view, moves):
        time.sleep(1)
        return moves[0]


class ExitsPython(GreedyBot):
    def choose(self, view, moves):
        sys.exit("bye")


class CrashesWhenCreated(GreedyBot):
    def __init__(self, seat):
        raise RuntimeError("can't even start")


class CreateReturnsJunk(GreedyBot):
    @classmethod
    def create(cls, seat, seed=None, **options):
        return "not a bot"


class CrashesWhenWatching(GreedyBot):
    def observe_opponent_turn(self, ends, draws, played):
        raise ValueError("bug while watching")


BAD_BOTS = [
    (Crashes, "error", "ZeroDivisionError"),
    (ReturnsNothing, "illegal", "None"),
    (ReturnsAWrongMove, "illegal", "(9, 9)"),
    (Hangs, "timeout", "no answer"),
    (TooSlow, "timeout", "no answer"),
    (ExitsPython, "error", "SystemExit"),
    (CrashesWhenCreated, "error", "can't even start"),
    (CreateReturnsJunk, "error", "not a Bot"),
]


class TestFairGames(unittest.TestCase):
    def test_a_normal_game_ends_normally(self):
        result = play_match(Honest, Honest, seed=1)
        self.assertIn(result.end_reason, ("domino", "blocked"))
        self.assertIsNone(result.fault)
        self.assertEqual(result.names, ("Greedy", "Greedy"))

    def test_the_same_seed_replays_the_same_game(self):
        for level in ("easy", "medium", "hard"):
            with self.subTest(level=level):
                bot = LEVELS[level]
                options = ({"samples": 8}, {"samples": 8}) if level == "hard" else ({}, {})
                first = play_match(bot, Honest, seed=11, options=options)
                again = play_match(bot, Honest, seed=11, options=options)
                self.assertEqual(first.history, again.history)

    def test_different_seeds_give_different_games(self):
        histories = {repr(play_match(Honest, Honest, seed=s).history) for s in range(5)}
        self.assertGreater(len(histories), 1)

    def test_all_our_bots_finish_without_faults(self):
        for level, bot in LEVELS.items():
            with self.subTest(level=level):
                options = {"samples": 5} if level in ("hard", "superhard") else {}
                result = play_match(bot, Honest, seed=3, time_limit=10, options=(options, {}))
                self.assertIsNone(result.fault)


class TestBotsThatBreakTheRules(unittest.TestCase):
    def test_a_bot_that_breaks_the_rules_loses_and_the_other_wins(self):
        for bad, reason, detail in BAD_BOTS:
            for seat in (0, 1):
                with self.subTest(bot=bad.__name__, seat=seat):
                    bots = (bad, Honest) if seat == 0 else (Honest, bad)
                    started = time.perf_counter()
                    result = play_match(*bots, seed=seat, time_limit=0.3)
                    self.assertLess(time.perf_counter() - started, 5)    # nobody can hold the game up
                    self.assertEqual(result.end_reason, reason)
                    self.assertEqual(result.winner, 1 - seat)
                    self.assertEqual(result.fault["seat"], seat)
                    self.assertIn(detail, result.fault["detail"])
                    self.assertEqual(result.history[-1]["action"], "forfeit")

    def test_a_bot_that_crashes_while_watching_the_opponent_loses(self):
        for seed in range(10):                 # find a game where the opponent gets to move
            result = play_match(Honest, CrashesWhenWatching, seed=seed)
            if result.fault:
                self.assertEqual(result.fault["seat"], 1)
                self.assertEqual(result.end_reason, "error")
                self.assertEqual(result.winner, 0)
                return
        self.fail("the watching bot never got to watch")

    def test_every_fault_reason_is_known(self):
        self.assertEqual(set(FAULTS), {"error", "illegal", "timeout"})


class TestAskBot(unittest.TestCase):
    def test_returns_a_legal_move(self):
        game = Game.quick_start()
        seat = game.current_seat
        moves = game.legal_moves(seat)
        self.assertIn(ask_bot(Honest(seat), seat, game.view(seat), moves), moves)

    def test_raises_a_bot_fault_naming_the_seat_and_reason(self):
        game = Game.quick_start()
        seat = game.current_seat
        with self.assertRaises(BotFault) as caught:
            ask_bot(Crashes(seat), seat, game.view(seat), game.legal_moves(seat))
        self.assertEqual((caught.exception.seat, caught.exception.reason), (seat, "error"))

    def test_without_a_time_limit_it_uses_no_thread(self):
        # the website runs in Pyodide, which can't start threads: time_limit=None must not need one
        import threading
        original = threading.Thread.start
        threading.Thread.start = lambda self: (_ for _ in ()).throw(RuntimeError("no threads here"))
        try:
            game = Game.quick_start()
            seat = game.current_seat
            ask_bot(Honest(seat), seat, game.view(seat), game.legal_moves(seat))
        finally:
            threading.Thread.start = original


class TestForfeit(unittest.TestCase):
    def test_forfeit_ends_the_game_for_the_other_seat(self):
        game = Game.quick_start()
        game.forfeit(0, "timeout")
        self.assertTrue(game.finished)
        self.assertEqual((game.winner, game.end_reason), (1, "timeout"))
        self.assertEqual(game.history[-1], {"seat": 0, "action": "forfeit", "reason": "timeout"})

    def test_cannot_forfeit_a_finished_game(self):
        game = Game.quick_start()
        game.forfeit(0, "error")
        with self.assertRaises(ValueError):
            game.forfeit(1, "error")

    def test_an_incomplete_bot_loses_instead_of_breaking_the_game(self):
        result = play_match(Bot, Honest)   # Bot itself is abstract: creating it fails
        self.assertEqual((result.winner, result.end_reason), (1, "error"))
        self.assertIn("abstract", result.fault["detail"])
