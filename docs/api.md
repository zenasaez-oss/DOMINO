# API reference

Generated from the code's docstrings. For the ideas behind it, read
[What a bot sees and returns](contract.md) first.

## Writing a bot

::: domino.bots.base.Bot

::: domino.bots.base.check_move

::: domino.bots.base.IllegalMove

## The game

`Game.view(seat)` is what a bot receives. The other methods are how a game is played.

::: domino.game.Game
    options:
      members:
        - view
        - legal_moves
        - can_draw
        - can_pass
        - play
        - draw
        - pass_turn
        - forfeit
        - state
        - quick_start

## Finding bots

::: domino.bots.registry.find_bots

::: domino.bots.registry.scan

::: domino.bots.registry.BotRegistryError

## The referee

::: domino.referee.play_match

::: domino.referee.MatchResult

::: domino.referee.STANDARD_TIME_LIMIT

::: domino.referee.FAULTS

::: domino.referee.ask_bot

::: domino.referee.make_bot

::: domino.referee.tell_bot

::: domino.referee.BotFault
