"""Developer tool: play one game in the terminal against the superhard (expert) bot.

Not part of the game logic - the real game runs on the platform. The bot itself, and how it
thinks, is in domino/bots/expert.py.

Run from the project folder:  python -m tools.play_expert
"""
from domino.bots import ExpertBot
from domino.game import Game
from domino.player import Player
from tools.play import show_board, tile_str
from tools.play_scoring import bot_turn, your_turn

YOU, BOT = 0, 1


def main():
    game = Game([Player(id="you", name="You"), Player(id="bot", name="Bot", is_bot=True)])
    bot = ExpertBot(BOT)
    who = "You start" if game.current_seat == YOU else "Bot starts"
    print(f"{who} (opening tile {tile_str(game.opening_tile)}) - you're playing the expert bot")
    while not game.finished:
        if game.current_seat == YOU:
            your_turn(game, bot)
        else:
            bot_turn(game, bot)
    show_board(game)
    state = game.state()
    if state["winner"] is None:
        print("\nBlocked game, tied on dots - nobody wins.")
    else:
        winner = "You win" if state["winner"] == YOU else "Bot wins"
        how = "went out" if state["end_reason"] == "domino" else "fewest dots in a blocked game"
        print(f"\n{winner}! ({how}) Score: {state['score']}")


if __name__ == "__main__":
    main()
