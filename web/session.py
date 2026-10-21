"""One game in the browser: you against a bot.

This runs inside the web page through Pyodide (Python in the browser), so the page
uses the real rules engine in domino/ with no server. The page only calls the
functions at the bottom and gets back JSON.

The rules engine does all the game logic; this file only runs the bot's turns,
keeps a log of what happened and hides what you must not see (the bot's tiles).
The bot moves only when the page asks (bot_turn), so the page can show it thinking.

Who opens: the first game follows the engine's rule (highest double). After that the
web alternates: one game the bot opens, the next one you do, each with the highest
double in their hand (or their heaviest tile if they have no double).
"""
import json

from domino.board import board_ends
from domino.domino import pip_count
from domino.game import Game
from domino.hand import highest_double, highest_tile
from domino.player import Player
from tools.play_scoring import ScoringBot

YOU, BOT = 0, 1
BOT_LEVELS = ("easy", "medium")


class Session:
    """The engine's Game plus what the web needs around it."""

    def __init__(self, level="medium", your_name="Tú", opener=None):
        if level not in BOT_LEVELS:
            raise ValueError(f"level must be one of {BOT_LEVELS}")
        self.level = level
        self.game = Game([Player(id="you", name=your_name),
                          Player(id="bot", name="Bot", is_bot=True)])
        if opener is not None:
            self._set_opener(opener)
        self.bot = ScoringBot(BOT)
        self.log = []                 # what happened, newest last
        self.last_bot_turn = []       # what the bot did in its last turn
        self._start_your_turn()       # if the bot opens, the page calls bot_turn()

    def _set_opener(self, seat):
        """Make `seat` open, with their highest double (or heaviest tile if they have none)."""
        hand = self.game.players[seat].hand
        self.game.opening_tile = highest_double(hand) or highest_tile(hand)
        self.game.turns.current = seat

    # --- your turn ---
    def _start_your_turn(self):
        """Remember what the scoring bot could see when your turn began."""
        self.turn_ends = board_ends(self.game.board)
        self.turn_draws = 0

    def play(self, tile, side):
        opening = not self.game.board
        self.game.play(YOU, tile, side)
        self.bot.observe_opponent_turn(self.turn_ends, self.turn_draws, played=True)
        self.log.append({"who": "you", "action": "play", "tile": tile, "side": side, "opening": opening})

    def draw(self):
        tile = self.game.draw(YOU)
        self.turn_draws += 1
        self.log.append({"who": "you", "action": "draw", "tile": tile})

    def pass_turn(self):
        self.game.pass_turn(YOU)
        self.bot.observe_opponent_turn(self.turn_ends, self.turn_draws, played=False)
        self.log.append({"who": "you", "action": "pass"})

    # --- bot's turn ---
    def bot_choice(self, moves):
        if self.level == "medium":
            return self.bot.choose(self.game, moves)
        return max(moves, key=lambda m: pip_count(m[0]))  # easy: heaviest tile

    def run_bot(self):
        """Let the bot play until it's your turn again or the game is over."""
        game = self.game
        turn = []
        while not game.finished and game.current_seat == BOT:
            moves = game.legal_moves(BOT)
            if moves:
                tile, side = self.bot_choice(moves)
                opening = not game.board
                game.play(BOT, tile, side)
                turn.append({"who": "bot", "action": "play", "tile": tile, "side": side, "opening": opening})
            elif game.can_draw(BOT):
                game.draw(BOT)  # which tile the bot drew stays secret
                turn.append({"who": "bot", "action": "draw"})
            else:
                game.pass_turn(BOT)
                turn.append({"who": "bot", "action": "pass"})
        if turn:  # nothing happens if it wasn't the bot's turn
            self.last_bot_turn = turn
            self.log.extend(turn)
            self._start_your_turn()

    # --- what the page gets ---
    def to_dict(self):
        game = self.game
        state = game.state(for_seat=YOU)  # only your own hand is revealed
        state.update({
            "level": self.level,
            "opening_tile": game.opening_tile,
            "can_draw": game.can_draw(YOU),
            "can_pass": game.can_pass(YOU),
            "log": self.log,  # the whole game, for the history
            "bot_turn": self.last_bot_turn,
            # the bot's tiles are only shown once the game is over
            "bot_hand": list(game.players[BOT].hand) if game.finished else None,
        })
        return state


# --- what the web page calls (one game per open page) ---
current = None
last_opener = None   # who opened the previous game, so the next one goes to the other


def _reply(action):
    """Run `action` and answer with the game as JSON, or {"error": ...} if it was illegal."""
    try:
        action()
        return json.dumps(current.to_dict())
    except ValueError as error:
        return json.dumps({"error": str(error)})


def new_game(level="medium"):
    def start():
        global current, last_opener
        opener = None if last_opener is None else 1 - last_opener
        current = Session(level, opener=opener)
        last_opener = current.game.current_seat
    return _reply(start)


def play(a, b, side):
    """Play the tile (a, b) on side "L" or "R"."""
    return _reply(lambda: current.play((int(a), int(b)), side))


def draw():
    return _reply(lambda: current.draw())


def pass_turn():
    return _reply(lambda: current.pass_turn())


def bot_turn():
    """Let the bot take its turn (does nothing if it isn't the bot's turn)."""
    return _reply(lambda: current.run_bot())
