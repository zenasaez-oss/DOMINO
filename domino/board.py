"""The line of tiles on the table.

Classic domino: one line of play with two open ends (left and right), no branches.
The board is a list of tiles laid out left -> right, each oriented so touching numbers match:
    [(1, 3), (3, 3), (3, 6)]  ->  left end = 1, right end = 6
"""
from .domino import flip

LEFT = "L"
RIGHT = "R"
SIDES = (LEFT, RIGHT)


def board_ends(board):
    """Return (left_end, right_end), or None if the board is empty."""
    if not board:
        return None
    return board[0][0], board[-1][1]


def place_tile(board, tile, side):
    """Put `tile` on `side` of the board, turned so it matches. Raises if it doesn't fit."""
    if not board:
        board.append(tile)
        return
    left, right = board_ends(board)
    if side == LEFT and left in tile:
        board.insert(0, tile if tile[1] == left else flip(tile))
    elif side == RIGHT and right in tile:
        board.append(tile if tile[0] == right else flip(tile))
    else:
        raise ValueError(f"{tile} does not fit on side {side}")
