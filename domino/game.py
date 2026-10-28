"""Running the game: dealing, playing tiles, drawing, turns and the end of the game.

Legality checks live in rules.py. Nothing here prints or asks for input: the platform
calls these functions / Game methods and reads back the result.

Tiles are tuples like (3, 5). The board is a list of tiles laid out
left -> right, each oriented so touching numbers match:
    [(1, 3), (3, 3), (3, 6)]  ->  left end = 1, right end = 6
"""
from . import rules
from .board import place_tile
from .deck import deal, shuffled_set
from .domino import normalize
from .player import Player
from .turn_manager import TurnManager

# --- presets ---
NUM_PLAYERS = 2       # project requirement: two-player game only
MAX_PIP = 6           # double-six set, 28 tiles
TILES_PER_PLAYER = 7  # 2 players x 7 = 14 dealt, 14 left in the boneyard


def check_player_count(n_players):
    if n_players != NUM_PLAYERS:
        raise ValueError(f"the game needs exactly {NUM_PLAYERS} players, got {n_players}")


def new_game():
    """Shuffle a double-six set and deal 7 tiles to each of the 2 players. Returns (hands, boneyard, board)."""
    hands, boneyard = deal(shuffled_set(MAX_PIP), NUM_PLAYERS, TILES_PER_PLAYER)
    board = []
    return hands, boneyard, board


def play_move(hand, board, tile, side):
    """Remove `tile` from `hand` and place it on `side` of `board`, flipping it if needed."""
    if tile not in hand:
        raise ValueError(f"{tile} is not in the hand")
    if not rules.is_valid_move(tile, side, board):
        raise ValueError(f"{tile} does not fit on side {side}")
    hand.remove(tile)
    place_tile(board, tile, side)


def draw_tile(hand, boneyard):
    """Move one tile from the boneyard into the hand. Returns it, or None if empty."""
    if not boneyard:
        return None
    tile = boneyard.pop()
    hand.append(tile)
    return tile


class Game:
    """One round of classic two-player domino. Players are referred to by seat number (0 or 1).

    Each turn the current player does one of:
      play(seat, tile, side)  - if they have a legal move
      draw(seat)              - if they have no legal move and the boneyard isn't empty
      pass_turn(seat)         - if they have no legal move and the boneyard is empty
    Illegal actions raise ValueError and change nothing.
    """

    def __init__(self, players):
        check_player_count(len(players))
        self.players = players
        hands, self.boneyard, self.board = new_game()
        for player, hand in zip(players, hands):
            player.hand = hand

        first_seat, self.opening_tile = rules.first_player(self.hands)
        self.turns = TurnManager(NUM_PLAYERS, first_seat)
        self.finished = False
        self.winner = None   # seat, or None if a blocked game ended in a tie
        self.end_reason = None  # "domino" (someone went out), "blocked", or a forfeit reason
        self.history = []    # public events, oldest first (see view)

    @classmethod
    def quick_start(cls):
        """Quick setup with two placeholder players, handy for testing."""
        return cls([Player(id=str(i), name=f"Player {i}") for i in range(NUM_PLAYERS)])

    # --- reading the state ---
    @property
    def hands(self):
        return [p.hand for p in self.players]

    @property
    def current_seat(self):
        return self.turns.current

    def legal_moves(self, seat):
        """Moves `seat` could make right now (empty if it isn't their turn)."""
        if self.finished or seat != self.current_seat:
            return []
        if not self.board:  # the opener must play the opening tile
            return [(self.opening_tile, rules.RIGHT)]
        return rules.valid_moves(self.players[seat].hand, self.board)

    def can_draw(self, seat):
        return not self.legal_moves(seat) and bool(self.boneyard) and self._is_turn(seat)

    def can_pass(self, seat):
        return not self.legal_moves(seat) and not self.boneyard and self._is_turn(seat)

    def state(self, for_seat=None):
        """Snapshot for the platform. Only `for_seat`'s own hand is revealed."""
        return {
            "board": list(self.board),
            "ends": rules.board_ends(self.board),
            "current_seat": self.current_seat,
            "players": [
                {"seat": s, "id": p.id, "name": p.name, "tiles_left": len(p.hand)}
                for s, p in enumerate(self.players)
            ],
            "boneyard_size": len(self.boneyard),
            "my_hand": list(self.players[for_seat].hand) if for_seat is not None else None,
            "my_moves": self.legal_moves(for_seat) if for_seat is not None else None,
            "finished": self.finished,
            "winner": self.winner,
            "end_reason": self.end_reason,
            "score": rules.round_score(self.hands, self.winner)
                     if self.finished and self.winner is not None else None,
        }

    def view(self, seat):
        """What `seat` is allowed to see: its own hand plus everything public. This is the only
        thing a bot is given.

        The opponent's tiles and the boneyard's tiles are not in it, so a bot can't read them,
        and it's a fresh copy, so changing it doesn't change the game.

        my_seat        - the seat this view is for (0 or 1)
        my_hand        - its own tiles
        board          - the tiles on the table, left to right, oriented so neighbours match
        ends           - the two open numbers, (left, right), or None on an empty board
        opponent_tiles - how many tiles the opponent holds (not which)
        boneyard_size  - how many tiles are left to draw (not which)
        current_seat   - whose turn it is
        history        - public events, oldest first:
                         {"seat": s, "action": "play", "tile": (a, b), "side": "L" or "R"}
                         {"seat": s, "action": "draw"}   (which tile was drawn stays secret)
                         {"seat": s, "action": "pass"}
                         {"seat": s, "action": "forfeit", "reason": r}   (see forfeit)
        """
        return {
            "my_seat": seat,
            "my_hand": list(self.players[seat].hand),
            "board": list(self.board),
            "ends": rules.board_ends(self.board),
            "opponent_tiles": len(self.players[1 - seat].hand),
            "boneyard_size": len(self.boneyard),
            "current_seat": self.current_seat,
            "history": [dict(event) for event in self.history],
        }

    # --- actions ---
    def play(self, seat, tile, side):
        self._check_turn(seat)
        tile = normalize(tile)
        if not self.board and tile != self.opening_tile:
            raise ValueError(f"the game must open with {self.opening_tile}")
        play_move(self.players[seat].hand, self.board, tile, side)
        self.history.append({"seat": seat, "action": "play", "tile": tile, "side": side})
        self.turns.record_play()

        if rules.has_won(self.players[seat].hand):
            self._finish(seat, "domino")
        else:
            self.turns.next_turn()

    def draw(self, seat):
        """Draw one tile. The turn stays with the player so they can play it if it fits."""
        self._check_turn(seat)
        if not self.can_draw(seat):
            raise ValueError("you can only draw when you have no legal move and the boneyard isn't empty")
        tile = draw_tile(self.players[seat].hand, self.boneyard)
        self.history.append({"seat": seat, "action": "draw"})   # no tile: what was drawn is secret
        return tile

    def pass_turn(self, seat):
        self._check_turn(seat)
        if not self.can_pass(seat):
            raise ValueError("you can only pass when you have no legal move and the boneyard is empty")
        self.history.append({"seat": seat, "action": "pass"})
        self.turns.record_pass()
        if self.turns.everyone_passed():
            self._finish(rules.blocked_winner(self.hands), "blocked")
        else:
            self.turns.next_turn()

    def forfeit(self, seat, reason):
        """`seat` loses on the spot. Used by the referee when a bot crashes ("error"), answers
        with an illegal move ("illegal") or takes too long ("timeout")."""
        if self.finished:
            raise ValueError("the game is over")
        self.history.append({"seat": seat, "action": "forfeit", "reason": reason})
        self._finish(1 - seat, reason)

    # --- internals ---
    def _is_turn(self, seat):
        return not self.finished and seat == self.current_seat

    def _check_turn(self, seat):
        if self.finished:
            raise ValueError("the game is over")
        if seat != self.current_seat:
            raise ValueError(f"it is seat {self.current_seat}'s turn, not seat {seat}'s")

    def _finish(self, winner, reason):
        self.finished = True
        self.winner = winner
        self.end_reason = reason
