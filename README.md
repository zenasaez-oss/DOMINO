# Domino

Game logic for classic domino (one line of play, two open ends), for 2 players.
The game itself is played on a separate platform; this repo is the rules engine it calls.

- **Play:** https://zenasaez-oss.github.io/DOMINO/
- **Ranking** of every bot: https://zenasaez-oss.github.io/DOMINO/web/#ranking
- **Documentation**, including the API for bots and a tutorial to write your own:
  https://domino-game.readthedocs.io/en/latest/ (built from the `docs/` folder; `mkdocs serve`
  shows it locally).

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
| `domino/bots/` | The bots: the `Bot` base class (`base.py`), automatic discovery (`registry.py`) and our four bots, `GreedyBot` (easy), `ScoringBot` (medium), `MonteCarloBot` (hard), `ExpertBot` (superhard) |
| `domino/referee.py` | Plays games between bots; a bot that crashes, plays illegally or runs out of time loses |
| `domino/tournament.py` | Every bot against every other (round robin): the website's tournament and the published ranking |
| `main.py` | Developer check: plays one random game and prints the result |
| `tools/` | Developer tools only: terminal games against each bot (`play*.py`), bot-vs-bot matches (`arena.py`) and the ranking tournament (`tournament.py`) |
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

## Bots

Every bot inherits from `Bot` (`domino/bots/base.py`) and implements four methods: who it
is (`get_name`, `get_authors`, `get_description`) and how it plays (`choose`). A bot that
forgets one is refused as soon as it's created.

A bot never gets the game itself. On its turn it gets `game.view(seat)`: its own hand plus
everything public (board, ends, how many tiles the opponent holds, how many are left to draw,
and the history of plays, draws and passes). The opponent's tiles and the boneyard aren't in
it, so a bot can't cheat even if it tries.

```python
from domino.bots import Bot

class MyBot(Bot):
    @classmethod
    def get_name(cls):
        return "My bot"

    @classmethod
    def get_authors(cls):
        return ["Your name"]

    @classmethod
    def get_description(cls):
        return "Plays its heaviest tile."

    def choose(self, view, moves):          # moves = every legal (tile, side)
        return max(moves, key=lambda m: sum(m[0]))
```

Save it as a file in `domino/bots/` and that's all: `find_bots()` finds every bot in that folder
automatically, and reports any file that fails to import, any bot missing a required method and
any two bots with the same name.

`choose` must return exactly one of `moves`. The referee (`domino/referee.py`) plays games between
bots and makes sure none can break them: a bot that crashes, answers with an illegal move or takes
longer than the time limit loses that game on the spot, and the other bot wins.

```python
from domino.bots import find_bots
from domino.referee import play_match

bots = find_bots()                                   # {"Greedy": GreedyBot, ..., "My bot": MyBot}
result = play_match(bots["My bot"], bots["Scoring"], seed=7, time_limit=1)
result.winner, result.end_reason, result.fault       # e.g. 1, "illegal", {"seat": 0, ...}
```

The referee builds each bot with `MyBot.create(seat, seed)`. The same seed replays exactly the same
game, so override `create` to pass the seed on if your bot uses randomness.

## Running

```
python main.py                                    # play one random game
python -m tools.play                              # play against the easy bot in the terminal
python -m tools.play_scoring                      # play against the medium (scoring) bot
python -m tools.play_montecarlo                   # play against the hard (Monte Carlo) bot
python -m tools.play_expert                       # play against the superhard (expert) bot
python -m tools.arena montecarlo scoring -n 200   # bot against bot, win counts (any bot in domino/bots/)
python -m tools.tournament -n 10                  # every bot against every other, ranked
python -m unittest discover -s tests -t .         # run the tests
```

## Web

`web/` is the website. From its home screen you can:

- **Jugar**: play a full game against any bot in `domino/bots/`. Our four have a character each
  (easy = heaviest tile, medium = the scoring bot, hard = the Monte Carlo bot, superhard = the
  expert bot); any other bot is played by the Stranger, under the bot's own name.
- **Torneo**: every bot you pick against every other, played in your browser.
- **Ranking**: the official ranking, played on GitHub on every push to `main` with the 5-second
  time limit (`tools/tournament.py`), with head-to-head results.
- **Información**: the rules, every bot with its authors and description, and how to write yours.

**A new bot needs no change to the website**: every file in `domino/bots/` is loaded, and the
registry says who the bots are. See the
[tournament and ranking docs](https://domino-game.readthedocs.io/en/latest/tournament/).

It is a static page:
[Pyodide](https://pyodide.org) runs the real `domino/` engine inside the browser,
so there is no server and nothing to install. GitHub Pages publishes it on every
push to `main` (`.github/workflows/pages.yml`), together with the ranking.

Try it on your computer, from the project folder:

    python -m tools.tournament -n 10 --out web/ranking.json   # optional: a ranking to show
    python -m http.server 8001      # then open http://localhost:8001/web/

| Path | What it does |
|---|---|
| `web/session.py` | Bridge to the engine: runs the bot's turns, hides the bot's tiles, lists the bots, plays the tournament, answers in JSON |
| `web/index.html` | The page and its sections |
| `web/static/app.js` | Loads the engine with Pyodide (every bot file included), draws the board and your hand, sends your moves |
| `web/static/views.js` | Home, tournament, ranking and information sections; starts the page |
| `web/static/style.css` | Looks |

## The Monte Carlo bot

`MonteCarloBot` (in `domino/bots/montecarlo.py`) is the hard bot. Like every bot it only gets
its view (`game.view(its_seat)`), i.e. what any player at the table can see, and it works out what the
opponent's turns reveal by itself (drawing or passing means they held no tile with the open ends).

For each move it deals the opponent many possible hands that fit what has been seen, plays the rest of
the game out in each of them with a fast heuristic, and keeps the move that does best. Once the boneyard
is empty every sampled world is a perfect-information game, so it is solved exactly.

```python
from domino.bots import MonteCarloBot

bot = MonteCarloBot(seat=1)                       # samples=300 hands per decision by default
bot = MonteCarloBot(seat=1, time_limit=0.5)       # or: think for 0.5 s per decision
tile, side = bot.choose(game.view(1), game.legal_moves(1))
```

Measured with `python -m tools.arena` (games alternate seats; win rate of the first bot):

| Match | Games | Win rate of the first bot |
|---|---|---|
| `montecarlo` vs `scoring` | 2000 | 65.6 % (+/- 2.1 %) |
| `montecarlo` vs `heavy` | 1000 | 71.9 % (+/- 2.8 %) |
| `scoring` vs `heavy` | 2000 | 60.8 % (+/- 2.1 %) |

It thinks about 30 ms per move on average (never more than a second or so). The bot is random, so
repeating the measurement gives a few points of difference either way.

## The expert bot

`ExpertBot` (`domino/bots/expert.py`) only gets its view (`game.view(its_seat)`), what any
player at the table can see, and works out the opponent's tiles from more than their draws
and passes:

- **The opening.** The opener plays their highest double, or their heaviest tile if they
  have no double, so a 4-4 opening means they weren't dealt the 5-5 or the 6-6, and a plain
  tile means no doubles at all. That holds until they draw.
- **Their choices.** Each tile the opponent picks is a clue about the ones they kept. The
  bot weighs every hand it imagines for them by how likely those choices were with it.
- **Their style, learned as it plays.** How likely a choice is depends on who is playing,
  so the bot knows four styles, each a softmax over the legal moves fitted on thousands of
  recorded decisions: like the Monte Carlo bot, like the scoring bot, always the heaviest
  tile, or random. It keeps evidence for each style from the opponent's choices and reads
  their hand with the mix it believes in. Pass the same `memory` dict to the next game's
  bot and it keeps learning the same opponent from game to game.
- **Playing it out.** For each candidate move it imagines opponent hands that fit all of
  that, plays the rest of the game in each (the opponent in the style it believes in) and
  keeps the move that does best; weak candidates are dropped early to think more about the
  good ones. Once 4 tiles or fewer are left in the boneyard every imagined world is solved
  exactly instead, draws included.

Measured with the arena (`tools/arena.py`), 1000 games per match, seats alternating,
0.15 s per move:

| Opponent | Expert's win rate |
|---|---|
| Monte Carlo bot (`montecarlo`) | 54.7 % (+/- 3.1 %) |
| Scoring bot (`scoring`) | 64.6 % (+/- 3.0 %) |
| Heaviest tile (`heavy`) | 73.7 % (+/- 2.7 %) |

In the same games it guesses 48 % of the opponent's tiles right, against 43 % from draws
and passes alone (a blind guess gets about 40 %).

```python
from domino.bots import ExpertBot

bot = ExpertBot(seat=1)                         # thinks 0.3 s per decision by default
bot = ExpertBot(seat=1, time_limit=0.6)         # or longer
tile, side = bot.choose(game.view(1), game.legal_moves(1))
bot.style_odds()                                # {'montecarlo': 0.7, 'scoring': 0.2, ...}
```
