"""The base class every bot inherits from: the contract between the game and a bot.

To write a bot, inherit from Bot and fill in the four required methods:

    class MyBot(Bot):
        @classmethod
        def get_name(cls):
            return "My bot"

        @classmethod
        def get_authors(cls):
            return ["Your name"]

        @classmethod
        def get_description(cls):
            return "Plays its heaviest tile."

        def choose(self, view, moves):
            return moves[0]

Bot inherits from ABC (abstract base class) and marks the required methods with
@abstractmethod, so a bot that forgets one is refused the moment it's created, with an
error naming the missing method, instead of failing halfway through a game:

    TypeError: Can't instantiate abstract class MyBot without an implementation
               for abstract method 'choose'

Identity (name, authors, description) uses classmethods, so the website, the ranking and the
docs can read it from the class without creating a bot.

A bot never gets the Game itself, only `view`: what its seat is allowed to see (its own hand
and everything public), built by Game.view(seat). The opponent's tiles and the boneyard aren't
in it, so a bot can't cheat even if it tries.

What choose returns is checked with check_move: it must be exactly one of the `moves` it was
given. Anything else raises IllegalMove.
"""
from abc import ABC, abstractmethod


class IllegalMove(ValueError):
    """A bot returned something that isn't one of the legal moves it was given."""


def check_move(move, moves):
    """Return `move` if it's exactly one of `moves`, otherwise raise IllegalMove.

    Strict on purpose: the tile must be written as in `moves` ((6, 2), not (2, 6)), as a
    (tile, side) tuple, with side "L" or "R". A bot that returns an element of `moves` can
    never be wrong.
    """
    if not isinstance(move, tuple) or move not in moves:
        raise IllegalMove(f"{move!r} is not one of the legal moves {moves}")
    return move


class Bot(ABC):
    """A domino bot. Inherit from it and implement the four abstract methods.

    If your bot defines its own __init__, its first parameter must be the seat (0 or 1):
    that's how create() builds it.
    """

    _display_name = None    # set by a tournament to tell copies apart; see `name`

    def __init__(self, seat=0):
        self.seat = seat

    # --- identity: readable without creating the bot ------------------------------------
    @classmethod
    @abstractmethod
    def get_name(cls):
        """Return the bot's name, as shown on the website and in the ranking. Must be unique."""

    @classmethod
    @abstractmethod
    def get_authors(cls):
        """Return who wrote the bot, as a non-empty list of names."""

    @classmethod
    @abstractmethod
    def get_description(cls):
        """Return one or two sentences on how the bot decides (its strategy, not its code)."""

    # --- playing --------------------------------------------------------------------------
    @abstractmethod
    def choose(self, view, moves):
        """Pick the move to play. Called only when the bot has at least one legal move;
        drawing and passing are done for it automatically.

        view  - what this bot may see, a dict (see Game.view):
                my_seat, my_hand, board, ends, opponent_tiles, boneyard_size,
                current_seat, history
        moves - every legal move, as (tile, side) with side "L" or "R"

        Must return exactly one of `moves`, as given (checked by check_move).
        """

    # --- construction: how the referee and the tournament build a bot ---------------------
    @classmethod
    def create(cls, seat, seed=None, **options):
        """Build this bot for one game. This is the only way the referee creates a bot.

        seat    - which seat it plays (0 or 1)
        seed    - a number for the bot's own randomness, so a game can be replayed exactly
                  (None: not seeded). A bot without randomness can ignore it, which is what
                  this default does.
        options - settings for this bot, e.g. samples=20 for the Monte Carlo bot

        Override it if your bot uses randomness (pass `seed` on) or needs other settings.
        """
        return cls(seat, **options)

    # --- display name ---------------------------------------------------------------------
    @property
    def name(self):
        """The name shown for this particular bot: get_name(), unless a tournament renamed it
        (e.g. "Greedy#2" when two copies of the same bot play each other)."""
        return self._display_name if self._display_name is not None else self.get_name()

    @name.setter
    def name(self, value):
        self._display_name = value

    def __repr__(self):
        return f"<{type(self).__name__} {self.name!r} seat={getattr(self, 'seat', None)}>"

    # --- optional -------------------------------------------------------------------------
    def observe_opponent_turn(self, ends, draws, played):
        """Optional: what the bot saw on the opponent's last turn. Does nothing by default.

        ends   - board ends when their turn started (None on an empty board)
        draws  - how many tiles they drew
        played - True if they played a tile, False if they passed
        """
