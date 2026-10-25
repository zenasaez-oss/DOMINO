"""The filtered view: what a bot is allowed to see, and the public history it includes."""
import random
import unittest

from domino.board import RIGHT
from domino.bots import LEVELS, Bot
from domino.game import Game
from tests.test_game import make_game

VIEW_KEYS = {"my_seat", "my_hand", "board", "ends", "opponent_tiles", "boneyard_size",
             "current_seat", "history"}


def tiles_in(view):
    """Every tile that appears anywhere in a view."""
    seen = set(view["my_hand"]) | {tuple(sorted(t)) for t in view["board"]}
    seen |= {tuple(sorted(e["tile"])) for e in view["history"] if "tile" in e}
    return seen


class TestHistory(unittest.TestCase):
    def test_plays_draws_and_passes_are_recorded_in_order(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 2), (3, 4)]], boneyard=[(0, 5), (5, 6)])
        game.play(0, (6, 6), RIGHT)
        game.draw(1)                       # draws (5, 6)
        game.play(1, (5, 6), RIGHT)
        self.assertEqual(game.history, [
            {"seat": 0, "action": "play", "tile": (6, 6), "side": "R"},
            {"seat": 1, "action": "draw"},
            {"seat": 1, "action": "play", "tile": (5, 6), "side": "R"},
        ])

    def test_a_draw_never_says_which_tile(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 2), (3, 4)]], boneyard=[(0, 5), (5, 6)])
        game.play(0, (6, 6), RIGHT)
        game.draw(1)
        self.assertEqual(game.history[-1], {"seat": 1, "action": "draw"})

    def test_passes_are_recorded(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 2), (3, 4)]])
        game.play(0, (6, 6), RIGHT)
        game.pass_turn(1)
        self.assertEqual(game.history[-1], {"seat": 1, "action": "pass"})

    def test_illegal_moves_are_not_recorded(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 2), (3, 4)]])
        with self.assertRaises(ValueError):
            game.play(0, (0, 0), RIGHT)    # must open with (6, 6)
        self.assertEqual(game.history, [])


class TestView(unittest.TestCase):
    def test_it_has_exactly_the_public_fields(self):
        self.assertEqual(set(Game.quick_start().view(0)), VIEW_KEYS)

    def test_each_seat_sees_its_own_hand_and_only_a_count_of_the_other(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 2), (3, 4), (2, 5)]])
        self.assertEqual(game.view(0)["my_hand"], [(6, 6), (0, 0)])
        self.assertEqual(game.view(0)["opponent_tiles"], 3)
        self.assertEqual(game.view(1)["my_hand"], [(1, 2), (3, 4), (2, 5)])
        self.assertEqual(game.view(1)["opponent_tiles"], 2)

    def test_secret_tiles_appear_nowhere_in_it(self):
        """Over many random games, at every turn: no opponent tile and no boneyard tile is in the view."""
        rng = random.Random(1)
        for _ in range(100):
            game = Game.quick_start()
            while not game.finished:
                seat = game.current_seat
                view = game.view(seat)
                secret = set(game.players[1 - seat].hand) | set(game.boneyard)
                self.assertFalse(tiles_in(view) & secret)
                self.assertEqual(view["boneyard_size"], len(game.boneyard))
                moves = game.legal_moves(seat)
                if moves:
                    game.play(seat, *rng.choice(moves))
                elif game.can_draw(seat):
                    game.draw(seat)
                else:
                    game.pass_turn(seat)

    def test_changing_the_view_does_not_change_the_game(self):
        game = make_game([[(6, 6), (0, 0)], [(1, 2), (3, 4)]], boneyard=[(0, 5)])
        game.play(0, (6, 6), RIGHT)
        view = game.view(1)
        view["my_hand"].clear()
        view["board"].append((9, 9))
        view["history"][0]["tile"] = (0, 0)
        view["history"].clear()
        self.assertEqual(game.players[1].hand, [(1, 2), (3, 4)])
        self.assertEqual(game.board, [(6, 6)])
        self.assertEqual(game.history[0]["tile"], (6, 6))

    def test_it_holds_only_plain_data_never_the_game(self):
        def plain(value):
            if isinstance(value, dict):
                return all(plain(v) for v in value.values())
            if isinstance(value, (list, tuple)):
                return all(plain(v) for v in value)
            return value is None or isinstance(value, (int, str))
        self.assertTrue(plain(Game.quick_start().view(0)))


class Peeker(Bot):
    """A bot that tries to cheat: it looks for the opponent's tiles in what it's given."""

    @classmethod
    def get_name(cls):
        return "Peeker"

    @classmethod
    def get_authors(cls):
        return ["Tester"]

    @classmethod
    def get_description(cls):
        return "Tries to find the opponent's tiles."

    def __init__(self):
        self.found = set()

    def choose(self, view, moves):
        self.found |= tiles_in(view)
        return moves[0]


class TestBotsOnlyGetTheView(unittest.TestCase):
    def test_a_cheating_bot_finds_nothing_secret(self):
        game = Game.quick_start()
        seat = game.current_seat
        peeker = Peeker()
        peeker.choose(game.view(seat), game.legal_moves(seat))
        self.assertFalse(peeker.found & set(game.players[1 - seat].hand))
        self.assertFalse(peeker.found & set(game.boneyard))

    def test_our_bots_play_full_games_from_the_view_alone(self):
        for level, bot_class in LEVELS.items():
            with self.subTest(level=level):
                random.seed(7)
                game = Game.quick_start()
                options = {"samples": 5} if level in ("hard", "superhard") else {}
                bots = [bot_class(seat, **options) for seat in (0, 1)]
                while not game.finished:
                    seat = game.current_seat
                    moves = game.legal_moves(seat)
                    if moves:
                        move = bots[seat].choose(game.view(seat), moves)
                        self.assertIn(move, moves)
                        game.play(seat, *move)
                    elif game.can_draw(seat):
                        game.draw(seat)
                    else:
                        game.pass_turn(seat)


if __name__ == "__main__":
    unittest.main()
