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
| `tests/test_rules.py`, `test_game.py`, `test_board.py`, ... | The rules engine |
| `tests/test_montecarlo_bot.py`, `test_expert_bot.py` | Our two strongest bots in detail |
| `tests/test_web_session.py` | The website's bridge to the engine |

## Automation

| Workflow | When | What |
|---|---|---|
| `.github/workflows/tests.yml` | every pull request, every push to `main` | all tests, on Python 3.12 and 3.13 |
| `.github/workflows/pages.yml` | every push to `main` | tests, then publishes the website on GitHub Pages |

The documentation is built by Read the Docs (`.readthedocs.yaml`) on every push to `main`.

## Developer tools

```bash
python main.py                                  # one random game, printed
python -m tools.play_scoring                    # play against a bot in the terminal
python -m tools.arena montecarlo scoring -n 200 --time-limit 5   # bot against bot
```

`tools/` is for developers only: the website and the bots don't depend on it.

## Working on the project

- One branch per piece of work, merged into `main` through a pull request.
- The tests must pass on the pull request before it's merged.
- A new bot is one new file in `domino/bots/` (see the [tutorial](tutorial.md)).
- When a website Python file is added, also add it to `PY_FILES` in `web/static/app.js`, the list
  of files the page loads into the browser.

## Building the docs locally

```bash
mkdocs serve      # then open http://127.0.0.1:8000
mkdocs build      # builds the site into site/ (ignored by git)
```
