"""Developer tool: play one game in the terminal against the medium (scoring) bot.

Not part of the game logic - the real game runs on the platform. The bot itself lives in
domino/bots/scoring.py. The other play_* tools reuse bot_turn and your_turn from here.

Run from the project folder:  python -m tools.play_scoring
"""
from domino.board import board_ends
from domino.bots import ScoringBot
from domino.game import Game
from domino.player import Player
from tools.play import show_board, tile_str

YOU, BOT = 0, 1


def bot_turn(game, bot):
    while True:
        moves = game.legal_moves(BOT)
        if moves:
            tile, side = bot.choose(game.view(BOT), moves)
            game.play(BOT, tile, side)
            print(f"Bot plays {tile_str(tile)} on the {'left' if side == 'L' else 'right'}")
            return
        if game.can_draw(BOT):
            game.draw(BOT)
            print("Bot draws a tile")
        else:
            game.pass_turn(BOT)
            print("Bot passes")
            return


def your_turn(game, bot):
    """Your turn. Tells the bot what it could see: draws, and whether you played or passed."""
    ends = board_ends(game.board)
    draws = 0
    while True:
        show_board(game)
        print("Your hand:", " ".join(tile_str(t) for t in game.players[YOU].hand))
        moves = game.legal_moves(YOU)

        if not moves:
            if game.can_draw(YOU):
                tile = game.draw(YOU)
                draws += 1
                print(f"No moves - you draw {tile_str(tile)}")
                continue
            game.pass_turn(YOU)
            print("No moves and the boneyard is empty - you pass")
            bot.observe_opponent_turn(ends, draws, played=False)
            return

        for i, (tile, side) in enumerate(moves, start=1):
            print(f"  {i}: {tile_str(tile)} on the {'left' if side == 'L' else 'right'}")
        choice = input("Pick a move number (q to quit): ").strip().lower()
        if choice == "q":
            raise SystemExit("Bye!")
        if choice.isdigit() and 1 <= int(choice) <= len(moves):
            tile, side = moves[int(choice) - 1]
            game.play(YOU, tile, side)
            bot.observe_opponent_turn(ends, draws, played=True)
            return
        print("Not a valid choice, try again.")


def main():
    game = Game([Player(id="you", name="You"), Player(id="bot", name="Bot", is_bot=True)])
    bot = ScoringBot(BOT)
    who = "You start" if game.current_seat == YOU else "Bot starts"
    print(f"{who} (opening tile {tile_str(game.opening_tile)}) - you're playing the scoring bot")

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
    print("Bot's last tiles:", " ".join(tile_str(t) for t in game.players[BOT].hand) or "none")


if __name__ == "__main__":
    main()
