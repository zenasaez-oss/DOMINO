"""Developer tool: make two bots play many games against each other and count who wins.

Not part of the game logic. Each game uses the real Game rules; the bots swap seats every other
game and the games are seeded, so a result can be reproduced exactly.

Run from the project folder:
    python -m tools.arena montecarlo scoring -n 200
    python -m tools.arena scoring heavy -n 2000 --jobs 2
Bots: heavy (tools/play.py), scoring (tools/play_scoring.py), montecarlo (tools/play_montecarlo.py)
"""
import argparse
import math
import random
from multiprocessing import Pool

from domino.board import board_ends
from domino.domino import pip_count
from domino.game import Game
from domino.player import Player


class HeavyBot:
    """The simple bot of tools/play.py: always plays its heaviest tile."""

    def __init__(self, seat):
        self.seat = seat

    def choose(self, game, moves):
        return max(moves, key=lambda m: pip_count(m[0]))


def make_bot(name, seat, **options):
    if name == "heavy":
        return HeavyBot(seat)
    if name == "scoring":
        from tools.play_scoring import ScoringBot
        return ScoringBot(seat)
    if name == "montecarlo":
        from tools.play_montecarlo import MonteCarloBot
        return MonteCarloBot(seat, **options)
    raise SystemExit(f"unknown bot '{name}' (use heavy, scoring or montecarlo)")


def play_game(names, seed, options=None):
    """Play one game. names = (bot at seat 0, bot at seat 1). Returns (winner seat or None, points)."""
    random.seed(seed)
    options = options or ({}, {})
    game = Game([Player(id=str(i), name=n, is_bot=True) for i, n in enumerate(names)])
    bots = [make_bot(n, seat, **options[seat]) for seat, n in enumerate(names)]
    while not game.finished:
        seat = game.current_seat
        ends, draws = board_ends(game.board), 0
        while True:
            moves = game.legal_moves(seat)
            if moves:
                tile, side = bots[seat].choose(game, moves)
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
        other = bots[1 - seat]
        if hasattr(other, "observe_opponent_turn"):
            other.observe_opponent_turn(ends, draws, played)
    state = game.state()
    return state["winner"], state["score"] or 0


def _job(args):
    a, b, i, seed, opts_a, opts_b = args
    if i % 2 == 0:                      # bot A sits in seat 0
        winner, pts = play_game((a, b), seed + i, (opts_a, opts_b))
        mine = {0: "a", 1: "b", None: "tie"}[winner]
    else:                               # bot A sits in seat 1
        winner, pts = play_game((b, a), seed + i, (opts_b, opts_a))
        mine = {0: "b", 1: "a", None: "tie"}[winner]
    return mine, pts


def run(a, b, games, seed=0, jobs=1, opts_a=None, opts_b=None):
    """Returns dict with wins for a, wins for b, ties and total points won by each."""
    tasks = [(a, b, i, seed, opts_a or {}, opts_b or {}) for i in range(games)]
    if jobs > 1:
        with Pool(jobs) as pool:
            results = pool.map(_job, tasks, chunksize=max(1, games // (jobs * 8)))
    else:
        results = [_job(t) for t in tasks]
    out = {"a": 0, "b": 0, "tie": 0, "points_a": 0, "points_b": 0}
    for who, pts in results:
        out[who] += 1
        if who in ("a", "b"):
            out["points_" + who] += pts
    return out


def summary(a, b, games, r):
    decided = r["a"] + r["b"]
    rate = r["a"] / decided if decided else 0.5
    margin = 1.96 * math.sqrt(rate * (1 - rate) / decided) if decided else 0
    return (f"{a} vs {b}: {games} games -> {a} wins {r['a']}, {b} wins {r['b']}, ties {r['tie']}\n"
            f"  {a} win rate {rate * 100:.1f}% (+/- {margin * 100:.1f}% at 95% confidence)"
            f" | points: {a} {r['points_a']}, {b} {r['points_b']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bot_a")
    parser.add_argument("bot_b")
    parser.add_argument("-n", "--games", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=1, help="processes to use in parallel")
    parser.add_argument("--policy", default=None, help="Monte Carlo bot: playout policy (light or scoring)")
    parser.add_argument("--margin", type=float, default=None, help="Monte Carlo bot: weight of the dot margin")
    parser.add_argument("--samples", type=int, default=None, help="Monte Carlo bot: opponent hands per decision")
    args = parser.parse_args()
    opts = {"samples": args.samples} if args.samples else {}
    if args.margin is not None:
        opts["margin"] = args.margin
    if args.policy:
        opts["policy"] = args.policy
    r = run(args.bot_a, args.bot_b, args.games, args.seed, args.jobs,
            opts if args.bot_a == "montecarlo" else {}, opts if args.bot_b == "montecarlo" else {})
    print(summary(args.bot_a, args.bot_b, args.games, r))


if __name__ == "__main__":
    main()
