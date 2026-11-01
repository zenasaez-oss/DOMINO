import json
import random
import unittest
from unittest.mock import patch

from domino.bots import LEVELS, GreedyBot, scan
from web import session
from web.session import BOT, YOU, Session


def play_random_game(level):
    """Play a whole game through the functions the web page calls, picking random moves."""
    state = json.loads(session.new_game(level))
    for _ in range(200):
        if state["finished"]:
            return state
        if state["current_seat"] == BOT:
            state = json.loads(session.bot_turn())
        elif state["my_moves"]:
            (a, b), side = random.choice(state["my_moves"])
            state = json.loads(session.play(a, b, side))
        elif state["can_draw"]:
            state = json.loads(session.draw())
        else:
            state = json.loads(session.pass_turn())
        assert "error" not in state, state
    raise AssertionError("the game did not end")


class TestSession(unittest.TestCase):
    def test_bot_waits_for_the_page_then_hands_the_turn_back(self):
        for _ in range(20):
            s = Session()
            if s.game.current_seat == BOT:
                self.assertEqual(s.game.board, [])  # it hasn't opened yet
                s.run_bot()
            self.assertEqual(s.game.current_seat, YOU)

    def test_bot_turn_does_nothing_on_your_turn(self):
        state = json.loads(session.new_game("easy"))
        if state["current_seat"] == BOT:
            state = json.loads(session.bot_turn())
        again = json.loads(session.bot_turn())
        self.assertEqual(again["board"], state["board"])
        self.assertEqual(again["current_seat"], YOU)

    def test_full_games_end_at_both_levels(self):
        for level in ("easy", "medium"):
            for _ in range(50):
                state = play_random_game(level)
                self.assertTrue(state["finished"])
                self.assertIn(state["end_reason"], ("domino", "blocked"))

    def test_bot_hand_is_hidden_until_the_end(self):
        state = json.loads(session.new_game("medium"))
        self.assertIsNone(state["bot_hand"])
        self.assertEqual(state["my_hand"], [list(t) for t in session.current.game.players[YOU].hand])
        for entry in state["log"]:
            if entry["who"] == "bot" and entry["action"] == "draw":
                self.assertNotIn("tile", entry)

    def test_bot_hand_is_shown_at_the_end(self):
        state = play_random_game("easy")
        self.assertEqual(len(state["bot_hand"]), state["players"][BOT]["tiles_left"])

    def test_illegal_move_is_an_error_and_changes_nothing(self):
        session.new_game("easy")
        before = session.current.to_dict()
        reply = json.loads(session.play(9, 9, "L"))
        self.assertIn("error", reply)
        self.assertEqual(session.current.to_dict(), before)

    def test_only_the_first_play_is_marked_as_opening(self):
        state = play_random_game("easy")
        plays = [e for e in state["log"] if e["action"] == "play"]
        self.assertTrue(plays[0]["opening"])
        self.assertFalse(any(e["opening"] for e in plays[1:]))

    def test_games_take_turns_to_open(self):
        openers = [json.loads(session.new_game("easy"))["current_seat"] for _ in range(6)]
        for before, after in zip(openers, openers[1:]):
            self.assertEqual(after, 1 - before)

    def test_the_opener_opens_with_their_best_double(self):
        for seat in (YOU, BOT):
            s = Session(opener=seat)
            hand = s.game.players[seat].hand
            doubles = [t for t in hand if t[0] == t[1]]
            self.assertEqual(s.game.current_seat, seat)
            self.assertIn(s.game.opening_tile, hand)
            if doubles:
                self.assertEqual(s.game.opening_tile, max(doubles))

    def test_full_games_end_at_hard_levels(self):
        think, session.SUPER_THINK = session.SUPER_THINK, 0.01   # keep the test quick
        try:
            for level in ("hard", "superhard"):
                for _ in range(3):
                    state = play_random_game(level)
                    self.assertTrue(state["finished"])
        finally:
            session.SUPER_THINK = think

    def test_superhard_remembers_your_style_between_games(self):
        think, session.SUPER_THINK = session.SUPER_THINK, 0.01
        try:
            play_random_game("superhard")
            first = session.current.bot
            play_random_game("superhard")
            self.assertIs(session.current.bot.style_evidence, first.style_evidence)
        finally:
            session.SUPER_THINK = think

    def test_unknown_level_is_an_error(self):
        self.assertIn("error", json.loads(session.new_game("impossible")))


class TestEveryBotOnThePage(unittest.TestCase):
    def test_every_bot_in_the_folder_is_listed(self):
        listed = json.loads(session.list_bots())
        found, _ = scan()
        self.assertEqual({b["id"] for b in listed["bots"]}, set(found))
        for bot in listed["bots"]:
            self.assertTrue(bot["name"] and bot["authors"] and bot["description"])

    def test_our_four_come_first_with_their_characters(self):
        bots = json.loads(session.list_bots())["bots"]
        self.assertEqual([b["character"] for b in bots[:4]], list(LEVELS))
        self.assertTrue(all(b["character"] is None for b in bots[4:]))

    def test_a_game_can_be_played_against_any_bot_by_name(self):
        name = LEVELS["medium"].get_name()
        state = play_random_game(name)
        self.assertTrue(state["finished"])
        self.assertEqual(state["bot"], name)
        self.assertEqual(state["character"], "medium")

    def test_a_bot_without_a_character_can_be_played(self):
        class Plain(GreedyBot):
            @classmethod
            def get_name(cls):
                return "Plain"

        with patch.object(session, "scan", return_value=({"Plain": Plain}, [])):
            state = play_random_game("Plain")
        self.assertTrue(state["finished"])
        self.assertIsNone(state["character"])
        self.assertEqual(state["players"][BOT]["name"], "Plain")

    def test_the_chosen_bot_hears_about_your_turns(self):
        heard = []

        class Listener(GreedyBot):
            @classmethod
            def get_name(cls):
                return "Listener"

            def observe_opponent_turn(self, ends, draws, played):
                heard.append(played)

        with patch.object(session, "scan", return_value=({"Listener": Listener}, [])):
            play_random_game("Listener")
        self.assertTrue(heard)

    def test_a_bot_that_cannot_be_built_loses_at_once(self):
        class Broken(GreedyBot):
            @classmethod
            def get_name(cls):
                return "Broken"

            def __init__(self, seat):
                raise RuntimeError("missing file")

        with patch.object(session, "scan", return_value=({"Broken": Broken}, [])):
            state = json.loads(session.new_game("Broken"))
        self.assertTrue(state["finished"])
        self.assertEqual(state["winner"], YOU)
        self.assertEqual(state["end_reason"], "error")
        self.assertEqual(state["bot_turn"][-1]["action"], "forfeit")


class TestTournamentOnThePage(unittest.TestCase):
    def test_a_tournament_plays_one_game_per_step(self):
        names = [LEVELS["easy"].get_name(), LEVELS["medium"].get_name()]
        state = json.loads(session.tournament_start(json.dumps(names), 2, 7))
        self.assertEqual((state["played"], state["total"]), (0, 2))
        state = json.loads(session.tournament_step())
        self.assertEqual(state["played"], 1)
        state = json.loads(session.tournament_step())
        self.assertTrue(state["finished"])
        self.assertEqual(sum(row["played"] for row in state["table"]), 4)
        again = json.loads(session.tournament_step())      # nothing left to play
        self.assertEqual(again["played"], 2)

    def test_one_bot_is_not_a_tournament(self):
        reply = json.loads(session.tournament_start(json.dumps([LEVELS["easy"].get_name()])))
        self.assertIn("error", reply)


if __name__ == "__main__":
    unittest.main()
