import copy
import random
import unittest

from domino.game import Game
from domino.player import Player
from tools import arena
from tools.play_montecarlo import (BIT, INDEX, MonteCarloBot, ends_after, solve)


def tiles(mask):
    return sorted(t for t, i in INDEX.items() if mask & BIT[i])


def mask(*ts):
    return sum(BIT[INDEX[t]] for t in ts)


class FogGame:
    """Shows a bot nothing but game.state(for_seat): no other attribute of the real game."""

    def __init__(self, game):
        self._game = game
        self.state_calls = []

    def state(self, for_seat=None):
        self.state_calls.append(for_seat)
        return self._game.state(for_seat=for_seat)

    def __getattr__(self, name):
        raise AssertionError(f"the bot looked at game.{name}")


def play_full_game(bot_seat, bot, rng, fog=True):
    """Bot against a random legal player. Returns the finished game."""
    game = Game([Player(id="0", name="a"), Player(id="1", name="b")])
    view = FogGame(game) if fog else game
    while not game.finished:
        seat = game.current_seat
        moves = game.legal_moves(seat)
        if moves:
            if seat == bot_seat:
                move = bot.choose(view, moves)
                if move not in moves:
                    raise AssertionError(f"bot returned {move}, not one of {moves}")
            else:
                move = rng.choice(moves)
            game.play(seat, *move)
        elif game.can_draw(seat):
            game.draw(seat)
        else:
            game.pass_turn(seat)
    return game


def brute_force(game):
    """Value for the player to move, found by trying every line with the real Game rules."""
    seat = game.current_seat
    moves = game.legal_moves(seat)
    best = -2
    for move in (moves or [None]):
        g = copy.deepcopy(game)
        if move:
            g.play(seat, *move)
        else:
            g.pass_turn(seat)
        if g.finished:
            value = 0 if g.winner is None else (1 if g.winner == seat else -1)
        else:
            value = -brute_force(g)
        best = max(best, value)
    return best


class TestSolver(unittest.TestCase):
    def test_going_out_wins(self):
        self.assertEqual(solve(mask((1, 2)), mask((3, 4)), 1, 5, 0, 0, {}), 1)

    def test_blocked_game_lowest_dots_wins(self):
        # nobody can play any tile on ends 1|2
        self.assertEqual(solve(mask((0, 0)), mask((6, 6)), 1, 2, 0, 0, {}), 1)
        self.assertEqual(solve(mask((6, 6)), mask((0, 0)), 1, 2, 0, 0, {}), -1)
        self.assertEqual(solve(mask((3, 3)), mask((0, 6)), 1, 2, 0, 0, {}), 0)

    def test_a_forced_win(self):
        # ends 3|3. (3,4) then (4,4) goes out; the other player's (3,5) cannot stop it or go out first
        self.assertEqual(solve(mask((3, 4), (4, 4)), mask((3, 5), (5, 5)), 3, 3, 0, 0, {}), 1)

    def test_matches_a_brute_force_search_with_the_real_rules(self):
        rng = random.Random(2024)
        for _ in range(250):
            all_tiles = sorted(INDEX)
            board_tile = rng.choice(all_tiles)
            rest = [t for t in all_tiles if t != board_tile]
            n = rng.randint(2, 5)
            mine, theirs = rng.sample(rest, n), None
            others = [t for t in rest if t not in mine]
            theirs = rng.sample(others, rng.randint(2, 5))
            game = Game.quick_start()
            game.players[0].hand, game.players[1].hand = list(mine), list(theirs)
            game.boneyard = []
            game.board = [board_tile]
            game.turns.current = 0
            left, right = board_tile
            expected = brute_force(game)
            got = solve(mask(*mine), mask(*theirs), left, right, 0, 0, {})
            self.assertEqual(got, expected, f"mine={mine} theirs={theirs} board={board_tile}")


class TestInference(unittest.TestCase):
    def learn(self, bot, ends, draws, played, board_len=5):
        """Feed the bot one opponent turn as the table would show it."""
        bot._last = {"board_len": board_len, "hand_len": 4, "yard": 6, "ends": ends}
        bot._learn(board_len + (1 if played else 0), 6 - draws, 4)

    def test_pass_without_drawing(self):
        bot = MonteCarloBot(1)
        self.learn(bot, (2, 5), draws=0, played=False)
        self.assertEqual(bot.opponent_lacks, {2, 5})

    def test_drew_and_played_keeps_old_knowledge(self):
        bot = MonteCarloBot(1)
        bot.opponent_lacks = {0}
        self.learn(bot, (2, 5), draws=1, played=True)
        self.assertEqual(bot.opponent_lacks, {0, 2, 5})

    def test_kept_tiles_reset_knowledge_to_the_ends(self):
        bot = MonteCarloBot(1)
        bot.opponent_lacks = {0}
        self.learn(bot, (2, 5), draws=3, played=True)      # drew 3, played one, kept 2
        self.assertEqual(bot.opponent_lacks, {2, 5})

    def test_played_without_drawing_learns_nothing(self):
        bot = MonteCarloBot(1)
        bot.opponent_lacks = {0}
        self.learn(bot, (2, 5), draws=0, played=True)
        self.assertEqual(bot.opponent_lacks, {0})

    def test_unexpected_table_change_forgets_safely(self):
        bot = MonteCarloBot(1)
        bot.opponent_lacks = {0, 3}
        bot._last = {"board_len": 5, "hand_len": 4, "yard": 6, "ends": (2, 5)}
        bot._learn(8, 6, 4)                                # three tiles appeared: we missed turns
        self.assertEqual(bot.opponent_lacks, set())


class TestBot(unittest.TestCase):
    def test_ends_after(self):
        self.assertEqual(ends_after(None, (3, 5), "R"), (3, 5))
        self.assertEqual(ends_after((1, 3), (3, 5), "R"), (1, 5))
        self.assertEqual(ends_after((1, 3), (1, 4), "L"), (4, 3))
        self.assertEqual(ends_after((2, 2), (2, 2), "L"), (2, 2))

    def test_always_legal_and_only_reads_state(self):
        rng = random.Random(11)
        for seed in range(12):
            random.seed(seed)
            bot_seat = seed % 2
            bot = MonteCarloBot(bot_seat, samples=12, seed=seed)
            game = play_full_game(bot_seat, bot, rng)
            self.assertTrue(game.finished)

    def test_only_asks_for_its_own_seat(self):
        random.seed(3)
        game = Game([Player(id="0", name="a"), Player(id="1", name="b")])
        bot = MonteCarloBot(game.current_seat, samples=5, seed=1)
        view = FogGame(game)
        moves = game.legal_moves(game.current_seat)
        bot.choose(view, moves)
        self.assertEqual(set(view.state_calls), {game.current_seat})

    def test_never_sees_the_opponent_hand(self):
        """Changing the opponent's hidden tiles (same counts) cannot change what the bot plays."""
        random.seed(5)
        game = Game([Player(id="0", name="a"), Player(id="1", name="b")])
        seat = game.current_seat
        while not game.board:                       # play the opening so there is a real choice
            game.play(game.current_seat, *game.legal_moves(game.current_seat)[0])
        seat = game.current_seat
        moves = game.legal_moves(seat)
        if len(moves) < 2:
            self.skipTest("this deal has no choice to make")
        pick_a = MonteCarloBot(seat, samples=30, seed=9).choose(FogGame(game), moves)
        other = 1 - seat
        mine = set(game.players[seat].hand)
        unseen = [t for t in INDEX if t not in mine and t not in {tuple(sorted(b)) for b in game.board}]
        random.Random(1).shuffle(unseen)
        n = len(game.players[other].hand)
        game.players[other].hand = unseen[:n]
        game.boneyard = unseen[n:]
        pick_b = MonteCarloBot(seat, samples=30, seed=9).choose(FogGame(game), moves)
        self.assertEqual(pick_a, pick_b)

    def test_forced_move_is_returned_without_thinking(self):
        random.seed(1)
        game = Game([Player(id="0", name="a"), Player(id="1", name="b")])
        bot = MonteCarloBot(game.current_seat, samples=1000000)   # would take forever if it searched
        moves = game.legal_moves(game.current_seat)
        self.assertEqual(len(moves), 1)
        self.assertEqual(bot.choose(FogGame(game), moves), moves[0])

    def test_same_seed_same_game(self):
        def run():
            random.seed(21)
            bot = MonteCarloBot(0, samples=10, seed=4)
            game = play_full_game(0, bot, random.Random(2))
            return game.board, game.winner
        self.assertEqual(run(), run())

    def test_time_limit_mode(self):
        random.seed(8)
        bot = MonteCarloBot(0, time_limit=0.02, seed=2)
        game = play_full_game(0, bot, random.Random(3))
        self.assertTrue(game.finished)


class TestStrength(unittest.TestCase):
    """Fixed seeds, so these are repeatable, not lucky."""

    def test_beats_the_simple_bot(self):
        r = arena.run("montecarlo", "heavy", 80, seed=100, opts_a={"samples": 40})
        self.assertGreater(r["a"], r["b"])

    def test_arena_counts_every_game(self):
        r = arena.run("scoring", "heavy", 30, seed=1)
        self.assertEqual(r["a"] + r["b"] + r["tie"], 30)


if __name__ == "__main__":
    unittest.main()
