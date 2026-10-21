import unittest

from domino.board import LEFT, RIGHT, board_ends, place_tile


class TestBoard(unittest.TestCase):
    def test_ends_of_empty_board(self):
        self.assertIsNone(board_ends([]))

    def test_ends(self):
        self.assertEqual(board_ends([(1, 3), (3, 3), (3, 6)]), (1, 6))

    def test_first_tile_goes_down_as_is(self):
        board = []
        place_tile(board, (3, 5), RIGHT)
        self.assertEqual(board, [(3, 5)])

    def test_tiles_are_turned_to_match(self):
        board = [(3, 5)]
        place_tile(board, (5, 6), RIGHT)
        place_tile(board, (1, 3), LEFT)
        place_tile(board, (6, 2), RIGHT)
        place_tile(board, (4, 1), LEFT)
        self.assertEqual(board, [(4, 1), (1, 3), (3, 5), (5, 6), (6, 2)])

    def test_tile_flipped_when_needed(self):
        board = [(3, 5)]
        place_tile(board, (6, 5), RIGHT)
        self.assertEqual(board, [(3, 5), (5, 6)])

    def test_tile_that_does_not_fit(self):
        board = [(3, 5)]
        with self.assertRaises(ValueError):
            place_tile(board, (1, 2), RIGHT)
        self.assertEqual(board, [(3, 5)])


if __name__ == "__main__":
    unittest.main()
