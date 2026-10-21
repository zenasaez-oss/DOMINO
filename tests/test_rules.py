import unittest

from domino.rules import (
    LEFT, RIGHT, blocked_winner, first_player, has_valid_move, has_won,
    is_valid_move, round_score, valid_moves,
)

BOARD = [(1, 3), (3, 3), (3, 6)]  # ends: 1 and 6


class TestMoves(unittest.TestCase):
    def test_is_valid_move(self):
        self.assertTrue(is_valid_move((6, 2), RIGHT, BOARD))
        self.assertFalse(is_valid_move((6, 2), LEFT, BOARD))
        self.assertTrue(is_valid_move((4, 1), LEFT, BOARD))

    def test_only_left_and_right_exist(self):
        self.assertFalse(is_valid_move((6, 2), "U", BOARD))

    def test_anything_goes_on_empty_board(self):
        self.assertTrue(is_valid_move((2, 4), RIGHT, []))

    def test_valid_moves(self):
        hand = [(6, 2), (4, 1), (1, 6), (3, 5)]
        self.assertEqual(
            valid_moves(hand, BOARD),
            [((6, 2), RIGHT), ((4, 1), LEFT), ((1, 6), LEFT), ((1, 6), RIGHT)],
        )

    def test_same_ends_listed_once(self):
        self.assertEqual(valid_moves([(3, 4)], [(3, 5), (5, 3)]), [((3, 4), LEFT)])

    def test_has_valid_move(self):
        self.assertTrue(has_valid_move([(6, 0)], BOARD))
        self.assertFalse(has_valid_move([(2, 4)], BOARD))


class TestGameRules(unittest.TestCase):
    def test_highest_double_starts(self):
        hands = [[(1, 1), (5, 6)], [(4, 4), (0, 2)], [(2, 3)]]
        self.assertEqual(first_player(hands), (1, (4, 4)))

    def test_highest_tile_starts_without_doubles(self):
        hands = [[(1, 2), (3, 6)], [(4, 6), (0, 1)]]
        self.assertEqual(first_player(hands), (1, (4, 6)))

    def test_has_won(self):
        self.assertTrue(has_won([]))
        self.assertFalse(has_won([(0, 1)]))

    def test_blocked_winner_lowest_pips(self):
        self.assertEqual(blocked_winner([[(6, 6)], [(0, 1)], [(2, 2)]]), 1)

    def test_blocked_tie_has_no_winner(self):
        self.assertIsNone(blocked_winner([[(1, 2)], [(0, 3)], [(6, 6)]]))

    def test_round_score(self):
        self.assertEqual(round_score([[], [(1, 2)], [(6, 6)]], winner=0), 15)


if __name__ == "__main__":
    unittest.main()
