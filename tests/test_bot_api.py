import json
import unittest

from domino.bots import LEVELS, Bot, IllegalMove, check_move
from domino.game import Game
from web import session


class Complete(Bot):
    @classmethod
    def get_name(cls):
        return "Complete"

    @classmethod
    def get_authors(cls):
        return ["Tester"]

    @classmethod
    def get_description(cls):
        return "Plays the first legal move."

    def choose(self, game, moves):
        return moves[0]


class NoChoose(Bot):
    @classmethod
    def get_name(cls):
        return "No choose"

    @classmethod
    def get_authors(cls):
        return ["Tester"]

    @classmethod
    def get_description(cls):
        return "Forgot to write choose."


class NoName(Bot):
    @classmethod
    def get_authors(cls):
        return ["Tester"]

    @classmethod
    def get_description(cls):
        return "Forgot to write get_name."

    def choose(self, game, moves):
        return moves[0]


class TestBotBaseClass(unittest.TestCase):
    def test_the_base_class_itself_cannot_be_created(self):
        with self.assertRaises(TypeError):
            Bot()

    def test_a_complete_bot_can_be_created_and_play(self):
        self.assertEqual(Complete().choose(None, [((6, 6), "R")]), ((6, 6), "R"))

    def test_a_bot_without_choose_is_refused_at_creation(self):
        with self.assertRaises(TypeError) as caught:
            NoChoose()
        self.assertIn("choose", str(caught.exception))

    def test_a_bot_without_its_name_is_refused_at_creation(self):
        with self.assertRaises(TypeError) as caught:
            NoName()
        self.assertIn("get_name", str(caught.exception))

    def test_observing_the_opponent_is_optional(self):
        Complete().observe_opponent_turn((1, 6), 2, True)   # the default does nothing, no error


class TestOurBots(unittest.TestCase):
    def test_every_bot_inherits_from_bot(self):
        for level, bot in LEVELS.items():
            with self.subTest(level=level):
                self.assertTrue(issubclass(bot, Bot))

    def test_identity_is_readable_without_creating_the_bot(self):
        for level, bot in LEVELS.items():
            with self.subTest(level=level):
                self.assertIsInstance(bot.get_name(), str)
                self.assertTrue(bot.get_name().strip())
                authors = bot.get_authors()
                self.assertIsInstance(authors, list)
                self.assertTrue(authors and all(isinstance(a, str) and a.strip() for a in authors))
                self.assertTrue(bot.get_description().strip())

    def test_names_are_unique(self):
        names = [bot.get_name() for bot in LEVELS.values()]
        self.assertEqual(len(names), len(set(names)))


MOVES = [((6, 2), "R"), ((1, 4), "L"), ((1, 6), "L"), ((1, 6), "R")]


class TestWhatABotMustReturn(unittest.TestCase):
    def test_every_legal_move_is_accepted_as_given(self):
        for move in MOVES:
            self.assertEqual(check_move(move, MOVES), move)

    def test_anything_else_is_an_illegal_move(self):
        wrong = [
            None,                     # returned nothing
            ((3, 3), "R"),            # a tile that isn't playable
            ((6, 2), "L"),            # a playable tile on the wrong side
            ((2, 6), "R"),            # the right tile written the other way round
            [(6, 2), "R"],            # a list instead of a tuple
            ([6, 2], "R"),            # the tile as a list
            ((6, 2), "right"),        # the side spelled out
            ((6, 2), "R", "extra"),   # too many parts
            (6, 2),                   # just the tile, no side
            "((6, 2), 'R')",          # text that looks like a move
        ]
        for move in wrong:
            with self.subTest(move=move):
                with self.assertRaises(IllegalMove):
                    check_move(move, MOVES)

    def test_an_illegal_move_is_a_value_error(self):
        # so the website's existing error handling turns it into a message for the page
        self.assertTrue(issubclass(IllegalMove, ValueError))

    def test_on_the_website_an_illegal_bot_move_changes_nothing(self):
        class Garbage(Complete):
            def choose(self, view, moves):
                return None

        for _ in range(20):                       # until the bot is the one to open
            state = json.loads(session.new_game("hard"))
            if state["current_seat"] == session.BOT:
                break
        else:
            self.skipTest("the bot never opened")
        session.current.strong = Garbage()
        before = session.current.to_dict()
        reply = json.loads(session.bot_turn())
        self.assertIn("error", reply)
        self.assertIn("not one of the legal moves", reply["error"])
        self.assertEqual(session.current.to_dict(), before)


if __name__ == "__main__":
    unittest.main()
