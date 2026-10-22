import json
import random
import unittest

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
            first = session.current.strong
            play_random_game("superhard")
            self.assertIs(session.current.strong.style_evidence, first.style_evidence)
        finally:
            session.SUPER_THINK = think

    def test_unknown_level_is_an_error(self):
        self.assertIn("error", json.loads(session.new_game("impossible")))


if __name__ == "__main__":
    unittest.main()
