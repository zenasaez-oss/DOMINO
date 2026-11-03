# Tournament and ranking

Every bot in `domino/bots/` takes part automatically: the website's tournament and the
published ranking both use the registry (`scan()`), so a bot that's merged into `main` is in
both with no other change.

## The format: a round robin

`Tournament` (in `domino/tournament.py`) makes **every bot play every other bot** the same
number of games.

- **Every game goes through the referee** (`play_match`): each bot only sees its view, and a bot
  that crashes, plays an illegal move or runs out of time loses that game.
- **Every deal is played twice, with the seats swapped.** Game 1 is A against B with deal *s*;
  game 2 is B against A with the same deal. Each bot gets the other's hand once, so neither the
  luck of the deal nor the seat favours anyone.
- **The schedule goes round by round**: each round, every pair plays once. The table is fair at
  any moment, which matters on the website, where it fills in game by game.
- **Seeded**: the same seed replays exactly the same tournament.

```python
from domino.bots import find_bots
from domino.tournament import Tournament

tournament = Tournament(find_bots(), games_per_pair=10, seed=0)
tournament.play_all()
for row in tournament.table():
    print(row["rank"], row["name"], row["wins"], row["win_rate"])
```

## The table

| Column | Meaning |
|---|---|
| `played` (PJ) | games played |
| `wins` (G), `ties` (E), `losses` (P) | won, tied (a blocked game with equal dots), lost |
| `points` | dots won: the winner of a game scores the dots left in the loser's hand |
| `win_rate` | `wins / played` |
| `faults` | games lost by breaking the rules (crash, illegal move, timeout) |

Bots are ranked by **win rate**, then by **points** to break ties. The ranking also shows
**head to head**: how each bot did against each other bot.

## The published ranking

On every push to `main`, the [publishing workflow](development.md#automation) runs

```bash
python -m tools.tournament --games 50 --jobs 4 --out _site/web/ranking.json
```

which plays 50 games per pair, each in a worker process, **with the platform's time limit of
5 seconds per move**, and publishes the result with the website. The Ranking page reads that
file. Bots that fail to load are left out and listed under "problems".

To see it on your computer:

```bash
python -m tools.tournament -n 10 --out web/ranking.json     # web/ranking.json is git-ignored
python -m http.server 8001                                  # then open http://localhost:8001/web/#ranking
```

## The tournament on the website

The Torneo page plays the same round robin **in your browser**, with the bots you tick (all of
them by default), one game at a time so the table fills in as it goes. It uses
`session.tournament_start(...)` and `session.tournament_step()` (`web/session.py`).

!!! note "No time limit in the browser"
    Python in the browser can't start threads, which the referee's clock needs, so the
    website's tournament has no time limit. Crashes and illegal moves are still caught. The
    published ranking is the one that applies the 5-second limit.
