"""Rough bot strategies for logic.Game.

A strategy is a function (game, player, hand, moves) -> (tile, side).

Run:  python bots.py [n_players] [n_games]   -> medium bot (seat 0) vs greedy bots
"""
import random
import sys

from logic import Game, pips


def greedy_bot(game, player, hand, moves):
    return max(moves, key=lambda m: (pips(m[0]), m[0][0] == m[0][1]))


def random_bot(game, player, hand, moves):
    return random.choice(moves)


def _ends_after(game, tile, side):
    """Board ends if `tile` were played on `side` (without touching the board)."""
    a, b = tile
    if not game.line:
        return a, b
    left, right = game.ends()
    if side == "L":
        new_left = a if b == left else b
        return new_left, right
    new_right = b if a == right else a
    return left, new_right


def _unseen_count(game, hand, value):
    """How many tiles with `value` might still be in opponents' hands or the boneyard."""
    total = game.max_pip + 1  # tiles containing a given number in a full set
    on_board = sum(1 for t in game.line if value in t)
    in_hand = sum(1 for t in hand if value in t)
    return total - on_board - in_hand


def medium_bot(game, player, hand, moves):
    """Heuristic bot: dumps weight, keeps options open, and blocks the next player.

    Each candidate move gets a score made of a few simple factors:
      - pips:     unload heavy tiles (lower count if the game ends blocked)
      - double:   doubles only match one number, so get rid of them early
      - follow:   prefer ends I can still play on next turn
      - variety:  avoid playing my last tile of a number
      - block:    leave ends the next player is known to lack
      - scarcity: when I'm light, push ends whose number is nearly exhausted
    """
    nxt = (player + 1) % game.n

    def score(move):
        tile, side = move
        rest = [t for t in hand if t != tile]
        new_ends = _ends_after(game, tile, side)

        s = pips(tile) * 1.0
        if tile[0] == tile[1]:
            s += 4

        # can I follow up on the ends I'm creating?
        for e in set(new_ends):
            s += 3 * sum(1 for t in rest if e in t)

        # don't throw away the last tile I hold of some number
        for v in set(tile):
            if not any(v in t for t in rest):
                s -= 2

        # next player passed / drew on these numbers before -> likely stuck
        for e in set(new_ends):
            if e in game.lacks[nxt]:
                s += 5

        # blocking pressure: if I'd win a blocked game, choke the board
        others_min = min(len(h) for p, h in enumerate(game.hands) if p != player)
        if len(rest) <= others_min:
            for e in set(new_ends):
                s += 4 - min(4, _unseen_count(game, rest, e))

        # going out is always best
        if not rest:
            s += 1000
        return s + random.random() * 0.1  # tiny noise to break ties

    return max(moves, key=score)


def compare(n_players=4, n_games=2000):
    wins = [0] * n_players
    for _ in range(n_games):
        strategies = [medium_bot] + [greedy_bot] * (n_players - 1)
        wins[Game(n_players, strategies=strategies).play(verbose=False)] += 1
    print(f"{n_players} players, {n_games} games (seat 0 = medium, rest = greedy)")
    for p, w in enumerate(wins):
        label = "medium" if p == 0 else "greedy"
        print(f"  seat {p} ({label}): {w / n_games:.1%}")
    print(f"  fair share would be {1 / n_players:.1%}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    games = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    compare(n, games)
