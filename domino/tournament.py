"""A round robin: every bot plays every other bot the same number of games.

Every game goes through the referee (play_match), so each bot only sees its view and a bot that
crashes, plays illegally or runs out of time loses that game. Every deal is played twice with
the seats swapped, so neither the luck of the deal nor the seat favours anyone.

    from domino.bots import find_bots
    from domino.tournament import Tournament

    tournament = Tournament(find_bots(), games_per_pair=10)
    tournament.play_all()
    tournament.table()      # [{"rank": 1, "name": "Expert", "wins": ..., "win_rate": ...}, ...]

The website plays it one game at a time (play_next) to show the table filling in; the published
ranking is the same tournament, played on GitHub by tools/tournament.py.
"""
from itertools import combinations

from .bots.registry import describe
from .referee import play_match


def schedule(names, games_per_pair, seed=0):
    """Every game as (bot in seat 0, bot in seat 1, seed), round by round: in each round every
    pair plays once, so the table is fair at any moment. Games come in twos: the same deal (seed)
    with the seats swapped."""
    games = []
    for i in range(games_per_pair):
        deal = seed + i - i % 2
        for a, b in combinations(names, 2):
            games.append((a, b, deal) if i % 2 == 0 else (b, a, deal))
    return games


class Tournament:
    """bots: {name: bot class}. time_limit: seconds per action (None in the browser, which has
    no threads for the referee's clock)."""

    def __init__(self, bots, games_per_pair=2, seed=0, time_limit=None):
        if len(bots) < 2:
            raise ValueError("a tournament needs at least two bots")
        if games_per_pair < 1:
            raise ValueError("each pair must play at least one game")
        self.bots = dict(bots)
        self.games_per_pair = games_per_pair
        self.seed = seed
        self.time_limit = time_limit
        self.games = schedule(list(self.bots), games_per_pair, seed)
        self.played = 0
        self.last = None              # the latest game, for the page to show
        self.stats = {name: {"played": 0, "wins": 0, "losses": 0, "ties": 0, "points": 0, "faults": 0}
                      for name in self.bots}
        # head_to_head[a][b]: how a did against b
        self.head_to_head = {a: {b: {"played": 0, "wins": 0} for b in self.bots if b != a}
                             for a in self.bots}

    @property
    def finished(self):
        return self.played == len(self.games)

    def play_next(self):
        """Play the next game of the schedule and count it. Returns its MatchResult."""
        a, b, seed = self.games[self.played]
        result = play_match(self.bots[a], self.bots[b], seed=seed, time_limit=self.time_limit)
        self.record(winner=result.winner, score=result.score, end_reason=result.end_reason,
                    fault=result.fault)
        return result

    def play_all(self):
        while not self.finished:
            self.play_next()

    def record(self, winner, score, end_reason, fault=None):
        """Count the next game of the schedule. Games played elsewhere (e.g. in other processes)
        are counted here in schedule order."""
        seats = self.games[self.played][:2]
        for seat, name in enumerate(seats):
            self.stats[name]["played"] += 1
            self.head_to_head[name][seats[1 - seat]]["played"] += 1
        if winner is None:
            for name in seats:
                self.stats[name]["ties"] += 1
        else:
            won, lost = seats[winner], seats[1 - winner]
            self.stats[won]["wins"] += 1
            self.stats[won]["points"] += score
            self.stats[lost]["losses"] += 1
            self.head_to_head[won][lost]["wins"] += 1
        if fault:
            self.stats[seats[fault["seat"]]]["faults"] += 1
        self.last = {"seats": list(seats), "winner": None if winner is None else seats[winner],
                     "score": score, "end_reason": end_reason,
                     "fault": fault["reason"] if fault else None}
        self.played += 1

    def table(self):
        """The standings, best first: by share of games won, then by points scored."""
        rows = []
        for name, s in self.stats.items():
            rate = s["wins"] / s["played"] if s["played"] else 0.0
            rows.append({**describe(self.bots[name]), "name": name, **s, "win_rate": round(rate, 4)})
        rows.sort(key=lambda r: (-r["win_rate"], -r["points"], r["name"].lower()))
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank
        return rows

    def to_dict(self):
        return {"played": self.played, "total": len(self.games), "finished": self.finished,
                "games_per_pair": self.games_per_pair, "seed": self.seed, "time_limit": self.time_limit,
                "last": self.last, "table": self.table(), "head_to_head": self.head_to_head}
