"""One game in the browser: you against a bot. Also the bot list and the tournament.

This runs inside the web page through Pyodide (Python in the browser), so the page
uses the real rules engine in domino/ with no server. The page only calls the
functions at the bottom and gets back JSON.

The rules engine does all the game logic; this file only runs the bot's turns,
keeps a log of what happened and hides what you must not see (the bot's tiles).
The bot moves only when the page asks (bot_turn), so the page can show it thinking.

Bots: every bot in domino/bots/ can be played, found by the registry (list_bots), so a bot
added to the folder shows up on the page by itself. Our four have a character on the page,
one per level (LEVELS): easy plays its heaviest tile, medium is the scoring bot, hard is the
Monte Carlo bot and superhard the expert bot, which works out the tiles you hold and learns
your style; it keeps what it learned about you from one game to the next.

Who opens: the first game follows the engine's rule (highest double). After that the
web alternates: one game the bot opens, the next one you do, each with the highest
double in their hand (or their heaviest tile if they have no double).
"""
import json

from domino.board import board_ends
from domino.bots import LEVELS, ExpertBot, describe, scan
from domino.game import Game
from domino.hand import highest_double, highest_tile
from domino.player import Player
from domino.referee import BotFault, ask_bot, make_bot, tell_bot
from domino.tournament import Tournament

YOU, BOT = 0, 1
SUPER_THINK = 1.5     # seconds the expert bot thinks per move (Python in the browser is slower)
your_style = {}       # what the expert has learned about how you play, kept between games
CHARACTER = {cls: level for level, cls in LEVELS.items()}   # our bots' characters on the page


def bot_class(choice):
    """The bot called `choice`: a level ("hard") or any bot's name ("Monte Carlo")."""
    if choice in LEVELS:
        return LEVELS[choice]
    bots, _ = scan()
    if choice not in bots:
        raise ValueError(f"there is no bot called {choice!r}")
    return bots[choice]


class Session:
    """The engine's Game plus what the web needs around it."""

    def __init__(self, bot="Scoring", your_name="Tú", opener=None):
        cls = bot_class(bot)
        self.bot_name = cls.get_name()
        self.character = CHARACTER.get(cls)      # None for a bot without a character
        self.game = Game([Player(id="you", name=your_name),
                          Player(id="bot", name=self.bot_name, is_bot=True)])
        if opener is not None:
            self._set_opener(opener)
        self.log = []                 # what happened, newest last
        self.last_bot_turn = []       # what the bot did in its last turn
        options = {}
        if cls is ExpertBot:
            # it reads the opening by the engine's rule only in the first game
            options = {"time_limit": SUPER_THINK, "global_opening": opener is None,
                       "memory": your_style.get("evidence")}
        try:
            self.bot = make_bot(cls, BOT, **options)
        except BotFault as fault:     # the bot can't even be built: you win
            self.bot = None
            self.last_bot_turn = [self._forfeit(fault)]
            self.log.extend(self.last_bot_turn)
        if isinstance(self.bot, ExpertBot):
            your_style["evidence"] = self.bot.style_evidence
        self._start_your_turn()       # if the bot opens, the page calls bot_turn()

    def _set_opener(self, seat):
        """Make `seat` open, with their highest double (or heaviest tile if they have none)."""
        hand = self.game.players[seat].hand
        self.game.opening_tile = highest_double(hand) or highest_tile(hand)
        self.game.turns.current = seat

    def _forfeit(self, fault):
        """The bot broke the rules: it loses, you win. Returns the log entry."""
        self.game.forfeit(BOT, fault.reason)
        return {"who": "bot", "action": "forfeit", "reason": fault.reason, "detail": fault.detail}

    # --- your turn ---
    def _start_your_turn(self):
        """Remember what the bot could see when your turn began."""
        self.turn_ends = board_ends(self.game.board)
        self.turn_draws = 0

    def _tell_bot(self, played):
        """Tell the bot what it saw on your turn (observe_opponent_turn), through the referee."""
        if self.game.finished:
            return
        try:
            tell_bot(self.bot, BOT, self.turn_ends, self.turn_draws, played)
        except BotFault as fault:
            self.log.append(self._forfeit(fault))

    def play(self, tile, side):
        opening = not self.game.board
        self.game.play(YOU, tile, side)
        self.log.append({"who": "you", "action": "play", "tile": tile, "side": side, "opening": opening})
        self._tell_bot(played=True)

    def draw(self):
        tile = self.game.draw(YOU)
        self.turn_draws += 1
        self.log.append({"who": "you", "action": "draw", "tile": tile})

    def pass_turn(self):
        self.game.pass_turn(YOU)
        self.log.append({"who": "you", "action": "pass"})
        self._tell_bot(played=False)

    # --- bot's turn ---
    def bot_choice(self, moves):
        """The bot's move, asked through the referee: the bot only sees its view, and if it
        crashes or answers with an illegal move, BotFault is raised (no time limit here:
        Python in the browser can't run the referee's clock)."""
        return ask_bot(self.bot, BOT, self.game.view(BOT), moves)

    def run_bot(self):
        """Let the bot play until it's your turn again or the game is over."""
        game = self.game
        turn = []
        while not game.finished and game.current_seat == BOT:
            moves = game.legal_moves(BOT)
            if moves:
                try:
                    tile, side = self.bot_choice(moves)
                except BotFault as fault:             # the bot broke the rules: it loses, you win
                    turn.append(self._forfeit(fault))
                    break
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
            "bot": self.bot_name,
            "character": self.character,
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
tournament = None    # the tournament being played on the page, if any


def _reply(action):
    """Run `action` and answer with the game as JSON, or {"error": ...} if it was illegal."""
    try:
        action()
        return json.dumps(current.to_dict())
    except ValueError as error:
        return json.dumps({"error": str(error)})


def list_bots():
    """Every bot in domino/bots/: our four characters first (easy to superhard), then the rest
    by name. Files that fail to load are listed under "problems" instead of breaking the page."""
    found, problems = scan()
    bots = []
    for name, cls in found.items():
        try:
            bots.append({**describe(cls), "id": name, "character": CHARACTER.get(cls)})
        except Exception as error:   # noqa: BLE001 - one bad bot mustn't hide the others
            problems.append(f"{name}: {type(error).__name__}: {error}")
    order = list(LEVELS)
    bots.sort(key=lambda b: (order.index(b["character"]) if b["character"] else len(order),
                             b["name"].lower()))
    return json.dumps({"bots": bots, "problems": problems})


def new_game(bot="medium"):
    """Start a game against `bot`: a level ("hard") or any bot's name ("Monte Carlo")."""
    def start():
        global current, last_opener
        opener = None if last_opener is None else 1 - last_opener
        current = Session(bot, opener=opener)
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


def tournament_start(names, games_per_pair=2, seed=0):
    """Start a tournament between the bots named in `names` (a JSON list). The page then calls
    tournament_step() once per game, so it can redraw the table between games."""
    global tournament
    try:
        found, _ = scan()
        chosen = {name: found[name] for name in json.loads(names) if name in found}
        tournament = Tournament(chosen, int(games_per_pair), int(seed))
    except ValueError as error:
        return json.dumps({"error": str(error)})
    return json.dumps(tournament.to_dict())


def tournament_step():
    """Play the tournament's next game and answer with the tournament as it stands."""
    if tournament is None:
        return json.dumps({"error": "no tournament has been started"})
    if not tournament.finished:
        tournament.play_next()
    return json.dumps(tournament.to_dict())
