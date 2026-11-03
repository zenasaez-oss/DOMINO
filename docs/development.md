# Development

## Setting up

```bash
git clone https://github.com/zenasaez-oss/DOMINO.git
cd DOMINO
pip install -e ".[docs]"      # the game (editable) plus the tools to build these docs
```

The game itself only uses the Python standard library; `[docs]` adds MkDocs to build this site.

## Tests

```bash
python -m unittest discover -s tests -t .        # everything
python -m unittest tests.test_all_bots -v        # only the checks every bot must pass
```

| File | Checks |
|---|---|
| `tests/test_all_bots.py` | **Every bot in `domino/bots/`**, found automatically: identity, `create`, full games through the referee in both seats, with the time limit |
| `tests/test_bot_api.py` | The `Bot` class: abstract methods, identity, `check_move`, `create`, `name` |
| `tests/test_view.py` | The view hides every secret, at every turn; the public history |
| `tests/test_referee.py` | Bots that crash, cheat, hang or break while being created lose, and the game still ends |
| `tests/test_registry.py` | Adding a file adds a bot; broken files, incomplete bots and duplicate names are reported |
| `tests/test_tournament.py` | The round robin: fair schedule, every game counted once, cheaters last, the ranking file |
| `tests/test_rules.py`, `test_game.py`, `test_board.py`, ... | The rules engine |
| `tests/test_montecarlo_bot.py`, `test_expert_bot.py` | Our two strongest bots in detail |
| `tests/test_web_session.py` | The website's bridge to the engine: games against any bot, the bot list, the tournament |

## Automation

| Workflow | When | What |
|---|---|---|
| `.github/workflows/tests.yml` | every pull request, every push to `main` | all tests, on Python 3.12 and 3.13 |
| `.github/workflows/pages.yml` | every push to `main` | tests, the [ranking tournament](tournament.md), then publishes the website and the ranking on GitHub Pages |

The documentation is built by Read the Docs (`.readthedocs.yaml`) on every push to `main`.

## Developer tools

```bash
python main.py                                  # one random game, printed
python -m tools.play_scoring                    # play against a bot in the terminal
python -m tools.arena montecarlo scoring -n 200 --time-limit 5   # bot against bot
python -m tools.tournament -n 10 --out web/ranking.json         # every bot against every other
python -m http.server 8001                      # the website: http://localhost:8001/web/
```

Port 8001 rather than 8000, which is often taken by another program (e.g. Apache) on Windows.

`tools/` is for developers only: the website and the bots don't depend on it.

## Working on the project

- One branch per piece of work, merged into `main` through a pull request.
- The tests must pass on the pull request before it's merged.
- A new bot is one new file in `domino/bots/` (see the [tutorial](tutorial.md)).
- A new bot appears on the website, in the tournament and in the ranking by itself. Any other
  new Python file the website needs must be added to `PY_FILES` in `web/static/app.js`, the list
  of files the page loads into the browser.

## Building the docs locally

```bash
mkdocs serve      # then open http://127.0.0.1:8000
mkdocs build      # builds the site into site/ (ignored by git)
```
