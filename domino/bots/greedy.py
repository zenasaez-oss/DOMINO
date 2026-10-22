"""Easy bot: always plays its heaviest tile."""
from ..domino import pip_count


class GreedyBot:
    """Plays the legal move with the most dots. Ignores everything else."""

    def __init__(self, seat):
        self.seat = seat

    def observe_opponent_turn(self, ends, draws, played):
        pass   # it doesn't learn anything

    def choose(self, game, moves):
        return max(moves, key=lambda m: pip_count(m[0]))
