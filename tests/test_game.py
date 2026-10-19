import unittest

from domino.board import LEFT, RIGHT
from domino.game import Game, check_player_count, draw_tile, new_game, play_move
from domino.player import Player
from domino.rules import first_player


def make_game(hands, boneyard=()):
    """Game with fixed hands instead of a random deal."""
    game = Game.quick_start()
    for player, hand in zip(game.players, hands):
        player.hand = list(hand)
    game.boneyard = list(boneyard)
    game.turns.current, game.opening_tile = first_player(game.hands)
    return game


class TestFunctions(unittest.TestCase):
    def test_new_game_deals_7_each(self):
        hands, boneyard, board = new_game()
        self.assertEqual([len(h) for h in hands], [7, 7])
        self.assertEqual(len(boneyard), 14)
        self.assertEqual(board, [])

    def test_only_two_players(self):
        check_player_count(2)
        for n in (1, 3, 4):
            with self.assertRaises(ValueError):
                check_player_count(n)

    def test_play_move(self):
        hand, board = [(3, 5), (5, 6)], [(1, 3)]
        play_move(hand, board, (3, 5), RIGHT)
        self.assertEqual((hand, board), ([(5, 6)], [(1, 3), (3, 5)]))

    def test_play_move_rejects_bad_moves(self):
        with self.assertRaises(ValueError):
            play_move([(1, 2)], [(3, 5)], (1, 2), RIGHT)   # does not fit
        with self.assertRaises(ValueError):
            play_move([(1, 2)], [(3, 5)], (5, 6), RIGHT)   # not in the hand

    def test_draw_tile(self):
        hand, boneyard = [], [(0, 1)]
        self.assertEqual(draw_tile(hand, boneyard), (0, 1))
        self.assertIsNone(draw_tile(hand, boneyard))


class TestGame(unittest.TestCase):
    def test_needs_exactly_2_players(self):
        with self.assertRaises(ValueError):
            Game([Player(id="1", name="solo")])
        with self.assertRaises(ValueError):
            Game([Player(id=str(i), name=str(i)) for i in range(3)])

    def test_opener_must_play_opening_tile(self):
        game = make_game([[(6, 6), (1, 6)], [(0, 1), (2, 3)]])
        self.assertEqual(game.current_seat, 0)
        self.assertEqual(game.legal_moves(0), [((6, 6), RIGHT)])
        with self.assertRaises(ValueError):
            game.play(0, (1, 6), RIGHT)
        game.play(0, (6, 6), RIGHT)
        self.assertEqual(game.current_seat, 1)

    def test_wrong_turn(self):
        game = make_game([[(6, 6)], [(0, 1)]])
        with self.assertRaises(ValueError):
            game.play(1, (0, 1), RIGHT)

    def test_tile_order_from_platform_does_not_matter(self):
        game = make_game([[(6, 6), (1, 6)], [(2, 6), (0, 0)]])
        game.play(0, (6, 6), RIGHT)
        game.play(1, (6, 2), LEFT)  # hand holds (2, 6); the platform sent it the other way round
        self.assertEqual(game.board, [(2, 6), (6, 6)])

    def test_going_out_wins(self):
        game = make_game([[(6, 6)], [(0, 1), (2, 3)]])
        game.play(0, (6, 6), RIGHT)
        self.assertTrue(game.finished)
        self.assertEqual((game.winner, game.end_reason), (0, "domino"))
        self.assertEqual(game.state()["score"], 6)

    def test_draw_then_play(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 2), (3, 4)]], boneyard=[(0, 5), (5, 6)])
        game.play(0, (6, 6), RIGHT)
        self.assertFalse(game.can_pass(1))
        with self.assertRaises(ValueError):
            game.pass_turn(1)                      # must draw first
        self.assertEqual(game.draw(1), (5, 6))
        self.assertEqual(game.current_seat, 1)     # still their turn
        game.play(1, (5, 6), RIGHT)
        self.assertEqual(game.current_seat, 0)

    def test_cannot_draw_with_a_legal_move(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 6), (3, 4)]], boneyard=[(0, 5)])
        game.play(0, (6, 6), RIGHT)
        with self.assertRaises(ValueError):
            game.draw(1)

    def test_blocked_game(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 2), (3, 4)]])
        game.play(0, (6, 6), RIGHT)
        game.pass_turn(1)
        game.pass_turn(0)
        self.assertTrue(game.finished)
        self.assertEqual(game.end_reason, "blocked")
        self.assertEqual(game.winner, 0)  # 0 pips vs 10

    def test_state_only_shows_own_hand(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 2), (3, 4)]])
        state = game.state(for_seat=1)
        self.assertEqual(state["my_hand"], [(1, 2), (3, 4)])
        self.assertEqual([p["tiles_left"] for p in state["players"]], [2, 2])

    def test_random_games_finish(self):
        from main import auto_play
        for _ in range(600):
            game = auto_play(Game.quick_start())
            self.assertTrue(game.finished)
            total = len(game.board) + len(game.boneyard) + sum(len(h) for h in game.hands)
            self.assertEqual(total, 28)


if __name__ == "__main__":
    unittest.main()
