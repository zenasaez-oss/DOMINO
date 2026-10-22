import random
import unittest

from domino.board import board_ends
from domino.domino import pip_count
from domino.game import Game
from domino.player import Player
from domino.bots.expert import (BIT, INDEX, STYLES, TILES, ExpertBot, TooBig, ends_after, legal, negamax,
                                opponent_appeal)
from domino.bots import ScoringBot


def mask(tiles):
    return sum(BIT[INDEX[t]] for t in tiles)


class HeavyBot:
    """Always plays its heaviest tile (like tools/play.py)."""

    def __init__(self, seat):
        self.seat = seat

    def choose(self, game, moves):
        return max(moves, key=lambda m: pip_count(m[0]))


def play_game(bots, seed):
    """One full game between two bots (bots[seat]). Returns the winner's seat, or None on a tie."""
    random.seed(seed)
    game = Game([Player(id=str(i), name=f"bot{i}", is_bot=True) for i in range(2)])
    while not game.finished:
        seat = game.current_seat
        ends, draws = board_ends(game.board), 0
        while True:
            moves = game.legal_moves(seat)
            if moves:
                move = bots[seat].choose(game, moves)
                assert move in moves, f"illegal move {move}"
                game.play(seat, *move)
                played = True
                break
            if game.can_draw(seat):
                game.draw(seat)
                draws += 1
                continue
            game.pass_turn(seat)
            played = False
            break
        other = bots[1 - seat]
        if hasattr(other, "observe_opponent_turn"):
            other.observe_opponent_turn(ends, draws, played)
    return game.winner


class FakeGame:
    """Just enough of a Game for the bot to read: the state it would see from its seat."""

    def __init__(self, board, my_hand, opp_left, yard, seat=1):
        self.view = {
            "board": board,
            "ends": (board[0][0], board[-1][1]) if board else None,
            "my_hand": my_hand,
            "players": [{"tiles_left": opp_left}, {"tiles_left": len(my_hand)}] if seat == 1
            else [{"tiles_left": len(my_hand)}, {"tiles_left": opp_left}],
            "boneyard_size": yard,
        }

    def state(self, for_seat=None):
        return self.view


class TestHelpers(unittest.TestCase):
    def test_legal_lists_each_way_a_tile_fits(self):
        moves = legal([(1, 3), (2, 2)], 1, 3)
        self.assertIn(((1, 3), 3, 3), moves)        # (1,3) on the left: the 1 is covered
        self.assertIn(((1, 3), 1, 1), moves)        # on the right: the 3 is covered
        self.assertEqual(len(moves), 2)

    def test_ends_after(self):
        self.assertEqual(ends_after((1, 5), (1, 4), "L"), (4, 5))
        self.assertEqual(ends_after((1, 5), (5, 6), "R"), (1, 6))
        self.assertEqual(ends_after(None, (2, 3), "R"), (2, 3))

    def test_styles_prefer_what_they_were_fitted_on(self):
        hand = [(6, 6), (0, 1), (1, 2)]
        heavy = STYLES["heavy"]
        self.assertGreater(opponent_appeal(hand, (6, 6), 6, 6, m=heavy),
                           opponent_appeal(hand, (0, 1), 1, 6, m=heavy))
        self.assertEqual(opponent_appeal(hand, (6, 6), 6, 6, m=STYLES["random"]), 0.0)


class TestExactSolver(unittest.TestCase):
    def test_last_tile_that_fits_wins(self):
        # we hold (2,3) on ends 3/4; they hold (5,5) which never fits: we play and go out
        self.assertEqual(negamax(mask([(2, 3)]), mask([(5, 5)]), 3, 4, False, (), 0, {}, 1000), 1)

    def test_blocked_game_goes_to_fewer_dots(self):
        # nobody can play on 0/0 and the boneyard is empty: 3 dots beat 12
        self.assertEqual(negamax(mask([(1, 2)]), mask([(6, 6)]), 0, 0, False, (), 0, {}, 1000), 1)
        self.assertEqual(negamax(mask([(6, 6)]), mask([(1, 2)]), 0, 0, False, (), 0, {}, 1000), -1)

    def test_draws_from_the_boneyard_in_order(self):
        # we can't play on 0/0, so we draw (0,4) and play it; then nobody can follow 4/0 and the
        # game is blocked with our 10 dots against their 14
        self.assertEqual(negamax(mask([(5, 5)]), mask([(6, 6), (1, 1)]), 0, 0, False,
                                 (BIT[INDEX[(0, 4)]],), 0, {}, 1000), 1)

    def test_gives_up_on_huge_positions(self):
        with self.assertRaises(TooBig):
            full = list(TILES)
            negamax(mask(full[:7]), mask(full[7:14]), 0, 0, False, (), 0, {}, 10)


class TestOpening(unittest.TestCase):
    def test_a_double_opening_rules_out_higher_doubles(self):
        bot = ExpertBot(1, samples=5, seed=1)
        bot._read_opening(FakeGame([(4, 4)], [(0, 1)], 6, 14).state(), [((0, 1), "R")])
        self.assertEqual(bot.never, {(5, 5), (6, 6)})

    def test_a_plain_opening_rules_out_every_double_and_heavier_tiles(self):
        bot = ExpertBot(1, samples=5, seed=1)
        bot._read_opening(FakeGame([(3, 5)], [(0, 1)], 6, 14).state(), [((0, 1), "R")])
        self.assertTrue(all((n, n) in bot.never for n in range(7)))
        self.assertIn((4, 6), bot.never)            # 10 dots: heavier than 3-5
        self.assertIn((2, 6), bot.never)            # 8 dots like 3-5, but its 6 beats the 5
        self.assertNotIn((1, 6), bot.never)         # 7 dots: lighter
        self.assertNotIn((1, 2), bot.never)

    def test_when_we_open_it_only_counts_under_the_engines_rule(self):
        mine = ExpertBot(1, samples=5, seed=1, global_opening=False)
        mine._read_opening(FakeGame([], [(4, 4), (0, 1)], 7, 14).state(), [((4, 4), "R")])
        self.assertEqual(mine.never, set())


class TestDecisions(unittest.TestCase):
    def test_goes_out_when_it_can(self):
        bot = ExpertBot(1, samples=10, seed=3)
        game = FakeGame([(2, 3)], [(3, 6)], 5, 10)
        self.assertEqual(bot.choose(game, [((3, 6), "R")]), ((3, 6), "R"))

    def test_belief_is_a_probability_for_each_hidden_tile(self):
        game = Game([Player("a", "A"), Player("b", "B")])
        bot = ExpertBot(1, samples=10, seed=4)
        belief = bot.belief(game, worlds=200)
        self.assertTrue(all(0.0 <= p <= 1.0 for p in belief.values()))
        self.assertAlmostEqual(sum(belief.values()), len(game.players[0].hand), places=6)

    def test_style_odds_add_up(self):
        odds = ExpertBot(1).style_odds()
        self.assertAlmostEqual(sum(odds.values()), 1.0)
        self.assertEqual(set(odds), set(STYLES))

    def test_plays_whole_games_with_legal_moves(self):
        for i in range(4):
            winner = play_game([ExpertBot(0, samples=15, seed=i), ScoringBot(1)], 100 + i)
            self.assertIn(winner, (0, 1, None))

    def test_learns_that_a_heavy_player_is_heavy(self):
        # across a few games against the always-heaviest bot, shared memory should favour "heavy"
        memory = {name: 0.0 for name in STYLES}
        for i in range(6):
            play_game([ExpertBot(0, samples=20, seed=i, memory=memory), HeavyBot(1)], 200 + i)
        odds = ExpertBot(0, memory=memory).style_odds()
        self.assertEqual(max(odds, key=odds.get), "heavy")

    def test_beats_the_heavy_bot_more_often_than_not(self):
        wins = sum(play_game([ExpertBot(0, samples=30, seed=i), HeavyBot(1)], 300 + i) == 0 for i in range(20))
        self.assertGreater(wins, 10)


if __name__ == "__main__":
    unittest.main()
