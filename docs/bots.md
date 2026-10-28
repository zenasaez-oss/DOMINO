# Our bots

Four bots come with the game, one per difficulty level on the website. They follow exactly the
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

## Adding yours

Any bot in `domino/bots/` is found automatically, plays in the arena and in tournaments, and is
checked by the tests on every pull request. See the [tutorial](tutorial.md).

The website's level menu shows the four bots above; a new bot isn't added to it automatically.
