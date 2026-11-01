"""The official tournament: every bot in domino/bots/ against every other, for the ranking.

Not part of the game logic. It plays domino/tournament.py's round robin with the platform's
time limit, each game in a worker process, and writes the standings as JSON. GitHub runs it on
every push to main (.github/workflows/pages.yml) and publishes the file with the website, whose
Ranking page shows it. Bot files that fail to load are left out and listed under "problems".

Run from the project folder:
    python -m tools.tournament                                  # print the table
    python -m tools.tournament -n 20 --jobs 4 --out web/ranking.json
    python -m tools.tournament greedy scoring -n 4              # only some bots
Then `python -m http.server 8001` and http://localhost:8001/web/#ranking shows it locally.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from multiprocessing import Pool

from domino.bots import scan
from domino.referee import STANDARD_TIME_LIMIT, play_match
from domino.tournament import Tournament

from .arena import key

_bots = None   # each worker process finds the bots once


def _play(game):
    """Play one game of the schedule in a worker process; return what Tournament.record needs."""
    global _bots
    if _bots is None:
        _bots, _ = scan()
    a, b, seed, time_limit = game
    result = play_match(_bots[a], _bots[b], seed=seed, time_limit=time_limit)
    return result.winner, result.score, result.end_reason, result.fault


def run(names=None, games_per_pair=10, seed=0, jobs=1, time_limit=STANDARD_TIME_LIMIT):
    """Play the tournament and return the ranking as a dict (what ranking.json holds).
    names: only these bots (written as on the command line, e.g. "montecarlo"); None for all."""
    bots, problems = scan()
    if names:
        wanted = {key(n) for n in names}
        bots = {name: cls for name, cls in bots.items() if key(name) in wanted}
    tournament = Tournament(bots, games_per_pair, seed, time_limit)
    tasks = [(a, b, game_seed, time_limit) for a, b, game_seed in tournament.games]
    if jobs > 1:
        with Pool(jobs) as pool:
            results = pool.map(_play, tasks, chunksize=1)
    else:
        results = map(_play, tasks)
    for winner, score, end_reason, fault in results:   # counted in schedule order
        tournament.record(winner, score, end_reason, fault)
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": os.environ.get("GITHUB_SHA", "")[:7] or None,
        "games_per_pair": games_per_pair,
        "time_limit": time_limit,
        "seed": seed,
        "bots": tournament.table(),
        "head_to_head": tournament.head_to_head,
        "problems": problems,
    }


def summary(ranking):
    lines = [f"{'#':>2}  {'bot':<16}{'played':>7}{'won':>6}{'lost':>6}{'tied':>6}{'points':>8}{'win %':>8}{'faults':>8}"]
    for r in ranking["bots"]:
        lines.append(f"{r['rank']:>2}  {r['name']:<16}{r['played']:>7}{r['wins']:>6}{r['losses']:>6}"
                     f"{r['ties']:>6}{r['points']:>8}{r['win_rate'] * 100:>7.1f}%{r['faults']:>8}")
    lines += [f"left out: {p}" for p in ranking["problems"]]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bots", nargs="*", help="only these bots (default: every bot in domino/bots/)")
    parser.add_argument("-n", "--games", type=int, default=10, help="games per pair of bots (default 10)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="processes in parallel")
    parser.add_argument("--time-limit", type=float, default=STANDARD_TIME_LIMIT,
                        help=f"seconds a bot may take per move (default {STANDARD_TIME_LIMIT})")
    parser.add_argument("--out", help="also write the ranking to this JSON file")
    args = parser.parse_args()
    ranking = run(args.bots, args.games, args.seed, args.jobs, args.time_limit)
    print(summary(ranking))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as file:
            json.dump(ranking, file, ensure_ascii=False, indent=1)
        print(f"written to {args.out}")


if __name__ == "__main__":
    main()
