import unittest

from domino.bots import LEVELS, Bot


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


if __name__ == "__main__":
    unittest.main()
