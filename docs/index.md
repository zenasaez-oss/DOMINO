# Domino

Classic two-player domino: one line of tiles with two open ends, played with a double-six set.

- **Play it** in your browser, against a bot of your choice, with nothing to install:
  [zenasaez-oss.github.io/DOMINO](https://zenasaez-oss.github.io/DOMINO/)
- **Write your own bot** and send it to us with a pull request:
  [Tutorial: write your first bot](tutorial.md)
- **Source code:** [github.com/zenasaez-oss/DOMINO](https://github.com/zenasaez-oss/DOMINO)

## What's in this project

| Part | What it is |
|---|---|
| The game (`domino/`) | The rules engine, as an installable Python library. A full game can be played from code, with no interface |
| The bots (`domino/bots/`) | Four bots, from easy to superhard, and the `Bot` class every bot is built on |
| The referee (`domino/referee.py`) | Plays games between bots and makes sure none can break them |
| The website (`web/`) | A page where a person plays a full game against a bot. It runs the same Python engine in the browser |

## Quick start

```bash
git clone https://github.com/zenasaez-oss/DOMINO.git
cd DOMINO
pip install .                                  # the game only needs Python 3.10+
python -m unittest discover -s tests -t .      # run every test
python -m tools.arena scoring greedy -n 200    # two bots, 200 games
```

Play a game from code:

```python
from domino.bots import find_bots
from domino.referee import play_match

bots = find_bots()                       # every bot in domino/bots/
result = play_match(bots["Scoring"], bots["Greedy"], seed=7)
print(result.winner, result.end_reason, result.score)
```

## Where to go next

- [Rules](rules.md): exactly which domino rules this game uses.
- [How it works](architecture.md): the engine, the bots, the referee and the website, and how they fit.
- [Our bots](bots.md): the four bots you can play against and how they think.
- [What a bot sees and returns](contract.md): the full contract between the game and a bot.
- [API reference](api.md): every class and function a bot author uses.
- [Development](development.md): tests, workflows and the tools for developers.
