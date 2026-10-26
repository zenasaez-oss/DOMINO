# Rules

Classic domino for **two players**: one line of tiles with two open ends (left and right), no
branches.

## The set and the deal

- A **double-six** set: every pair of numbers from 0 to 6, each once. That's 28 tiles.
- Each player gets **7 tiles**. The other **14** stay face down in the **boneyard**.

## Who opens

- The player holding the **highest double** opens with it (6-6, then 5-5, ...).
- If nobody has a double, the player with the **heaviest tile** opens with it (most dots; on a
  tie, the one with the bigger half).
- On the website, after the first game the opener **alternates**: one game the bot opens, the
  next one you do, each with their own highest double (or heaviest tile).

## Your turn

1. **Play** a tile that matches the number at the **left** or **right** end of the line.
2. If you can't, **draw** from the boneyard until you can. You keep the turn while you draw.
3. Only when you can't play **and** the boneyard is empty do you **pass**.

You can't draw while you have a legal move, and you can't pass while you can still draw.

## How a game ends

| End | When | Who wins | Score |
|---|---|---|---|
| **Domino** | A player plays their last tile | That player | The dots left in the other player's hand |
| **Blocked** | Both players pass in a row: nobody can move | The player with **fewer dots** in hand | The dots left in the loser's hand |
| **Tie** | Blocked, and both hold the same number of dots | Nobody | 0 |

## When a bot breaks the rules

In games run by the [referee](architecture.md#the-referee), a bot that crashes, answers with an
illegal move or takes too long **loses on the spot**, and the other player wins. The end reason
is then `"error"`, `"illegal"` or `"timeout"` instead of `"domino"` or `"blocked"`.
