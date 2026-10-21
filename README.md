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
| `tools/play_montecarlo.py` | The hard bot (`MonteCarloBot`) and a terminal game against it |
| `tools/arena.py` | Developer tool: make two bots play many games and count the wins |
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
python -m tools.play_montecarlo                   # play against the hard (Monte Carlo) bot
python -m tools.arena montecarlo scoring -n 200   # bot against bot, win counts
python -m unittest discover -s tests -t .         # run the tests
```

## The Monte Carlo bot

`MonteCarloBot` (in `tools/play_montecarlo.py`) is the hardest bot. It only reads
`game.state(for_seat=its_seat)`, i.e. what any player at the table can see, and it works out what the
opponent's turns reveal by itself (drawing or passing means they held no tile with the open ends).

For each move it deals the opponent many possible hands that fit what has been seen, plays the rest of
the game out in each of them with a fast heuristic, and keeps the move that does best. Once the boneyard
is empty every sampled world is a perfect-information game, so it is solved exactly.

```python
from tools.play_montecarlo import MonteCarloBot

bot = MonteCarloBot(seat=1)                       # samples=300 hands per decision by default
bot = MonteCarloBot(seat=1, time_limit=0.5)       # or: think for 0.5 s per decision
tile, side = bot.choose(game, game.legal_moves(1))
```

Measured with `python -m tools.arena` (games alternate seats; win rate of the first bot):

| Match | Games | Win rate of the first bot |
|---|---|---|
| `montecarlo` vs `scoring` | 2000 | 65.6 % (+/- 2.1 %) |
| `montecarlo` vs `heavy` | 1000 | 71.9 % (+/- 2.8 %) |
| `scoring` vs `heavy` | 2000 | 60.8 % (+/- 2.1 %) |

It thinks about 30 ms per move on average (never more than a second or so). The bot is random, so
repeating the measurement gives a few points of difference either way.
