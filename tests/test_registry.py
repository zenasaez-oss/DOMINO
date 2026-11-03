"""Automatic registration: adding a bot is just adding a file to the bots folder."""
import importlib
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from domino.bots import LEVELS, BotRegistryError, find_bots, scan

GOOD_BOT = '''
from domino.bots import Bot

class {cls}(Bot):
    @classmethod
    def get_name(cls):
        return "{name}"

    @classmethod
    def get_authors(cls):
        return ["Another team"]

    @classmethod
    def get_description(cls):
        return "Plays the first legal move."

    def choose(self, view, moves):
        return moves[0]
'''

INCOMPLETE_BOT = '''
from domino.bots import Bot

class Forgetful(Bot):
    @classmethod
    def get_name(cls):
        return "Forgetful"

    @classmethod
    def get_authors(cls):
        return ["Another team"]

    @classmethod
    def get_description(cls):
        return "Forgot to write choose."
'''


class BotFolder:
    """A throwaway package standing in for domino/bots, so tests can add files to it."""

    def __init__(self, files):
        self._dir = tempfile.TemporaryDirectory()
        self.package = f"tmpbots_{abs(hash(self._dir.name))}"
        root = Path(self._dir.name) / self.package
        root.mkdir()
        (root / "__init__.py").write_text("")
        for name, code in files.items():
            (root / name).write_text(textwrap.dedent(code))

    def __enter__(self):
        sys.path.insert(0, self._dir.name)
        importlib.invalidate_caches()
        return self.package

    def __exit__(self, *exc):
        sys.path.remove(self._dir.name)
        for name in [m for m in sys.modules if m == self.package or m.startswith(self.package + ".")]:
            del sys.modules[name]
        self._dir.cleanup()


class TestOurBots(unittest.TestCase):
    def test_all_four_of_our_bots_are_found(self):
        # other teams' bots may be in the folder too, so these four are a part of what's found
        found = find_bots()
        self.assertLessEqual(set(LEVELS.values()), set(found.values()))
        self.assertLessEqual({"Greedy", "Scoring", "Monte Carlo", "Expert"}, set(found))

    def test_no_problems_in_our_folder(self):
        self.assertEqual(scan()[1], [])


class TestAddingABot(unittest.TestCase):
    def test_a_new_file_is_found_without_editing_anything_else(self):
        with BotFolder({"team7.py": GOOD_BOT.format(cls="Team7Bot", name="Team 7")}) as package:
            bots = find_bots(package)
        self.assertEqual(list(bots), ["Team 7"])
        self.assertEqual(bots["Team 7"].__name__, "Team7Bot")

    def test_several_bots_and_helper_classes(self):
        files = {
            "a.py": GOOD_BOT.format(cls="ABot", name="A"),
            "b.py": GOOD_BOT.format(cls="BBot", name="B") + "\nclass Helper:\n    pass\n",
        }
        with BotFolder(files) as package:
            self.assertEqual(sorted(find_bots(package)), ["A", "B"])   # Helper isn't a bot

    def test_imported_bots_are_not_counted_twice(self):
        files = {
            "a.py": GOOD_BOT.format(cls="ABot", name="A"),
            "b.py": "from .a import ABot\n",                 # b.py only imports A's bot
        }
        with BotFolder(files) as package:
            self.assertEqual(list(find_bots(package)), ["A"])


class TestProblemsAreReported(unittest.TestCase):
    def test_an_incomplete_bot_is_reported_by_name(self):
        with BotFolder({"forgetful.py": INCOMPLETE_BOT}) as package:
            bots, problems = scan(package)
        self.assertEqual(bots, {})
        self.assertEqual(len(problems), 1)
        self.assertIn("Forgetful", problems[0])
        self.assertIn("choose", problems[0])

    def test_two_bots_with_the_same_name_are_reported(self):
        files = {"a.py": GOOD_BOT.format(cls="ABot", name="Same"),
                 "b.py": GOOD_BOT.format(cls="BBot", name="Same")}
        with BotFolder(files) as package:
            bots, problems = scan(package)
        self.assertEqual(len(bots), 1)
        self.assertIn("two bots are called 'Same'", problems[0])

    def test_a_file_with_an_error_is_reported_and_the_others_still_found(self):
        files = {"broken.py": "def broken(:\n",
                 "good.py": GOOD_BOT.format(cls="GoodBot", name="Good")}
        with BotFolder(files) as package:
            bots, problems = scan(package)
        self.assertEqual(list(bots), ["Good"])
        self.assertIn("broken", problems[0])
        self.assertIn("SyntaxError", problems[0])

    def test_find_bots_refuses_a_folder_with_problems(self):
        with BotFolder({"forgetful.py": INCOMPLETE_BOT}) as package:
            with self.assertRaises(BotRegistryError) as caught:
                find_bots(package)
        self.assertIn("Forgetful", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
