"""Developer tool: play one game in the terminal against the scoring (medium) bot.

Not part of the game logic - the real game runs on the platform.

Run from the project folder:  python -m tools.play_scoring
"""
import random

from domino.board import LEFT, board_ends
from domino.domino import is_double, pip_count
from domino.game import Game
from domino.player import Player
from tools.play import show_board, tile_str

YOU, BOT = 0, 1
NUMBERS_PER_SET = 7  # in a double-six set every number appears on 7 tiles


def ends_after(board, tile, side):
    """Board ends if `tile` were played on `side`, without touching the board."""
    if not board:
        return tile
    left, right = board_ends(board)
    if side == LEFT:
        return (tile[0] if tile[1] == left else tile[1]), right
    return left, (tile[1] if tile[0] == right else tile[0])


class ScoringBot:
    """Scores every legal move and plays the best one.

    It only uses what any player at the table can see: the board, its own hand,
    how many tiles the opponent holds, and when the opponent draws or passes.
    """

    def __init__(self, seat):
        self.seat = seat
        self.opponent = 1 - seat
        self.opponent_lacks = set()  # numbers the opponent is known not to hold

    def observe_opponent_turn(self, ends, draws, played):
        """Update what we know after the opponent's turn.

        ends   - board ends when their turn started (None on an empty board)
        draws  - how many tiles they drew this turn
        played - True if they played a tile, False if they passed
        """
        if ends is None:
            return
        kept = draws - (1 if played else 0)   # drawn tiles still in their hand
        if kept > 0:
            # A kept tile didn't fit these ends, but could hold any older "missing" number.
            self.opponent_lacks = set(ends)
        elif draws > 0 or not played:
            # They drew and played the one matching tile, or passed without drawing:
            # everything we knew still holds, and now they lack these ends too.
            self.opponent_lacks |= set(ends)
        # Played without drawing: nothing learned, and nothing they already lacked changes.

    def choose(self, game, moves):
        hand = game.players[self.seat].hand
        opp_tiles = len(game.players[self.opponent].hand)

        def unseen(rest, n):
            """How many tiles with `n` we haven't seen (not on the board, not in our hand)."""
            return NUMBERS_PER_SET - sum(n in t for t in game.board) - sum(n in t for t in rest)

        def score(move):
            tile, side = move
            rest = [t for t in hand if t != tile]
            new_ends = set(ends_after(game.board, tile, side))

            s = pip_count(tile)                                   # weight
            if is_double(tile):
                s += 4                                            # doubles
            for e in new_ends:
                s += 3 * sum(e in t for t in rest)                # follow-up
            for n in set(tile):
                if not any(n in t for t in rest):
                    s -= 2                                        # variety
            for e in new_ends:
                if e in self.opponent_lacks:
                    s += 5                                        # blocking
            if len(rest) <= opp_tiles:
                for e in new_ends:
                    s += 4 - min(4, unseen(rest, e))              # choking
            if not rest:
                s += 1000                                         # going out
            return s + random.random() * 0.1                      # break ties

        return max(moves, key=score)


def bot_turn(game, bot):
    while True:
        moves = game.legal_moves(BOT)
        if moves:
            tile, side = bot.choose(game, moves)
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
