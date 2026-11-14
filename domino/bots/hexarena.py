"""MEU bot by team hex-arena: plays the move with the highest expected utility.

MEU = Maximum Expected Utility. We can't see the opponent's tiles, so we reason with
probabilities:

1. Which tiles could the opponent hold? Every tile we can't see (not on the board, not in
   our hand) is either in their hand or in the boneyard. When the opponent draws or passes
   with ends (a, b) on the table, they had no tile with an a or a b: those tiles can only be
   in the boneyard.
2. For every legal move we look at the ends it leaves and compute the exact probability that
   the opponent can't play on them: choosing their k tiles at random among the n possible
   ones, the chance that none of the m tiles that fit is among them is C(n-m, k) / C(n, k).
3. Each move gets a utility: dots we get rid of, doubles, our tiles that will still fit, and
   the expected gain of blocking the opponent (probability x value). Near the end we also
   check whether the move closes the game, and who would win on dots.
4. We play the move with the highest expected utility.
"""
from math import comb

from ..board import LEFT, board_ends
from ..domino import full_set, is_double, pip_count
from .base import Bot

ALL_TILES = [tuple(t) for t in full_set()]

# Weights of the utility function (tuned with tools.arena against Greedy and Scoring).
WEIGHT_DOTS = 1.0       # each dot played is a dot that can't count against us
WEIGHT_DOUBLE = 7.0     # doubles fit only one number: get rid of them early
WEIGHT_FOLLOW_UP = 3.0  # each of our tiles that fits one of the new ends
WEIGHT_LAST_OF_NUMBER = 2.0  # playing our last tile of a number loses control of it
WEIGHT_BLOCK = 20.0     # value of the opponent being unable to play (x probability)
GOING_OUT = 1000.0      # playing our last tile wins the game
CLOSED_GAME = 500.0     # closing the game when we'd win (or lose) on dots


def ends_after(board, tile, side):
    """Board ends if `tile` were played on `side`, without touching the board."""
    if not board:
        return tuple(tile)
    left, right = board_ends(board)
    if side == LEFT:
        return (tile[0] if tile[1] == left else tile[1]), right
    return left, (tile[1] if tile[0] == right else tile[0])


def same_tile(a, b):
    """(2, 6) and (6, 2) are the same tile."""
    return a == b or a == (b[1], b[0])


def prob_cannot_play(ends, possible, opponent_tiles):
    """Probability that the opponent has no tile fitting `ends`.

    Assumes their `opponent_tiles` tiles are a random subset of the `possible` tiles
    (hypergeometric distribution): C(n - m, k) / C(n, k), with n possible tiles, m of them
    fitting one of the ends, and k tiles in their hand.
    """
    n, k = len(possible), opponent_tiles
    m = sum(1 for t in possible if ends[0] in t or ends[1] in t)
    if k == 0:
        return 1.0
    if k > n:
        return 0.0
    return comb(n - m, k) / comb(n, k)


class MEUBot(Bot):
    """Plays the move with the highest expected utility, using what it can infer about
    the opponent's hand from their draws and passes."""

    @classmethod
    def get_name(cls):
        return "HexArena MEU"

    @classmethod
    def get_authors(cls):
        return ["Cristina Colunga", "Mónica Anzola"]

    @classmethod
    def get_description(cls):
        return ("Maximum expected utility: estimates which tiles the opponent can hold (and "
                "which they lack, from their draws and passes) and plays the move that best "
                "combines dots played, doubles, tiles that keep fitting and the probability "
                "of blocking the opponent.")

    def __init__(self, seat):
        self.seat = seat
        self.opponent_lacks = set()  # numbers the opponent is known not to hold

    def observe_opponent_turn(self, ends, draws, played):
        """If they drew or passed with `ends` on the table, they had none of those numbers."""
        if ends is None:
            return
        kept = draws - (1 if played else 0)  # tiles they drew and still hold
        if kept > 0:
            # The tiles they kept could hold any number we thought they lacked:
            # only the current ends are still certain.
            self.opponent_lacks = set(ends)
        elif draws > 0 or not played:
            self.opponent_lacks |= set(ends)

    def possible_opponent_tiles(self, view):
        """Tiles we can't see that the opponent could hold."""
        seen = list(view["board"]) + list(view["my_hand"])
        unseen = [t for t in ALL_TILES if not any(same_tile(t, s) for s in seen)]
        return [t for t in unseen if not (set(t) & self.opponent_lacks)]

    def utility(self, view, move, possible):
        """Expected utility of `move` (higher is better)."""
        tile, side = move
        hand = view["my_hand"]
        rest = [t for t in hand if t != tile]
        if not rest:
            return GOING_OUT
        ends = ends_after(view["board"], tile, side)

        value = WEIGHT_DOTS * pip_count(tile)
        if is_double(tile):
            value += WEIGHT_DOUBLE
        value += WEIGHT_FOLLOW_UP * sum(1 for t in rest if ends[0] in t or ends[1] in t)
        for n in set(tile):
            if not any(n in t for t in rest):
                value -= WEIGHT_LAST_OF_NUMBER

        p_block = prob_cannot_play(ends, possible, view["opponent_tiles"])
        value += WEIGHT_BLOCK * p_block

        # Closed game: nobody can ever play on these ends again (all their tiles are on the
        # board or ours, and we hold none). The lower dot total wins.
        nobody_fits = not any(ends[0] in t or ends[1] in t for t in possible + rest)
        if nobody_fits and view["boneyard_size"] == 0:
            my_dots = sum(pip_count(t) for t in rest)
            unseen_dots = sum(pip_count(t) for t in possible)
            # Expected opponent dots: their k tiles out of the possible ones.
            expected_opp = unseen_dots * view["opponent_tiles"] / max(1, len(possible))
            value += CLOSED_GAME if my_dots < expected_opp else -CLOSED_GAME
        return value

    def choose(self, view, moves):
        possible = self.possible_opponent_tiles(view)
        return max(moves, key=lambda move: self.utility(view, move, possible))
