"""Medium bot: scores every legal move and plays the best one.

It only uses what any player at the table can see: the board, its own hand, how many tiles
the opponent holds, and when the opponent draws or passes.
"""
import random

from ..board import LEFT, board_ends
from ..domino import is_double, pip_count

NUMBERS_PER_SET = 7  # in a double-six set every number appears on 7 tiles


def ends_after(board, tile, side):
    """Board ends if `tile` were played on `side`, without touching the board."""
    if not board:
        return tile
    left, right = board_ends(board)
    if side == LEFT:
        return (tile[0] if tile[1] == left else tile[1]), right
    return left, (tile[1] if tile[0] == right else tile[0])


class ScoringBot:
    """Scores every legal move and plays the best one.

    It only uses what any player at the table can see: the board, its own hand,
    how many tiles the opponent holds, and when the opponent draws or passes.
    """

    def __init__(self, seat):
        self.seat = seat
        self.opponent = 1 - seat
        self.opponent_lacks = set()  # numbers the opponent is known not to hold

    def observe_opponent_turn(self, ends, draws, played):
        """Update what we know after the opponent's turn.

        ends   - board ends when their turn started (None on an empty board)
        draws  - how many tiles they drew this turn
        played - True if they played a tile, False if they passed
        """
        if ends is None:
            return
        kept = draws - (1 if played else 0)   # drawn tiles still in their hand
        if kept > 0:
            # A kept tile didn't fit these ends, but could hold any older "missing" number.
            self.opponent_lacks = set(ends)
        elif draws > 0 or not played:
            # They drew and played the one matching tile, or passed without drawing:
            # everything we knew still holds, and now they lack these ends too.
            self.opponent_lacks |= set(ends)
        # Played without drawing: nothing learned, and nothing they already lacked changes.

    def choose(self, game, moves):
        hand = game.players[self.seat].hand
        opp_tiles = len(game.players[self.opponent].hand)

        def unseen(rest, n):
            """How many tiles with `n` we haven't seen (not on the board, not in our hand)."""
            return NUMBERS_PER_SET - sum(n in t for t in game.board) - sum(n in t for t in rest)

        def score(move):
            tile, side = move
            rest = [t for t in hand if t != tile]
            new_ends = set(ends_after(game.board, tile, side))

            s = pip_count(tile)                                   # weight
            if is_double(tile):
                s += 4                                            # doubles
            for e in new_ends:
                s += 3 * sum(e in t for t in rest)                # follow-up
            for n in set(tile):
                if not any(n in t for t in rest):
                    s -= 2                                        # variety
            for e in new_ends:
                if e in self.opponent_lacks:
                    s += 5                                        # blocking
            if len(rest) <= opp_tiles:
                for e in new_ends:
                    s += 4 - min(4, unseen(rest, e))              # choking
            if not rest:
                s += 1000                                         # going out
            return s + random.random() * 0.1                      # break ties

        return max(moves, key=score)
