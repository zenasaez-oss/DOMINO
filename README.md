# Domino

Game logic for classic domino (one line of play, two open ends), for 2 players.
The game itself is played on a separate platform; this repo is the rules engine it calls.

## Rules used

- Double-six set (28 tiles), 7 tiles per player, 14 left in the boneyard.
- The player with the highest double opens with it. If nobody has a double, the highest tile opens.
- On your turn: play a tile that matches the left or right end. If you can't, draw from the boneyard
  until you can, and pass only when the boneyard is empty.
- The first player to play their last tile wins and scores the dots left in everyone else's hands.
- If every player passes in a row, the game is blocked: the lowest dot total wins, and a tie has no winner.

## Layout

| Path | What it does |
|---|---|
| `domino/domino.py` | Single tile helpers (`is_double`, `pip_count`, `flip`, ...) |
| `domino/deck.py` | Shuffling and dealing |
| `domino/hand.py` | Hand helpers (dot total, highest double) |
| `domino/board.py` | The line of tiles: its ends and placing a tile |
| `domino/player.py` | `Player` (id, name, bot or not, hand) |
| `domino/rules.py` | What's legal, who starts, who wins |
| `domino/turn_manager.py` | Whose turn it is, counting passes |
| `domino/game.py` | `Game`: ties it all together for the platform |
| `main.py` | Developer check: plays one random game and prints the result |
| `tools/play.py` | Developer tool: play a game in the terminal against a simple bot |
| `tests/` | Unit tests |

## Using it from the platform

```python
from domino.game import Game
from domino.player import Player

game = Game([Player(id="u1", name="Ana"), Player(id="u2", name="Leo")])

seat = game.current_seat
game.legal_moves(seat)          # e.g. [((6, 6), "R")]
game.play(seat, *game.legal_moves(seat)[0])   # or game.draw(seat) / game.pass_turn(seat)
game.state(for_seat=1)          # board, whose turn, my hand, my moves, winner ...
```

Illegal actions raise `ValueError` and leave the game unchanged.

## Running

```
python main.py                                    # play one random game
python -m tools.play                              # play against a bot in the terminal
python -m unittest discover -s tests -t .         # run the tests
```

Web
---
`web/` is the page where a person plays a full game against a bot (easy = heaviest
tile, medium = the scoring bot from `tools/play_scoring.py`). It is a static page:
[Pyodide](https://pyodide.org) runs the real `domino/` engine inside the browser,
so there is no server and nothing to install. GitHub Pages publishes it on every
push to `main` (`.github/workflows/pages.yml`).

Try it on your computer, from the project folder:

    python -m http.server 8000      # then open http://localhost:8000/web/

| Path | What it does |
|---|---|
| `web/session.py` | Bridge to the engine: runs the bot's turns, hides the bot's tiles, answers in JSON |
| `web/index.html` | The page |
| `web/static/app.js` | Loads the engine with Pyodide, draws the board and your hand, sends your moves |
| `web/static/style.css` | Looks |
