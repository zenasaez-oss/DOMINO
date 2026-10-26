"""The referee: plays a game between two bots and makes sure no bot can break it.

Every bot only ever gets its view (Game.view). If a bot misbehaves it loses the game on the spot
and the other bot wins; nothing else breaks:

    "error"   - it crashed (raised an exception), while being created or while playing
    "illegal" - choose returned something that isn't one of its legal moves
    "timeout" - it took longer than the time limit to answer

    from domino.bots import GreedyBot, ScoringBot
    from domino.referee import play_match

    result = play_match(GreedyBot, ScoringBot, seed=7)
    result.winner, result.end_reason, result.fault

The same seed replays exactly the same game: it sets the deal, and each bot gets its own seed
from it through create(). random.seed(seed) is also set, for bots that use the random module
directly.

The time limit needs a thread to stop waiting for a bot that hangs. Python in the browser
(Pyodide) can't start threads, so the website calls ask_bot with time_limit=None: crashes and
illegal moves are still caught there, only the clock isn't.
"""
import random
import threading
from dataclasses import dataclass, field

from .board import board_ends
from .bots.base import Bot, IllegalMove, check_move
from .game import Game
from .player import Player

FAULTS = ("error", "illegal", "timeout")


class BotFault(Exception):
    """A bot broke the rules. `reason` is one of FAULTS, `detail` says what happened."""

    def __init__(self, seat, reason, detail):
        super().__init__(f"seat {seat}: {reason} - {detail}")
        self.seat = seat
        self.reason = reason
        self.detail = detail


class _TooSlow(Exception):
    pass


def _run(action, time_limit):
    """Run `action()` and return its result. With a time limit it runs in a thread and we stop
    waiting after `time_limit` seconds (a bot stuck in an endless loop can't hold us up)."""
    if time_limit is None:
        return action()
    box = {}

    def target():
        try:
            box["value"] = action()
        except BaseException as error:          # noqa: BLE001 - report anything the bot raises
            box["error"] = error

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(time_limit)
    if worker.is_alive():
        raise _TooSlow(f"no answer after {time_limit} s")
    if "error" in box:
        raise box["error"]
    return box.get("value")


def _guard(seat, action, time_limit):
    """Run something a bot does; turn any misbehaviour into a BotFault for `seat`."""
    try:
        return _run(action, time_limit)
    except _TooSlow as slow:
        raise BotFault(seat, "timeout", str(slow)) from None
    except (Exception, SystemExit) as error:     # a bot calling sys.exit() mustn't stop us either
        raise BotFault(seat, "error", f"{type(error).__name__}: {error}") from None


def make_bot(bot_class, seat, seed=None, time_limit=None, **options):
    """Build a bot through its create(). Raises BotFault if that fails."""
    bot = _guard(seat, lambda: bot_class.create(seat, seed, **options), time_limit)
    if not isinstance(bot, Bot):
        raise BotFault(seat, "error", f"create() returned {bot!r}, not a Bot")
    return bot


def ask_bot(bot, seat, view, moves, time_limit=None):
    """Ask `bot` for its move. Returns one of `moves`, or raises BotFault."""
    move = _guard(seat, lambda: bot.choose(view, moves), time_limit)
    try:
        return check_move(move, moves)
    except IllegalMove as illegal:
        raise BotFault(seat, "illegal", str(illegal)) from None


def tell_bot(bot, seat, ends, draws, played, time_limit=None):
    """Tell `bot` what it saw on the opponent's turn (observe_opponent_turn). Raises BotFault."""
    _guard(seat, lambda: bot.observe_opponent_turn(ends, draws, played), time_limit)


@dataclass
class MatchResult:
    winner: int | None          # seat 0 or 1, or None for a tied blocked game
    end_reason: str             # "domino", "blocked", or a fault: "error", "illegal", "timeout"
    score: int                  # dots the winner scores (0 on a tie)
    fault: dict | None = None   # {"seat", "reason", "detail"} when a bot lost by misbehaving
    names: tuple = ()           # the two bots' names, seat 0 first
    history: list = field(default_factory=list)


def play_match(bot_a, bot_b, seed=0, time_limit=None, options=({}, {})):
    """Play one full game: bot_a (a Bot subclass) in seat 0 against bot_b in seat 1.

    seed       - replays the same game every time (the deal and both bots' randomness)
    time_limit - seconds a bot may take for each action (None: no limit)
    options    - settings for each bot's create(), e.g. ({"samples": 20}, {})
    """
    random.seed(seed)
    game = Game([Player(id=str(seat), name=f"seat {seat}", is_bot=True) for seat in (0, 1)])
    bot_seeds = random.Random(seed).sample(range(2 ** 31), 2)
    bots, fault = [None, None], None

    try:
        for seat, bot_class in enumerate((bot_a, bot_b)):
            bots[seat] = make_bot(bot_class, seat, bot_seeds[seat], time_limit, **options[seat])

        while not game.finished:
            seat = game.current_seat
            ends, draws = board_ends(game.board), 0
            while True:
                moves = game.legal_moves(seat)
                if moves:
                    tile, side = ask_bot(bots[seat], seat, game.view(seat), moves, time_limit)
                    game.play(seat, tile, side)
                    played = True
                    break
                if game.can_draw(seat):
                    game.draw(seat)
                    draws += 1
                    continue
                game.pass_turn(seat)
                played = False
                break
            if not game.finished:
                other = 1 - seat
                tell_bot(bots[other], other, ends, draws, played, time_limit)
    except BotFault as broke:
        fault = {"seat": broke.seat, "reason": broke.reason, "detail": broke.detail}
        game.forfeit(broke.seat, broke.reason)

    state = game.state()
    names = tuple(getattr(bot, "name", bot_class.__name__) if bot is not None else bot_class.__name__
                  for bot, bot_class in zip(bots, (bot_a, bot_b)))
    return MatchResult(winner=game.winner, end_reason=game.end_reason, score=state["score"] or 0,
                       fault=fault, names=names, history=game.history)
