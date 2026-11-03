import json
import unittest
from collections import Counter
from itertools import combinations

from domino.bots import Bot, GreedyBot, ScoringBot
from domino.referee import STANDARD_TIME_LIMIT
from domino.tournament import Tournament, schedule
from tools.tournament import run


class Cheater(Bot):
    @classmethod
    def get_name(cls):
        return "Cheater"

    @classmethod
    def get_authors(cls):
        return ["Test"]

    @classmethod
    def get_description(cls):
        return "Always answers with a tile that doesn't exist."

    def choose(self, view, moves):
        return ((9, 9), "L")


BOTS = {"Greedy": GreedyBot, "Scoring": ScoringBot, "Cheater": Cheater}


class TestSchedule(unittest.TestCase):
    def test_every_pair_plays_the_same_number_of_games(self):
        games = schedule(list(BOTS), games_per_pair=4)
        pairs = Counter(frozenset(g[:2]) for g in games)
        self.assertEqual(set(pairs), {frozenset(p) for p in combinations(BOTS, 2)})
        self.assertEqual(set(pairs.values()), {4})

    def test_each_deal_is_played_twice_with_the_seats_swapped(self):
        games = schedule(["A", "B"], games_per_pair=4, seed=10)
        self.assertEqual(games, [("A", "B", 10), ("B", "A", 10), ("A", "B", 12), ("B", "A", 12)])

    def test_every_pair_plays_once_per_round(self):
        games = schedule(list(BOTS), games_per_pair=2)
        first_round = games[:3]
        self.assertEqual(len({frozenset(g[:2]) for g in first_round}), 3)


class TestTournament(unittest.TestCase):
    def setUp(self):
        self.tournament = Tournament(BOTS, games_per_pair=2, seed=3)
        self.tournament.play_all()

    def test_every_game_is_counted_once(self):
        t = self.tournament
        self.assertTrue(t.finished)
        self.assertEqual(t.played, 6)
        rows = t.table()
        self.assertEqual(sum(r["played"] for r in rows), 2 * t.played)
        self.assertEqual(sum(r["wins"] for r in rows), sum(r["losses"] for r in rows))
        for r in rows:
            self.assertEqual(r["played"], r["wins"] + r["losses"] + r["ties"])

    def test_a_cheater_loses_every_game_and_is_last(self):
        rows = self.tournament.table()
        cheater = next(r for r in rows if r["name"] == "Cheater")
        self.assertEqual((cheater["wins"], cheater["losses"], cheater["faults"]), (0, 4, 4))
        self.assertEqual(cheater["rank"], 3)

    def test_the_table_is_sorted_and_says_who_the_bots_are(self):
        rows = self.tournament.table()
        self.assertEqual([r["rank"] for r in rows], [1, 2, 3])
        rates = [r["win_rate"] for r in rows]
        self.assertEqual(rates, sorted(rates, reverse=True))
        self.assertEqual(rows[-1]["authors"], ["Test"])

    def test_head_to_head_adds_up(self):
        h2h = self.tournament.head_to_head
        for a, b in combinations(BOTS, 2):
            self.assertEqual(h2h[a][b]["played"], 2)
            self.assertLessEqual(h2h[a][b]["wins"] + h2h[b][a]["wins"], 2)

    def test_the_same_seed_gives_the_same_tournament(self):
        again = Tournament(BOTS, games_per_pair=2, seed=3)
        again.play_all()
        self.assertEqual(again.table(), self.tournament.table())

    def test_needs_two_bots_and_at_least_one_game(self):
        with self.assertRaises(ValueError):
            Tournament({"Greedy": GreedyBot})
        with self.assertRaises(ValueError):
            Tournament(BOTS, games_per_pair=0)


class TestPublishedRanking(unittest.TestCase):
    def test_the_ranking_file_has_what_the_page_shows(self):
        ranking = run(["greedy", "scoring"], games_per_pair=2)
        json.dumps(ranking)                                   # it can be written as JSON
        self.assertEqual(sorted(r["name"] for r in ranking["bots"]), ["Greedy", "Scoring"])
        self.assertEqual(ranking["time_limit"], STANDARD_TIME_LIMIT)
        self.assertEqual(sum(r["played"] for r in ranking["bots"]), 4)
        for key in ("generated", "games_per_pair", "head_to_head", "problems"):
            self.assertIn(key, ranking)


if __name__ == "__main__":
    unittest.main()
