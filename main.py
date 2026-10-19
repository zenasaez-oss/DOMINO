"""Entry point.

The game is played on a separate platform, so this is only a developer check:
it plays a full round with every seat taking a random legal action and prints the result.

Run:  python main.py
"""
import random

from domino.game import Game


def auto_play(game):
    """Drive a game to the end, each seat taking a random legal action."""
    while not game.finished:
        seat = game.current_seat
        moves = game.legal_moves(seat)
        if moves:
            game.play(seat, *random.choice(moves))
        elif game.can_draw(seat):
            game.draw(seat)
        else:
            game.pass_turn(seat)
    return game


if __name__ == "__main__":
    game = auto_play(Game.with_n_players(2))
    state = game.state()
    print("Board:", " ".join(f"[{a}|{b}]" for a, b in state["board"]))
    print("Tiles left:", [p["tiles_left"] for p in state["players"]])
    print(f"Ended by: {state['end_reason']}, winner: seat {state['winner']}, score: {state['score']}")
