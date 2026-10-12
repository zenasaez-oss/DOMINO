"""Turn order: whose turn it is and counting passes."""


class TurnManager:
    def __init__(self, n_players, first_seat=0):
        self.n_players = n_players
        self.current = first_seat
        self.passes_in_a_row = 0

    def next_turn(self):
        self.current = (self.current + 1) % self.n_players

    def record_play(self):
        self.passes_in_a_row = 0

    def record_pass(self):
        self.passes_in_a_row += 1

    def everyone_passed(self):
        """True once every player has passed in a row -> the game is blocked."""
        return self.passes_in_a_row >= self.n_players
