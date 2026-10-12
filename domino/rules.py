"""Game rules: questions about what is allowed. Nothing here changes the game.

Classic domino: one line of play with two open ends (left and right), no branches.
"""
from .board import LEFT, RIGHT, SIDES, board_ends
from .domino import pip_count
from .hand import hand_pips, highest_double, highest_tile, is_empty


def is_valid_move(tile, side, board):
    """Can `tile` be placed on `side` of the board?"""
    if side not in SIDES:
        return False
    if not board:
        return True
    left, right = board_ends(board)
    end = left if side == LEFT else right
    return end in tile


def valid_moves(hand, board):
    """All legal (tile, side) moves for a hand."""
    if not board:
        return [(tile, RIGHT) for tile in hand]
    left, right = board_ends(board)
    moves = []
    for tile in hand:
        if left in tile:
            moves.append((tile, LEFT))
        if right in tile and left != right:  # both ends equal -> one move is enough
            moves.append((tile, RIGHT))
    return moves


def has_valid_move(hand, board):
    return len(valid_moves(hand, board)) > 0


def first_player(hands):
    """Who opens and with which tile: highest double, or the highest tile if nobody has a double.

    Returns (seat, tile).
    """
    doubles = [(highest_double(h), seat) for seat, h in enumerate(hands) if highest_double(h)]
    if doubles:
        tile, seat = max(doubles)
        return seat, tile
    tops = [(highest_tile(h), seat) for seat, h in enumerate(hands) if h]
    tile, seat = max(tops, key=lambda ts: (pip_count(ts[0]), max(ts[0])))
    return seat, tile


def has_won(hand):
    """A player wins by playing their last tile."""
    return is_empty(hand)


def blocked_winner(hands):
    """In a blocked game the lowest dot total wins. Returns the seat, or None on a tie."""
    totals = [hand_pips(h) for h in hands]
    lowest = min(totals)
    if totals.count(lowest) > 1:
        return None
    return totals.index(lowest)


def round_score(hands, winner):
    """Points for the winner: all dots left in the other players' hands."""
    return sum(hand_pips(h) for seat, h in enumerate(hands) if seat != winner)
