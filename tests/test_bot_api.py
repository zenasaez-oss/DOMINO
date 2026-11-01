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

    def test_on_the_website_a_bot_that_breaks_the_rules_loses(self):
        class Garbage(Complete):
            def choose(self, view, moves):
                return None

        class Crashes(Complete):
            def choose(self, view, moves):
                raise RuntimeError("bug in the bot")

        for bot, reason in ((Garbage(1), "illegal"), (Crashes(1), "error")):
            with self.subTest(reason=reason):
                for _ in range(20):                       # until the bot is the one to open
                    state = json.loads(session.new_game("hard"))
                    if state["current_seat"] == session.BOT:
                        break
                else:
                    self.skipTest("the bot never opened")
                session.current.bot = bot
                reply = json.loads(session.bot_turn())
                self.assertNotIn("error", reply)          # no stuck page: the game goes on to its end
                self.assertTrue(reply["finished"])
                self.assertEqual(reply["winner"], session.YOU)
                self.assertEqual(reply["end_reason"], reason)
                self.assertEqual(reply["log"][-1]["action"], "forfeit")
                self.assertEqual(reply["board"], [])     # it never got to play a tile


class TestCreateAndName(unittest.TestCase):
    def test_create_builds_a_bot_for_a_seat(self):
        for level, bot_class in LEVELS.items():
            with self.subTest(level=level):
                bot = bot_class.create(1, seed=3)
                self.assertIsInstance(bot, bot_class)
                self.assertEqual(bot.seat, 1)

    def test_create_passes_options_on(self):
        self.assertEqual(LEVELS["hard"].create(0, seed=1, samples=12).samples, 12)

    def test_same_seed_same_decisions(self):
        game = Game.quick_start()
        seat = game.current_seat
        while len(game.legal_moves(seat)) < 2:            # find a turn with a real choice
            game.play(seat, *game.legal_moves(seat)[0])
            seat = game.current_seat
            if game.finished:
                self.skipTest("no choice in this deal")
        view, moves = game.view(seat), game.legal_moves(seat)
        bot_class = LEVELS["hard"]
        picks = {bot_class.create(seat, seed=42, samples=15).choose(view, moves) for _ in range(3)}
        self.assertEqual(len(picks), 1)

    def test_name_is_get_name_until_renamed(self):
        bot_class = LEVELS["easy"]
        first, second = bot_class.create(0), bot_class.create(1)
        self.assertEqual(first.name, bot_class.get_name())
        second.name = bot_class.get_name() + "#2"
        self.assertEqual(second.name, "Greedy#2")
        self.assertEqual(first.name, "Greedy")             # renaming one copy leaves the other alone
        self.assertEqual(bot_class.get_name(), "Greedy")   # and the class itself


if __name__ == "__main__":
    unittest.main()
