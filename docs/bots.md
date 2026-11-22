# Our bots

Four bots come with the game, one per difficulty level on the website (bots sent by other teams
are [further down](#bots-from-other-teams)). They follow exactly the
same rules as a bot you write: they only get their [view](contract.md), and they go through the
referee.

| Level | Bot | On the website | Authors | How it plays |
|---|---|---|---|---|
| easy | `GreedyBot` | Paquito | Zena Saez | Always plays its heaviest tile, to get rid of dots early. |
| medium | `ScoringBot` | Rosa | Zena Saez | Scores every legal move on weight, doubles, keeping tiles that fit and blocking numbers the opponent lacks, then plays the best one. |
| hard | `MonteCarloBot` | Paco | santiagofernandezmarco | Imagines many hands the opponent could hold, plays each move out to the end in every one, and keeps the move that wins most; solves the endgame exactly. |
| superhard | `ExpertBot` | C06 | carlosjtabera-dev | Reads the opponent's hand from their draws, passes and choices, learns their playing style, and solves the last moves exactly. |

## How strong they are

Measured with the arena (`python -m tools.arena`), games alternating seats:

| Match | Games | Win rate of the first bot |
|---|---|---|
| Monte Carlo vs Scoring | 2000 | 65.6 % (± 2.1 %) |
| Monte Carlo vs Greedy | 1000 | 71.9 % (± 2.8 %) |
| Scoring vs Greedy | 2000 | 60.8 % (± 2.1 %) |
| Expert vs Monte Carlo | 1000 | 54.7 % (± 3.1 %) |
| Expert vs Scoring | 1000 | 64.6 % (± 3.0 %) |
| Expert vs Greedy | 1000 | 73.7 % (± 2.7 %) |

Domino has a lot of luck in the deal, so a few games prove nothing: these need hundreds of games
to be trusted.

## How they reason about what they can't see

Domino has hidden information: you never see the opponent's tiles. The stronger bots reason about
it from what's public:

- **Drawing or passing** shows the opponent holds no tile with either open number. The scoring,
  Monte Carlo and expert bots all track this.
- **Monte Carlo** deals the opponent many possible hands that fit everything seen so far, and
  plays each candidate move out to the end in all of them.
- **Expert** also reads the opponent's *choices*: each tile they pick is a clue about the ones
  they kept, weighed by how likely that choice was with each hand it imagines for them.

## Bots from other teams

Other teams wrote these bots and sent them by pull request. We reviewed each one against the
[checklist](tutorial.md#checklist-before-opening-the-pull-request) and the tests, then merged it.
Like every bot in `domino/bots/`, they play in the arena, the tournament and the ranking.

| Bot | Name | Authors | Pull request | How it plays |
|---|---|---|---|---|
| `TramperoBayesianoBot` | Trampero bayesiano | Marcos Felgueroso | [#15](https://github.com/zenasaez-oss/DOMINO/pull/15) | Deduces the opponent's hand with Bayes (draws, passes, the opening and the tiles they choose), plays out many possible hands and keeps the move with the highest expected chance of winning; solves the endgame exactly. |
| `MEUBot` | HexArena MEU | Cristina Colunga, Mónica Anzola | [#14](https://github.com/zenasaez-oss/DOMINO/pull/14) | Maximum expected utility: estimates which tiles the opponent can hold and plays the move that best combines dots played, doubles, tiles that keep fitting and the exact probability of blocking the opponent. |

Measured with the arena against our strongest bot:

| Match | Games | Win rate of the first bot |
|---|---|---|
| Expert vs Trampero bayesiano | 1000 | 51.1 % (± 3.1 %) |

That interval includes 50 %, so the two are as good as tied. The [ranking](tournament.md) has
every bot against every other one.

## Adding yours

Any bot in `domino/bots/` is found automatically, plays in the arena and in tournaments, and is
checked by the tests on every pull request. See the [tutorial](tutorial.md).

The website's level menu shows the four bots above; a new bot isn't added to it automatically.
