"""Helpers for one player's hand (a list of tiles)."""
from .domino import is_double, pip_count


def hand_pips(hand):
    """Total dots left in the hand. Lowest total wins a blocked game."""
    return sum(pip_count(t) for t in hand)


def highest_double(hand):
    """The biggest double in the hand, e.g. (6, 6), or None if there are no doubles."""
    doubles = [t for t in hand if is_double(t)]
    return max(doubles, default=None)


def highest_tile(hand):
    """The heaviest tile, ties broken by the bigger half. None for an empty hand."""
    return max(hand, key=lambda t: (pip_count(t), max(t)), default=None)


def is_empty(hand):
    return len(hand) == 0
