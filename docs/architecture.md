# How it works

```
domino/            the game, as a Python library (no printing, no input)
├── game.py        Game: one game; play / draw / pass, the public history, view(seat)
├── rules.py       what's legal, who opens, who wins
├── board.py, deck.py, hand.py, domino.py, player.py, turn_manager.py
├── referee.py     plays games between bots; a bot that misbehaves loses
└── bots/          the bots
    ├── base.py        Bot: the class every bot inherits from; check_move
    ├── registry.py    find_bots(): finds every bot in this folder automatically
    └── greedy.py, scoring.py, montecarlo.py, expert.py
web/               the website: index.html, static/app.js, static/style.css, session.py
tools/             developer tools: terminal games, arena.py (bot against bot)
tests/             every test, including the checks every bot must pass
```

## The game engine

`Game` (in `domino/game.py`) holds one game: both hands, the board, the boneyard and whose turn it
is. You change it only through `play`, `draw` and `pass_turn`; an illegal action raises
`ValueError` and changes nothing. It also keeps a **public history** of what happened.

## What a bot sees: the view

A bot never gets the `Game` itself. On its turn it gets `game.view(seat)`: a new dictionary with
its own hand and everything public, and nothing secret.

| In the view | Not in the view |
|---|---|
| its own hand, the board and its two ends | the opponent's tiles |
| how many tiles the opponent holds | the boneyard's tiles and their order |
| how many tiles are left to draw | which tile anyone drew |
| the history of plays, draws and passes | |

The secrets aren't hidden behind a rule ("please don't look"): they're simply not in the data a
bot receives. So a bot can't cheat even if it's written to, and since the view is a copy,
changing it can't change the game. See [What a bot sees and returns](contract.md).

## The bots

Every bot inherits from `Bot` (`domino/bots/base.py`), which is an *abstract base class*: it lists
the methods every bot must write, and Python refuses to create a bot that forgot one, before any
game starts. See [Our bots](bots.md).

`find_bots()` finds every bot in `domino/bots/` by itself, so **adding a bot is adding a file**.
Broken files, incomplete bots and two bots with the same name are reported, not skipped silently.

## The referee

`play_match(BotA, BotB, seed, time_limit)` (in `domino/referee.py`) plays one full game:

1. It builds each bot with `create(seat, seed)`.
2. On each turn it gives the bot only its view and the list of legal moves.
3. It checks the answer, and draws or passes for the bot when it has no legal move.

A bot that misbehaves **loses on the spot**, the other bot wins, and nothing else breaks:

| Reason | When |
|---|---|
| `"error"` | it raised an exception (while being created, choosing a move, or watching the opponent) |
| `"illegal"` | it returned something that isn't one of its legal moves |
| `"timeout"` | it took longer than the time limit (`STANDARD_TIME_LIMIT`, 5 seconds per action, in the bot tests) |

**Seeds.** The same seed replays exactly the same game: it fixes the deal, and each bot gets its
own seed from it through `create`, for its own randomness. That makes games reproducible (to
find a bug), comparisons fair, and tests independent of luck.

!!! note "Two limits of the time limit"
    - Python can't force a thread to stop. A bot stuck in an endless loop loses and the game
      goes on, but the loop keeps running in the background until the program ends. A
      tournament should run each game in its own process.
    - The website has no time limit: Python in the browser (Pyodide) can't start threads, which
      the clock needs. Crashes and illegal moves are still caught there.

## The website

The website is a static page on GitHub Pages: there's no server. The browser downloads
[Pyodide](https://pyodide.org) (Python compiled for the browser) and the project's Python files,
so the page runs **the same engine and the same bots** as everything else.

```
click → app.js → session.py (in Pyodide) → Game and the bot → JSON → app.js redraws the page
```

`web/session.py` is the bridge: it runs the bot's turns through the referee, keeps a log for the
page, hides the bot's tiles until the game ends, and answers in JSON.

## Automation (GitHub Actions)

| Workflow | When | What |
|---|---|---|
| `.github/workflows/tests.yml` | every pull request, and every push to `main` | runs every test, including the checks every bot must pass |
| `.github/workflows/pages.yml` | every push to `main` | runs the tests, then publishes the website |
