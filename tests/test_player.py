import unittest

from domino.player import Player


class TestPlayer(unittest.TestCase):
    def test_defaults(self):
        p = Player(id="u1", name="Ana")
        self.assertFalse(p.is_bot)
        self.assertEqual(p.hand, [])

    def test_hands_are_not_shared(self):
        a, b = Player(id="1", name="A"), Player(id="2", name="B")
        a.hand.append((1, 2))
        self.assertEqual(b.hand, [])


if __name__ == "__main__":
    unittest.main()
