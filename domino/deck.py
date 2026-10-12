"""Shuffling and dealing tiles."""
import random

from .domino import full_set


def shuffled_set(max_pip=6):
    tiles = full_set(max_pip)
    random.shuffle(tiles)
    return tiles


def deal(tiles, n_players, tiles_per_player):
    """Split `tiles` into hands. Returns (hands, boneyard); whatever isn't dealt is the boneyard."""
    if n_players * tiles_per_player > len(tiles):
        raise ValueError("not enough tiles for that many players")
    hands = [tiles[i * tiles_per_player:(i + 1) * tiles_per_player] for i in range(n_players)]
    boneyard = tiles[n_players * tiles_per_player:]
    return hands, boneyard
