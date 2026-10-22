"""The bots a player can choose to play against.

Every bot has the same two methods:
    choose(game, moves)                        -> the (tile, side) it plays
    observe_opponent_turn(ends, draws, played) -> optional, what it saw the opponent do

None of them print or ask for input; the website and the terminal tools both use them.
"""
from .expert import ExpertBot
from .greedy import GreedyBot
from .montecarlo import MonteCarloBot
from .scoring import ScoringBot

# level name (as the website shows it) -> bot class
LEVELS = {
    "easy": GreedyBot,
    "medium": ScoringBot,
    "hard": MonteCarloBot,
    "superhard": ExpertBot,
}
