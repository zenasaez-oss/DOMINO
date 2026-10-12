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
PLAYER_OPTIONS = (2, 3, 4)
MAX_PIP = 6          # double-six set, 28 tiles
TILES_PER_PLAYER = 7  # TODO: revisit - with 4 players this deals all 28 tiles, boneyard is empty


def check_player_count(n_players):
    if n_players not in PLAYER_OPTIONS:
        raise ValueError(f"players must be one of {PLAYER_OPTIONS}, got {n_players}")


def new_game(n_players):
    """Shuffle a double-six set and deal 7 tiles each. Returns (hands, boneyard, board)."""
    check_player_count(n_players)
    hands, boneyard = deal(shuffled_set(MAX_PIP), n_players, TILES_PER_PLAYER)
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
    """One round of classic domino. Players are referred to by seat number (0, 1, 2, ...).

    Each turn the current player does one of:
      play(seat, tile, side)  - if they have a legal move
      draw(seat)              - if they have no legal move and the boneyard isn't empty
      pass_turn(seat)         - if they have no legal move and the boneyard is empty
    Illegal actions raise ValueError and change nothing.
    """

    def __init__(self, players):
        check_player_count(len(players))
        self.players = players
        hands, self.boneyard, self.board = new_game(len(players))
        for player, hand in zip(players, hands):
            player.hand = hand

        first_seat, self.opening_tile = rules.first_player(self.hands)
        self.turns = TurnManager(len(players), first_seat)
        self.finished = False
        self.winner = None   # seat, or None if a blocked game ended in a tie
        self.end_reason = None  # "domino" (someone went out) or "blocked"

    @classmethod
    def with_n_players(cls, n_players):
        """Quick setup with placeholder players, handy for testing."""
        return cls([Player(id=str(i), name=f"Player {i}") for i in range(n_players)])

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

    # --- actions ---
    def play(self, seat, tile, side):
        self._check_turn(seat)
        tile = normalize(tile)
        if not self.board and tile != self.opening_tile:
            raise ValueError(f"the game must open with {self.opening_tile}")
        play_move(self.players[seat].hand, self.board, tile, side)
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
        return draw_tile(self.players[seat].hand, self.boneyard)

    def pass_turn(self, seat):
        self._check_turn(seat)
        if not self.can_pass(seat):
            raise ValueError("you can only pass when you have no legal move and the boneyard is empty")
        self.turns.record_pass()
        if self.turns.everyone_passed():
            self._finish(rules.blocked_winner(self.hands), "blocked")
        else:
            self.turns.next_turn()

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
