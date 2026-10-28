"""Developer tool: make two bots play many games against each other and count who wins.

Not part of the game logic. Every game goes through the referee (domino/referee.py): each bot
only sees its view, and a bot that crashes, plays illegally or runs out of time loses that game.
The bots swap seats every other game and the games are seeded, so a result can be reproduced
exactly.

Run from the project folder:
    python -m tools.arena montecarlo scoring -n 200
    python -m tools.arena scoring heavy -n 2000 --jobs 2 --time-limit 1
Bots: every bot in domino/bots/, found automatically. Write its name in lower case without
spaces (greedy, scoring, montecarlo, expert); "heavy" also works for the greedy bot.
"""
import argparse
import math
from multiprocessing import Pool

from domino.bots import find_bots
from domino.referee import play_match


def key(name):
    """How a bot's name is written on the command line: "Monte Carlo" -> "montecarlo"."""
    return name.lower().replace(" ", "").replace("-", "").replace("_", "")


def bots_by_key():
    bots = {key(name): cls for name, cls in find_bots().items()}
    if "greedy" in bots:
        bots.setdefault("heavy", bots["greedy"])   # the name it had before the registry
    return bots


def bot_class(name):
    bots = bots_by_key()
    if key(name) not in bots:
        raise SystemExit(f"unknown bot '{name}' (use {', '.join(sorted(bots))})")
    return bots[key(name)]


def play_game(names, seed, options=None, time_limit=None):
    """Play one game. names = (bot at seat 0, bot at seat 1).
    Returns (winner seat or None, points, seat that misbehaved or None)."""
    result = play_match(bot_class(names[0]), bot_class(names[1]), seed=seed, time_limit=time_limit,
                        options=options or ({}, {}))
    return result.winner, result.score, (result.fault or {}).get("seat")


def _job(args):
    a, b, i, seed, opts_a, opts_b, time_limit = args
    if i % 2 == 0:                      # bot A sits in seat 0
        winner, pts, faulty = play_game((a, b), seed + i, (opts_a, opts_b), time_limit)
        seat_of = {0: "a", 1: "b", None: "tie"}
    else:                               # bot A sits in seat 1
        winner, pts, faulty = play_game((b, a), seed + i, (opts_b, opts_a), time_limit)
        seat_of = {0: "b", 1: "a", None: "tie"}
    return seat_of[winner], pts, (seat_of[faulty] if faulty is not None else None)


def run(a, b, games, seed=0, jobs=1, opts_a=None, opts_b=None, time_limit=None):
    """Returns dict with wins for a, wins for b, ties, total points won by each, and how many
    games each lost by misbehaving (faults_a, faults_b)."""
    bot_class(a), bot_class(b)          # unknown names fail here, before any game starts
    tasks = [(a, b, i, seed, opts_a or {}, opts_b or {}, time_limit) for i in range(games)]
    if jobs > 1:
        with Pool(jobs) as pool:
            results = pool.map(_job, tasks, chunksize=max(1, games // (jobs * 8)))
    else:
        results = [_job(t) for t in tasks]
    out = {"a": 0, "b": 0, "tie": 0, "points_a": 0, "points_b": 0, "faults_a": 0, "faults_b": 0}
    for who, pts, faulty in results:
        out[who] += 1
        if who in ("a", "b"):
            out["points_" + who] += pts
        if faulty is not None:
            out["faults_" + faulty] += 1
    return out


def summary(a, b, games, r):
    decided = r["a"] + r["b"]
    rate = r["a"] / decided if decided else 0.5
    margin = 1.96 * math.sqrt(rate * (1 - rate) / decided) if decided else 0
    return (f"{a} vs {b}: {games} games -> {a} wins {r['a']}, {b} wins {r['b']}, ties {r['tie']}\n"
            f"  {a} win rate {rate * 100:.1f}% (+/- {margin * 100:.1f}% at 95% confidence)"
            f" | points: {a} {r['points_a']}, {b} {r['points_b']}"
            + (f"\n  games lost by misbehaving: {a} {r['faults_a']}, {b} {r['faults_b']}"
               if r["faults_a"] or r["faults_b"] else ""))


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
    parser.add_argument("--time-limit", type=float, default=None,
                        help="seconds a bot may take per move; slower loses the game (default: no limit)")
    args = parser.parse_args()
    opts = {"samples": args.samples} if args.samples else {}
    if args.margin is not None:
        opts["margin"] = args.margin
    if args.policy:
        opts["policy"] = args.policy
    mc = key("Monte Carlo")
    r = run(args.bot_a, args.bot_b, args.games, args.seed, args.jobs,
            opts if key(args.bot_a) == mc else {}, opts if key(args.bot_b) == mc else {}, args.time_limit)
    print(summary(args.bot_a, args.bot_b, args.games, r))


if __name__ == "__main__":
    main()
