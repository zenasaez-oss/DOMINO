"""Single tile helpers.

A tile is a tuple of two numbers, e.g. (3, 5).
"""


def full_set(max_pip=6):
    """Every tile from (0, 0) up to (max_pip, max_pip), each once. Double-six = 28 tiles."""
    return [(a, b) for a in range(max_pip + 1) for b in range(a, max_pip + 1)]


def is_double(tile):
    """Both halves the same, e.g. (4, 4)."""
    return tile[0] == tile[1]


def pip_count(tile):
    """Total dots on the tile, e.g. (3, 5) -> 8."""
    return tile[0] + tile[1]


def has_number(tile, n):
    """Does either half show `n`?"""
    return n in tile


def other_end(tile, n):
    """The half that is not `n`, e.g. other_end((3, 5), 3) -> 5. For a double, returns `n`."""
    if tile[0] == n:
        return tile[1]
    if tile[1] == n:
        return tile[0]
    raise ValueError(f"{tile} has no {n}")


def normalize(tile):
    """Smaller number first, e.g. (5, 3) -> (3, 5). Hands store tiles this way."""
    a, b = tile
    return (a, b) if a <= b else (b, a)


def flip(tile):
    """Turn the tile around, e.g. (3, 5) -> (5, 3)."""
    return tile[1], tile[0]
