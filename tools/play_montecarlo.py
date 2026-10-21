"""Developer tool: play one game in the terminal against the Monte Carlo (hard) bot.

Not part of the game logic - the real game runs on the platform.

Run from the project folder:  python -m tools.play_montecarlo

How the bot thinks (it only ever uses what any player at the table can see):
  1. It remembers what the opponent's turns reveal: drawing or passing means they held no tile
     with the open end numbers.
  2. It deals the opponent many possible hands that fit everything seen so far
     ("determinization"), and shuffles the unseen boneyard tiles.
  3. For each legal move it plays the rest of the game out in each of those worlds with a fast
     heuristic for both sides, and keeps the move that wins most often.
  4. When the boneyard is empty, every sampled world is a perfect-information game, so the bot
     solves it exactly instead of playing it out.
"""
import random
import time

from domino.board import LEFT
from tools.play_scoring import bot_turn, your_turn

YOU, BOT = 0, 1

# --- tile bookkeeping -------------------------------------------------------------------
TILES = [(a, b) for a in range(7) for b in range(a, 7)]   # same order as domino.full_set()
INDEX = {t: i for i, t in enumerate(TILES)}
PIPS = [a + b for a, b in TILES]
BIT = [1 << i for i in range(len(TILES))]
HAS = [sum(BIT[i] for i, t in enumerate(TILES) if n in t) for n in range(7)]  # tiles showing n
ALL = (1 << len(TILES)) - 1


def _mask_pips(mask):
    total = 0
    while mask:
        low = mask & -mask
        total += PIPS[low.bit_length() - 1]
        mask ^= low
    return total


def ends_after(ends, tile, side):
    """Open ends after `tile` is played on `side` (ends is None on an empty board)."""
    if ends is None:
        return tile
    left, right = ends
    if side == LEFT:
        return (tile[0] if tile[1] == left else tile[1]), right
    return left, (tile[1] if tile[0] == right else tile[0])


# --- exact solver for perfect-information endgames (boneyard empty) -----------------------
SOLVE_LIMIT = 4000    # positions the solver may visit per world before we play it out instead


class SolveTooBig(Exception):
    pass


def solve(mine, theirs, left, right, to_move, passes, memo):
    """Game value for the player to move: +1 they win, 0 tie, -1 they lose.

    mine / theirs are bitmasks of the tiles held by the player to move and by the other player.
    """
    key = (mine, theirs, left, right, passes)
    hit = memo.get(key)
    if hit is not None:
        return hit
    if len(memo) > SOLVE_LIMIT:
        raise SolveTooBig
    playable = mine & (HAS[left] | HAS[right])
    if not playable:
        if passes >= 1:                                    # both players passed in a row: blocked
            a, b = _mask_pips(mine), _mask_pips(theirs)
            best = 1 if a < b else (-1 if a > b else 0)
        else:
            best = -solve(theirs, mine, left, right, 1 - to_move, passes + 1, memo)
    else:
        best = -2
        rest = playable
        while rest:
            low = rest & -rest
            rest ^= low
            t = TILES[low.bit_length() - 1]
            a, b = t
            new_mine = mine ^ low
            if not new_mine:
                best = 1
                break
            options = set()
            if a == left or b == left:
                options.add((b if a == left else a, right))
            if (a == right or b == right) and left != right:
                options.add((left, b if a == right else a))
            for nl, nr in options:
                v = -solve(theirs, new_mine, nl, nr, 1 - to_move, 0, memo)
                if v > best:
                    best = v
                    if best == 1:
                        break
            if best == 1:
                break
    memo[key] = best
    return best


# --- fast rollouts ------------------------------------------------------------------------
def _heuristic_pick(hand, moves, rng):
    """Cheap move choice for both sides in playouts: heavy tiles, doubles and keeping options."""
    best, best_score = None, -1e9
    for move in moves:
        t, nl, nr = move
        s = t[0] + t[1] + (3 if t[0] == t[1] else 0)
        for o in hand:
            if o != t and (o[0] == nl or o[1] == nl or o[0] == nr or o[1] == nr):
                s += 2
        s += rng.random() * 0.5
        if s > best_score:
            best, best_score = move, s
    return best


def _scoring_pick(hand, moves, rng):
    """Playout choice closer to the scoring bot: weight, doubles, follow-ups and variety."""
    best, best_score = None, -1e9
    for move in moves:
        t, nl, nr = move
        a, b = t
        s = a + b + (4 if a == b else 0)
        has_a = has_b = False
        for o in hand:
            if o == t:
                continue
            m = (o[0] == nl or o[1] == nl) + (o[0] == nr or o[1] == nr)
            s += 3 * m
            if a in o:
                has_a = True
            if b in o:
                has_b = True
        if not has_a:
            s -= 2
        if b != a and not has_b:
            s -= 2
        s += rng.random() * 0.1
        if s > best_score:
            best, best_score = move, s
    return best


POLICIES = {"light": _heuristic_pick, "scoring": _scoring_pick}


def _legal(hand, left, right):
    out = []
    for t in hand:
        a, b = t
        if a == left or b == left:
            out.append((t, b if a == left else a, right))
        if (a == right or b == right) and left != right:
            out.append((t, left, b if a == right else a))
    return out


def rollout(me, opp, yard, left, right, turn, passes, rng, pick=_heuristic_pick, margin=0.02):
    """Play the game to the end with the heuristic. Returns +1 / 0 / -1 from my point of view.

    me, opp: lists of tiles; yard: list (tiles are drawn from the end); turn: 0 me, 1 opponent.
    """
    hands = (me, opp)
    yard = list(yard)
    while True:
        hand = hands[turn]
        moves = _legal(hand, left, right)
        while not moves and yard:
            hand.append(yard.pop())
            moves = _legal(hand, left, right)
        if not moves:
            passes += 1
            if passes >= 2:
                a = sum(t[0] + t[1] for t in me)
                b = sum(t[0] + t[1] for t in opp)
                return (1 + margin * (b - a)) if a < b else ((-1 - margin * (a - b)) if a > b else 0)
            turn ^= 1
            continue
        passes = 0
        t, left, right = pick(hand, moves, rng)
        hand.remove(t)
        if not hand:
            if turn == 0:
                return 1 + margin * sum(t[0] + t[1] for t in opp)
            return -1 - margin * sum(t[0] + t[1] for t in me)
        turn ^= 1


class MonteCarloBot:
    """Hard bot: sampled opponent hands + playouts, exact solving once the boneyard is empty.

    seat       - which seat the bot plays
    samples    - how many possible opponent hands to try per decision
    time_limit - optional: think for this many seconds per decision instead of a fixed sample count
    seed       - optional, makes a game reproducible
    max_time   - safety cap in seconds per decision for the fixed-samples mode (default 2)
    """

    def __init__(self, seat, samples=300, time_limit=None, seed=None, policy="light", margin=0.02, max_time=2.0):
        self.seat = seat
        self.opponent = 1 - seat
        self.samples = samples
        self.time_limit = time_limit
        self.rng = random.Random(seed)
        self.pick = POLICIES[policy]
        self.margin = margin
        self.max_time = max_time   # safety cap per decision when using a fixed number of samples
        self.opponent_lacks = set()   # numbers the opponent is known not to hold right now
        self._last = None             # what the table looked like right after our last move

    # The platform / terminal tool may call this after each opponent turn. It is optional: the
    # bot also works it out by itself from the table (see _learn), so both give the same result.
    def observe_opponent_turn(self, ends, draws, played):
        pass

    # --- what the opponent's turn tells us ------------------------------------------------
    def _learn(self, board_len, yard, hand_len):
        last, self._last = self._last, None
        if last is None:
            return
        grown = board_len - last["board_len"]
        my_draws = hand_len - last["hand_len"]
        opp_draws = last["yard"] - yard - my_draws
        if grown < 0 or grown > 1 or my_draws < 0 or opp_draws < 0 or last["ends"] is None:
            self.opponent_lacks = set()      # something we didn't see happen: forget, stay safe
            return
        played = grown == 1
        ends = set(last["ends"])
        kept = opp_draws - (1 if played else 0)   # tiles they drew and still hold
        if kept > 0:
            self.opponent_lacks = ends            # all their drawn tiles missed these ends
        elif opp_draws > 0 or not played:
            self.opponent_lacks |= ends

    # --- the decision ---------------------------------------------------------------------
    def choose(self, game, moves):
        view = game.state(for_seat=self.seat)       # the only thing we ever read from the game
        board = view["board"]
        hand = list(view["my_hand"])
        yard = view["boneyard_size"]
        opp_n = view["players"][self.opponent]["tiles_left"]
        self._learn(len(board), yard, len(hand))
        if len(moves) == 1:                          # forced move (including the opening tile)
            self._remember(moves[0], view)
            return moves[0]

        seen = 0
        for t in hand:
            seen |= BIT[INDEX[t]]
        for t in board:
            seen |= BIT[INDEX[tuple(sorted(t))]]
        unseen = [t for t in TILES if not seen & BIT[INDEX[t]]]
        lacks = self.opponent_lacks
        fits = [t for t in unseen if t[0] not in lacks and t[1] not in lacks]
        if len(fits) < opp_n:                         # inconsistent knowledge: drop the deductions
            fits = unseen
        forced_yard = [t for t in unseen if t not in fits]

        left, right = view["ends"]
        scores = [0.0] * len(moves)
        start = time.perf_counter()
        done = 0
        too_big = False
        while True:
            opp_hand = self.rng.sample(fits, opp_n)
            taken = set(opp_hand)
            pool = forced_yard + [t for t in fits if t not in taken]
            self.rng.shuffle(pool)
            for i, (tile, side) in enumerate(moves):
                nl, nr = ends_after((left, right), tile, side)
                rest = [t for t in hand if t != tile]
                if not rest:
                    scores[i] += 1
                elif not pool and not too_big:          # perfect information: solve exactly
                    mine = sum(BIT[INDEX[t]] for t in rest)
                    theirs = sum(BIT[INDEX[t]] for t in opp_hand)
                    try:
                        scores[i] += -solve(theirs, mine, nl, nr, 1, 0, {})
                    except SolveTooBig:                 # huge endgame: play it out instead
                        too_big = True
                        scores[i] += rollout(rest, list(opp_hand), pool, nl, nr, 1, 0, self.rng, self.pick, self.margin)
                else:
                    scores[i] += rollout(rest, list(opp_hand), pool, nl, nr, 1, 0, self.rng, self.pick, self.margin)
            done += 1
            spent = time.perf_counter() - start
            if self.time_limit:
                if done >= 10 and spent >= self.time_limit:
                    break
            elif done >= self.samples or (done >= 20 and spent >= self.max_time):
                break

        best = max(range(len(moves)), key=lambda i: scores[i])
        self._remember(moves[best], view)
        return moves[best]

    def _remember(self, move, view):
        tile, side = move
        board = view["board"]
        ends = ends_after(view["ends"], tile, side) if board else tuple(tile)
        self._last = {
            "board_len": len(board) + 1,
            "hand_len": len(view["my_hand"]) - 1,
            "yard": view["boneyard_size"],
            "ends": ends,
        }


def main():
    from domino.game import Game
    from domino.player import Player
    from tools.play import show_board, tile_str

    game = Game([Player(id="you", name="You"), Player(id="bot", name="Bot", is_bot=True)])
    bot = MonteCarloBot(BOT)
    who = "You start" if game.current_seat == YOU else "Bot starts"
    print(f"{who} (opening tile {tile_str(game.opening_tile)}) - you're playing the Monte Carlo bot")

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
