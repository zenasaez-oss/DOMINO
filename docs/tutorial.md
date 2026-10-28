# Tutorial: write your first bot

By the end of this page you'll have written a domino bot, tested it, played it against ours, and
sent it to us with a pull request. You won't touch the game's code: a bot is one new file.

**You need:** a GitHub account, [git](https://git-scm.com/), and Python 3.10 or newer.

## 1. Get your own copy of the project

1. On [github.com/zenasaez-oss/DOMINO](https://github.com/zenasaez-oss/DOMINO), click **Fork**.
   This makes your own copy of the project on your GitHub account.
2. Download your fork to your computer and create a branch for your bot:

```bash
git clone https://github.com/YOUR-USERNAME/DOMINO.git
cd DOMINO
git switch -c my-bot
```

3. Check everything works by running the tests:

```bash
python -m unittest discover -s tests -t .
```

You should see `OK` at the end.

## 2. Create your bot's file

Create a new file in `domino/bots/`, named after your team so it can't clash with anyone
else's, e.g. `domino/bots/team7.py`:

```python
from domino.bots import Bot


class DoublesFirstBot(Bot):
    """Plays a double whenever it can, otherwise its heaviest tile."""

    @classmethod
    def get_name(cls):
        return "Doubles First"            # unique: it's shown in menus and the ranking

    @classmethod
    def get_authors(cls):
        return ["Your name", "Your teammate"]

    @classmethod
    def get_description(cls):
        return "Plays a double whenever it can, otherwise its heaviest tile."

    def choose(self, view, moves):
        doubles = [move for move in moves if move[0][0] == move[0][1]]
        candidates = doubles or moves
        return max(candidates, key=lambda move: sum(move[0]))
```

That's a complete bot. The four methods are required: if one is missing, Python refuses to create
your bot and tells you which one.

- **`get_name`, `get_authors`, `get_description`** say who your bot is. They're *classmethods*,
  so the game can read them without creating your bot.
- **`choose(view, moves)`** is how it plays. It's called on your bot's turn, only when it has at
  least one legal move (drawing and passing are done for it).

## 3. Use what your bot can see

`moves` lists every legal move as `(tile, side)`, e.g. `((6, 2), "R")`. **Return exactly one of
them**, as given.

`view` is everything a player at the table can see:

```python
def choose(self, view, moves):
    view["my_hand"]         # [(2, 5), (6, 6), ...]  your tiles
    view["board"]           # [(1, 3), (3, 3), (3, 6)]  left to right
    view["ends"]            # (1, 6)  the two open numbers
    view["opponent_tiles"]  # 5  how many tiles the opponent holds (not which!)
    view["boneyard_size"]   # 12  how many tiles are left to draw
    view["history"]         # every play, draw and pass so far
    ...
```

For example, a bot that keeps its options open: it prefers moves that leave open numbers it
still holds, so it won't be forced to draw next turn.

```python
def choose(self, view, moves):
    def follow_ups(move):
        tile, side = move
        left, right = view["ends"] or tile          # the ends before this move (none on an empty board)
        if side == "L":
            new_end = tile[0] if tile[1] == left else tile[1]
        else:
            new_end = tile[1] if tile[0] == right else tile[0]
        rest = [t for t in view["my_hand"] if t != tile]
        return sum(new_end in t for t in rest)      # tiles I could play on that end next

    return max(moves, key=lambda move: (follow_ups(move), sum(move[0])))
```

All the fields, including the `history` of plays, draws and passes, are explained in
[What a bot sees and returns](contract.md).

## 4. Test your bot

Every bot in `domino/bots/` is found automatically and gets its own set of checks. Run them:

```bash
python -m unittest tests.test_all_bots -v
```

Look for the lines with your bot's class name, e.g. `TestDoublesFirstBot`. Your bot passes if:

- its file imports, it writes every required method, and its name is unique;
- it has a name, at least one author and a description;
- `create(seat, seed)` builds it for either seat;
- it plays full games in both seats, against another bot and against itself, without crashing,
  returning an illegal move, or taking more than 5 seconds for a move.

If something's wrong, the message says what, e.g.:

```
Doubles First lost by illegal: ((6, 2), 'R') is not one of the legal moves [((2, 6), 'R')]
```

That one means the tile was written back to front: return the element of `moves` itself.

## 5. Play it against our bots

```bash
python -m tools.arena doublesfirst greedy -n 200
python -m tools.arena doublesfirst scoring -n 200
```

Write your bot's name in lower case without spaces. The arena plays 200 games, swapping seats,
and shows your win rate. Domino has a lot of luck, so use a few hundred games before trusting a
result.

!!! tip "If your bot uses randomness"
    Make it repeatable: the referee gives every bot a seed through `create`. Override it to pass
    the seed on, and use your own `random.Random(seed)`:

    ```python
    import random

    class MyRandomBot(Bot):
        ...                                   # get_name, get_authors, get_description as before

        @classmethod
        def create(cls, seat, seed=None, **options):
            bot = cls(seat)
            bot.rng = random.Random(seed)     # its own random numbers, seeded by the referee
            return bot

        def choose(self, view, moves):
            return self.rng.choice(moves)
    ```

    The same seed then replays exactly the same game, which makes your bot much easier to debug.

## 6. Send it to us

1. Commit and push your branch to **your fork**:

```bash
git add domino/bots/team7.py
git commit -m "Add Doubles First bot"
git push -u origin my-bot
```

2. On GitHub, open your fork and click **Compare & pull request**. Make sure the pull request goes
   to `zenasaez-oss/DOMINO`, branch `main`.
3. The tests run automatically on your pull request. A green tick means your bot passed every
   check; a red cross links to what failed.
4. We review it and, if everything's fine, merge it. From then on your bot is part of the arena
   and the tournament.

## Checklist before opening the pull request

- [ ] One new file in `domino/bots/`, and **no other changes** (not the game, not other bots, not
      the tests).
- [ ] A unique name, at least one author, and a description of the strategy.
- [ ] `choose` returns one of `moves`, as given.
- [ ] Only the Python standard library (the website runs bots in the browser, where other
      packages may not be available).
- [ ] No printing, no files, no network.
- [ ] `python -m unittest discover -s tests -t .` ends with `OK`.
