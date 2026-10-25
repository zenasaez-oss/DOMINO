"""Easy bot: always plays its heaviest tile."""
from ..domino import pip_count
from .base import Bot


class GreedyBot(Bot):
    """Plays the legal move with the most dots. Ignores everything else."""

    @classmethod
    def get_name(cls):
        return "Greedy"

    @classmethod
    def get_authors(cls):
        return ["Zena Saez"]

    @classmethod
    def get_description(cls):
        return "Always plays its heaviest tile, to get rid of dots early."

    def __init__(self, seat):
        self.seat = seat

    def choose(self, view, moves):
        return max(moves, key=lambda m: pip_count(m[0]))
