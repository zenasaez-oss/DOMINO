"""Rough scratch domino game (block/draw style) for n players.

Run:  python logic.py            -> watch n bots play
      python logic.py 3 --human  -> 3 players, you are player 0
"""
import random
import sys
from collections import deque


def make_set(max_pip):
    return [(a, b) for a in range(max_pip + 1) for b in range(a, max_pip + 1)]


def pips(tile):
    return tile[0] + tile[1]


class Game:
    def __init__(self, n_players, hand_size=None, max_pip=None, human=False, strategies=None):
        if n_players < 2:
            raise ValueError("need at least 2 players")
        # double-six (28 tiles) for up to 4 players, double-nine (55) beyond that
        self.max_pip = max_pip if max_pip is not None else (6 if n_players <= 4 else 9)
        self.n = n_players
        self.human = human

        tiles = make_set(self.max_pip)
        random.shuffle(tiles)
        if hand_size is None:
            hand_size = 7 if n_players <= 4 else 5 if self.max_pip == 9 else 7
        if hand_size * n_players > len(tiles):
            raise ValueError("not enough tiles for that many players")

        self.hands = [tiles[i * hand_size:(i + 1) * hand_size] for i in range(n_players)]
        self.boneyard = tiles[n_players * hand_size:]
        self.line = deque()  # tiles on the table, oriented left->right
        # strategies[p](game, player, hand, moves) -> (tile, side); None = default greedy
        self.strategies = strategies or [None] * n_players
        # numbers each player is known NOT to have (seen when they draw or pass)
        self.lacks = [set() for _ in range(n_players)]

    # --- board helpers ---
    def ends(self):
        if not self.line:
            return None
        return self.line[0][0], self.line[-1][1]

    def legal_moves(self, hand):
        """Return list of (tile, side) where side is 'L' or 'R'."""
        if not self.line:
            return [(t, "R") for t in hand]
        left, right = self.ends()
        moves = []
        for t in hand:
            if left in t:
                moves.append((t, "L"))
            if right in t and left != right:  # same end value -> one move is enough
                moves.append((t, "R"))
        return moves

    def place(self, tile, side):
        a, b = tile
        if not self.line:
            self.line.append((a, b))
            return
        left, right = self.ends()
        if side == "L":
            self.line.appendleft((a, b) if b == left else (b, a))
        else:
            self.line.append((a, b) if a == right else (b, a))

    def board_str(self):
        return " ".join(f"[{a}|{b}]" for a, b in self.line) or "(empty)"

    # --- players ---
    def bot_choose(self, hand, moves):
        # greedy: dump the heaviest tile, prefer doubles on ties
        return max(moves, key=lambda m: (pips(m[0]), m[0][0] == m[0][1]))

    def human_choose(self, hand, moves):
        print(f"\nBoard: {self.board_str()}")
        print("Your hand:", " ".join(f"[{a}|{b}]" for a, b in hand))
        for i, (t, side) in enumerate(moves):
            print(f"  {i}: {t} on {side}")
        while True:
            choice = input("Pick move #: ").strip()
            if choice.isdigit() and int(choice) < len(moves):
                return moves[int(choice)]
            print("invalid")

    # --- game flow ---
    def first_player(self):
        # highest double starts; if no doubles, highest tile
        best = None
        for p, hand in enumerate(self.hands):
            for t in hand:
                key = (t[0] == t[1], pips(t))
                if best is None or key > best[0]:
                    best = (key, p, t)
        return best[1], best[2]

    def play(self, verbose=True):
        current, opener = self.first_player()
        self.hands[current].remove(opener)
        self.place(opener, "R")
        if verbose:
            print(f"Player {current} opens with {opener}")
        current = (current + 1) % self.n
        passes = 0

        while True:
            hand = self.hands[current]
            moves = self.legal_moves(hand)

            if not moves and self.line:
                self.lacks[current].update(self.ends())

            # draw from boneyard until something fits
            while not moves and self.boneyard:
                drawn = self.boneyard.pop()
                hand.append(drawn)
                if verbose:
                    print(f"Player {current} draws")
                moves = self.legal_moves(hand)

            if not moves:
                passes += 1
                if verbose:
                    print(f"Player {current} passes")
                if passes >= self.n:
                    return self.blocked_winner(verbose)
            else:
                passes = 0
                is_human = self.human and current == 0
                if is_human:
                    tile, side = self.human_choose(hand, moves)
                elif self.strategies[current]:
                    tile, side = self.strategies[current](self, current, hand, moves)
                else:
                    tile, side = self.bot_choose(hand, moves)
                hand.remove(tile)
                self.place(tile, side)
                if verbose:
                    print(f"Player {current} plays {tile} on {side}  ->  {self.board_str()}")
                if not hand:
                    if verbose:
                        print(f"\nPlayer {current} dominoes! Wins.")
                    return current

            current = (current + 1) % self.n

    def blocked_winner(self, verbose):
        totals = [sum(pips(t) for t in h) for h in self.hands]
        winner = min(range(self.n), key=lambda p: totals[p])
        if verbose:
            print("\nGame blocked. Pip totals:", totals)
            print(f"Player {winner} wins with lowest count.")
        return winner


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4
    human = "--human" in sys.argv
    Game(n, human=human).play()
