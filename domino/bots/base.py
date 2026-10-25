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
"""
from abc import ABC, abstractmethod


class Bot(ABC):
    """A domino bot. Inherit from it and implement the four abstract methods."""

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

        Must return one of `moves`.
        """

    # --- optional -------------------------------------------------------------------------
    def observe_opponent_turn(self, ends, draws, played):
        """Optional: what the bot saw on the opponent's last turn. Does nothing by default.

        ends   - board ends when their turn started (None on an empty board)
        draws  - how many tiles they drew
        played - True if they played a tile, False if they passed
        """
