"""The bots a player can choose to play against.

Every bot inherits from Bot (base.py), which defines what a bot must provide:
    get_name(), get_authors(), get_description()  -> who it is (readable without creating it)
    choose(game, moves)                            -> the (tile, side) it plays
    observe_opponent_turn(ends, draws, played)     -> optional, what it saw the opponent do

None of them print or ask for input; the website and the terminal tools both use them.
"""
from .base import Bot
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
