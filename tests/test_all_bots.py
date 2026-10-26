"""The checks every bot must pass before it's merged (requirement 2.2).

Nothing to write for a new bot: find_bots() finds every bot in domino/bots/, and each one gets
its own copy of BotContract below (shown as e.g. "TestGreedyBot" in the test output). They run
automatically on every pull request (.github/workflows/tests.yml).

A bot passes if:
  - its file imports, it writes every required method, and its name is unique;
  - its identity is filled in: a name, at least one author, a description;
  - create(seat, seed) builds it for either seat;
  - it plays full games through the referee, in both seats, against another bot and against a
    copy of itself, without crashing, playing an illegal move or taking longer than the platform's
    time limit (STANDARD_TIME_LIMIT seconds per action).
"""
import unittest

from domino.bots import GreedyBot, scan
from domino.referee import STANDARD_TIME_LIMIT, play_match

BOTS, PROBLEMS = scan()
SEEDS = (1, 2)


class TestTheBotFolder(unittest.TestCase):
    def test_every_bot_file_is_valid(self):
        """No file that fails to import, no incomplete bot, no two bots with the same name."""
        self.assertEqual(PROBLEMS, [], "problems in domino/bots/:\n" + "\n".join(PROBLEMS))

    def test_there_are_bots(self):
        self.assertTrue(BOTS)


class BotContract:
    """The tests every bot gets. `bot` is the bot class being checked."""

    bot = None

    def describe(self, result):
        fault = result.fault
        return f"{self.bot.get_name()} lost by {fault['reason']}: {fault['detail']}" if fault else ""

    # --- who it is ---
    def test_has_a_name(self):
        name = self.bot.get_name()
        self.assertIsInstance(name, str)
        self.assertTrue(name.strip(), "get_name() must not be empty")
        self.assertLessEqual(len(name), 40, "keep the name short: it's shown in menus and tables")

    def test_has_authors(self):
        authors = self.bot.get_authors()
        self.assertIsInstance(authors, list, "get_authors() must return a list of names")
        self.assertTrue(authors, "get_authors() must name at least one author")
        for author in authors:
            self.assertIsInstance(author, str)
            self.assertTrue(author.strip(), "an author's name can't be empty")

    def test_has_a_description(self):
        description = self.bot.get_description()
        self.assertIsInstance(description, str)
        self.assertTrue(description.strip(), "get_description() must not be empty")

    # --- being built ---
    def test_create_builds_it_for_either_seat(self):
        for seat in (0, 1):
            with self.subTest(seat=seat):
                instance = self.bot.create(seat, seed=7)
                self.assertIsInstance(instance, self.bot)
                self.assertEqual(instance.seat, seat)

    # --- playing by the rules ---
    def test_plays_full_games_in_both_seats(self):
        for seed in SEEDS:
            for seat in (0, 1):
                with self.subTest(seed=seed, seat=seat):
                    pair = (self.bot, GreedyBot) if seat == 0 else (GreedyBot, self.bot)
                    result = play_match(*pair, seed=seed, time_limit=STANDARD_TIME_LIMIT)
                    self.assertIsNone(result.fault, self.describe(result))
                    self.assertIn(result.end_reason, ("domino", "blocked"))

    def test_plays_a_full_game_against_itself(self):
        result = play_match(self.bot, self.bot, seed=SEEDS[0], time_limit=STANDARD_TIME_LIMIT)
        self.assertIsNone(result.fault, self.describe(result))
        self.assertIn(result.end_reason, ("domino", "blocked"))


# one test class per bot found in the folder, e.g. TestGreedyBot, TestScoringBot, ...
for _bot in BOTS.values():
    _name = f"Test{_bot.__name__}"
    globals()[_name] = type(_name, (BotContract, unittest.TestCase), {"bot": _bot, "__doc__": _bot.get_name()})
del _bot, _name


if __name__ == "__main__":
    unittest.main()
