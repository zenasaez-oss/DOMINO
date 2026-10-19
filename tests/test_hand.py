import unittest

from domino.hand import hand_pips, highest_double, highest_tile, is_empty


class TestHand(unittest.TestCase):
    def test_hand_pips(self):
        self.assertEqual(hand_pips([(3, 5), (0, 1)]), 9)
        self.assertEqual(hand_pips([]), 0)

    def test_highest_double(self):
        self.assertEqual(highest_double([(1, 1), (5, 5), (6, 4)]), (5, 5))
        self.assertIsNone(highest_double([(1, 2), (3, 4)]))

    def test_highest_tile(self):
        self.assertEqual(highest_tile([(1, 2), (4, 6), (5, 5)]), (4, 6))  # 10 pips, bigger half is 6
        self.assertIsNone(highest_tile([]))

    def test_is_empty(self):
        self.assertTrue(is_empty([]))
        self.assertFalse(is_empty([(0, 0)]))


if __name__ == "__main__":
    unittest.main()
