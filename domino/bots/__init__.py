"""The bots a player can choose to play against.

Every bot inherits from Bot (base.py), which defines what a bot must provide:
    get_name(), get_authors(), get_description()  -> who it is (readable without creating it)
    choose(view, moves)                            -> one of moves (checked by check_move)
    observe_opponent_turn(ends, draws, played)     -> optional, what it saw the opponent do

None of them print or ask for input; the website and the terminal tools both use them.

find_bots() (registry.py) finds every bot in this folder automatically, so adding a bot is just
adding a file here. LEVELS below is the website's own pick of four bots, one per level.
"""
from .base import Bot, IllegalMove, check_move
from .registry import BotRegistryError, find_bots, scan
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
