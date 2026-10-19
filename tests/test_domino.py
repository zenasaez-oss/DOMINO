import unittest

from domino.domino import flip, full_set, has_number, is_double, normalize, other_end, pip_count


class TestDomino(unittest.TestCase):
    def test_full_set_has_28_unique_tiles(self):
        tiles = full_set()
        self.assertEqual(len(tiles), 28)
        self.assertEqual(len(set(tiles)), 28)

    def test_is_double(self):
        self.assertTrue(is_double((4, 4)))
        self.assertFalse(is_double((3, 5)))

    def test_pip_count(self):
        self.assertEqual(pip_count((3, 5)), 8)

    def test_has_number(self):
        self.assertTrue(has_number((3, 5), 5))
        self.assertFalse(has_number((3, 5), 2))

    def test_other_end(self):
        self.assertEqual(other_end((3, 5), 3), 5)
        self.assertEqual(other_end((4, 4), 4), 4)
        with self.assertRaises(ValueError):
            other_end((3, 5), 2)

    def test_flip_and_normalize(self):
        self.assertEqual(flip((3, 5)), (5, 3))
        self.assertEqual(normalize((5, 3)), (3, 5))
        self.assertEqual(normalize((3, 5)), (3, 5))


if __name__ == "__main__":
    unittest.main()
