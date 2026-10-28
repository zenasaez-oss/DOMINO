# What a bot sees and returns

This is the full contract between the game and a bot: what the bot must write, when it's called,
what it receives, what it must return, and what happens if it breaks the rules.

## What a bot must write

Every bot inherits from `Bot` (`from domino.bots import Bot`) and writes four methods:

| Method | Kind | Returns |
|---|---|---|
| `get_name()` | classmethod | a short, **unique** name, e.g. `"Monte Carlo"` |
| `get_authors()` | classmethod | a non-empty list of names |
| `get_description()` | classmethod | one or two sentences on its strategy |
| `choose(view, moves)` | method | one of `moves` |

They're *abstract*: a bot that forgets one can't be created at all, so the mistake shows up
straight away, with the name of the missing method, instead of in the middle of a game.

Optional, with defaults in `Bot`:

| Method | Default | Override it to... |
|---|---|---|
| `create(seat, seed=None, **options)` | `cls(seat, **options)` | use the seed for your randomness, or pass settings |
| `observe_opponent_turn(ends, draws, played)` | does nothing | be told about each opponent turn (the same information is also in `view["history"]`) |

If your bot writes its own `__init__`, its first parameter must be the seat.

## When it's called

```
one game:  BotClass.create(seat, seed)        → a fresh bot, for this game only
each turn: if it has a legal move → bot.choose(view, moves)
           if not → the game draws for it until it can play, or passes when the boneyard is empty
```

A new bot is created for every game, so nothing it remembers carries over from one game to the
next.

## What it receives

### `view`: what a player at the table can see

| Key | Example | Meaning |
|---|---|---|
| `my_seat` | `1` | the bot's seat (0 or 1) |
| `my_hand` | `[(2, 5), (6, 6)]` | its own tiles |
| `board` | `[(1, 3), (3, 3), (3, 6)]` | the line of tiles, left to right, turned so neighbours match |
| `ends` | `(1, 6)` | the two open numbers, `(left, right)`; `None` on an empty board |
| `opponent_tiles` | `5` | how many tiles the opponent holds |
| `boneyard_size` | `12` | how many tiles are left to draw |
| `current_seat` | `1` | whose turn it is |
| `history` | see below | everything public that happened, oldest first |

`history` entries:

```python
{"seat": 0, "action": "play", "tile": (6, 6), "side": "R"}
{"seat": 1, "action": "draw"}                          # which tile was drawn stays secret
{"seat": 1, "action": "pass"}
```

**Not in the view, ever:** the opponent's tiles, the boneyard's tiles or their order, and which
tile anyone drew. The view is a fresh copy, so changing it doesn't change the game.

!!! tip "Reading the opponent"
    A `draw` or `pass` means the opponent had no tile with either open number at that moment.
    Careful: when they draw, they keep the tiles that didn't fit, which may hold numbers you
    thought they lacked earlier.

### `moves`: every legal move

A list of `(tile, side)`, with `side` `"L"` or `"R"`:

```python
[((6, 2), "R"), ((1, 4), "L"), ((1, 6), "L"), ((1, 6), "R")]
```

It holds every legal move and only legal moves. When both ends show the same number, each tile is
listed once. On the first move of the game it's just the opening tile.

## What it must return

**Exactly one element of `moves`, as given.** `((6, 2), "R")` is right; `((2, 6), "R")`,
`[(6, 2), "R"]`, `((6, 2), "right")` and `None` are all illegal. Returning an element of `moves`
can never be wrong.

## The rules, and what happens if they're broken

Games are run by the referee (`domino/referee.py`). A bot that breaks a rule **loses that game on
the spot**, the other player wins, and nothing else breaks.

| Rule | If broken | End reason |
|---|---|---|
| Don't raise an exception (in `create`, `choose` or `observe_opponent_turn`) | loses | `"error"` |
| Return one of `moves` | loses | `"illegal"` |
| Answer within the time limit (`STANDARD_TIME_LIMIT`: 5 seconds per action in the bot tests) | loses | `"timeout"` |
| Use only what you're given | can't be broken: there's nothing else to read | |

Also expected, and checked when a pull request is reviewed:

- **A unique name**, at least one author, and a description (also checked by the bot tests).
- **Only the Python standard library.** The website runs bots in the browser (Pyodide), where
  other packages may not be available.
- **No printing, no files, no network.**
- **Repeatable when seeded** (recommended): if your bot uses randomness, take it from the seed
  `create` receives, so the same seed replays the same game.
