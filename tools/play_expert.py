"""The expert bot: reads the opponent from every move they make, not only from their draws.

Not part of the game logic - the real game runs on the platform.

Run from the project folder:  python -m tools.play_expert

How it thinks (it only reads game.state(for_seat=its_seat), what any player at the table sees):
  1. Hard facts. Drawing or passing shows the opponent holds no tile with the open numbers.
  2. Soft clues. Every tile the opponent chooses says something about the tiles they did NOT
     choose: someone who lays a light tile while holding a heavy double that also fitted is
     unusual. The bot keeps the opponent's recent choices and, for each possible hand it
     imagines for them, measures how likely those choices were with that hand (a Bayesian
     weight). Hands that explain what the opponent did count for more.
  3. It imagines many opponent hands that respect the facts, weighs them by the clues, and
     plays the rest of the game out in each for every candidate move. Weak candidates are
     dropped early (successive halving), so the thinking time goes to the moves that matter.
  4. Late in the game it stops guessing. In an imagined world every tile is placed, even the
     boneyard's order, so once only a few tiles are left in the boneyard it solves the rest of
     each world exactly, draws included. (With the boneyard empty nothing is hidden at all.)
"""
import math
import random
import time

from domino.board import LEFT

YOU, BOT = 0, 1

TILES = [(a, b) for a in range(7) for b in range(a, 7)]
INDEX = {t: i for i, t in enumerate(TILES)}
BIT = [1 << i for i in range(len(TILES))]
PIPS = [a + b for a, b in TILES]
SHOWS = [sum(BIT[i] for i, t in enumerate(TILES) if n in t) for n in range(7)]   # tiles with n


def norm(tile):
    a, b = tile
    return (a, b) if a <= b else (b, a)


def ends_after(ends, tile, side):
    """Open numbers after `tile` goes on `side` (ends is None on an empty board)."""
    if ends is None:
        return tuple(tile)
    left, right = ends
    if side == LEFT:
        return (tile[0] if tile[1] == left else tile[1]), right
    return left, (tile[1] if tile[0] == right else tile[0])


def legal(hand, left, right):
    """(tile, new_left, new_right) for every way a tile in `hand` fits the ends."""
    out = []
    for t in hand:
        a, b = t
        if a == left or b == left:
            out.append((t, b if a == left else a, right))
        if (a == right or b == right) and left != right:
            out.append((t, left, b if a == right else a))
    return out


def move_score(hand, tile, new_left, new_right):
    """How attractive a move looks to a sensible player: weight, doubles, keeping options."""
    a, b = tile
    s = a + b + (4 if a == b else 0)
    for o in hand:
        if o is not tile and (new_left in o or new_right in o):
            s += 2.5
    return s


# --- how players pick a tile: styles learned from games ---------------------------------
# Each style is a softmax over the legal moves, fitted on thousands of recorded decisions.
#   montecarlo - the Monte Carlo bot (tools/play_montecarlo.py, branch BotDificil), 9,200 decisions; picks its move
#                60% of the time (a random guess: 39%). It hardly cares about dots; it loves
#                leaving both ends on the same number and doubles (not once the boneyard is
#                empty), chokes scarce numbers and leaves numbers it believes we don't hold.
#   scoring    - the scoring bot (tools/play_scoring.py), 10,800 decisions; picks its move 92%
#                of the time. Heavy tiles, doubles, keeping tiles that fit, blocking.
#   heavy      - always plays its heaviest tile (tools/play.py).
#   random     - no preference at all.
# The expert works out during the game (and, in the web, from game to game) which style
# explains the opponent's choices best, and reads their hand with that style.
STYLE_FEATURES = ("pips", "double", "follow", "variety_loss", "same_ends", "count_left", "count_right",
                  "scarce", "lacks_hit", "pips_late", "double_late")


def _style(**weights):
    return {f: weights.get(f, 0.0) for f in STYLE_FEATURES}


STYLES = {
    "montecarlo": _style(pips=0.041, double=0.983, follow=0.008, variety_loss=-0.079, same_ends=2.246,
                         count_left=0.326, count_right=0.457, scarce=0.396, lacks_hit=0.693,
                         pips_late=-0.09, double_late=-0.738),
    "scoring": _style(pips=1.271, double=5.088, follow=2.016, variety_loss=-2.347, same_ends=-2.64,
                      count_left=1.966, count_right=2.027, scarce=0.596, lacks_hit=5.696,
                      pips_late=0.122, double_late=0.304),
    "heavy": _style(pips=3.0),
    "random": _style(),
}
OPPONENT_MODEL = STYLES["montecarlo"]     # also how the expert plays its own side in playouts


def opponent_appeal(hand, tile, nl, nr, counts=None, lacks=(), yard=1, m=OPPONENT_MODEL):
    """How likely the opponent is to pick this move (a log-score; higher = more likely).

    counts[n] - tiles showing n on the board before the move (None: ignore the table)
    lacks     - numbers the opponent believes WE don't hold
    yard      - tiles left in the boneyard"""
    a, b = tile
    double = a == b
    s = m["pips"] * (a + b) + (m["double"] if double else 0.0) + (m["same_ends"] if nl == nr else 0.0)
    if yard == 0:
        s += m["pips_late"] * (a + b) + (m["double_late"] if double else 0.0)
    has_a = has_b = False
    with_left = with_right = 0
    for o in hand:
        if o == tile:
            continue
        on_left, on_right = nl in o, nr in o
        with_left += on_left
        with_right += on_right
        s += m["follow"] * (on_left or on_right)
        has_a = has_a or a in o
        has_b = has_b or b in o
    s += m["count_left"] * with_left + m["count_right"] * with_right
    s += m["variety_loss"] * ((not has_a) + (not double and not has_b))
    if counts is not None:
        scarce = 0
        for e, mine in ((nl, with_left), (nr, with_right)) if nl != nr else ((nl, with_left),):
            out = 7 - counts[e] - (e == a or e == b) - mine
            if out < 4:
                scarce += 4 - out
        s += m["scarce"] * scarce
    if lacks:
        s += m["lacks_hit"] * ((nl in lacks) + (nr != nl and nr in lacks))
    return s


def board_counts(board):
    counts = [0] * 7
    for a, b in board:
        counts[a] += 1
        if a != b:
            counts[b] += 1
    return counts


# --- playouts ---------------------------------------------------------------------------
BLOCK_BONUS = 8   # in playouts both sides go for moves that leave the other with nothing to play


def playout(me, opp, yard, left, right, turn, rng, mimic=False, counts=None, me_like_model=False,
            opp_style=OPPONENT_MODEL):
    """Finish the game. +1 / 0 / -1 for me, plus a little for the dot margin so that among
    wins the bigger one is preferred. We play sensibly and go for blocks; the opponent does
    too, or with mimic=True picks like the learned model says it does."""
    hands = (me, opp)
    passes = 0
    while True:
        hand = hands[turn]
        moves = legal(hand, left, right)
        while not moves and yard:
            hand.append(yard.pop())
            moves = legal(hand, left, right)
        if not moves:
            passes += 1
            if passes >= 2:
                a = sum(t[0] + t[1] for t in me)
                b = sum(t[0] + t[1] for t in opp)
                return 0.0 if a == b else (1.0 + 0.01 * (b - a) if a < b else -1.0 - 0.01 * (a - b))
            turn ^= 1
            continue
        passes = 0
        best, best_s = None, -1e9
        if (mimic and turn == 1) or (me_like_model and turn == 0):
            # sample from the learned model: argmax of score + Gumbel noise = a softmax draw
            for m in moves:
                s = opponent_appeal(hand, m[0], m[1], m[2], counts, (), len(yard),
                                    opp_style if turn == 1 else OPPONENT_MODEL)                     - math.log(-math.log(rng.random() or 1e-12))
                if s > best_s:
                    best, best_s = m, s
        else:
            other = hands[turn ^ 1]
            for m in moves:
                s = move_score(hand, m[0], m[1], m[2]) + rng.random() * 1.5
                nl, nr = m[1], m[2]
                if not any(nl in o or nr in o for o in other):
                    s += BLOCK_BONUS                  # it leaves the other side nothing to play
                if s > best_s:
                    best, best_s = m, s
        t, left, right = best
        hand.remove(t)
        if counts is not None:
            counts[t[0]] += 1
            if t[0] != t[1]:
                counts[t[1]] += 1
        if not hand:
            if turn == 0:
                return 1.0 + 0.01 * sum(x[0] + x[1] for x in opp)
            return -1.0 - 0.01 * sum(x[0] + x[1] for x in me)
        turn ^= 1


# --- exact solving of an imagined world ---------------------------------------------------
# In an imagined world every tile is placed, the boneyard's order too, so the rest of the game
# can be solved exactly, draws included, as long as it isn't too big.
EXACT_YARD = 4    # solve exactly once the boneyard has this many tiles or fewer
BUDGET = 5000     # positions per solve before giving up and playing it out instead


class TooBig(Exception):
    pass


def mask_pips(mask):
    total = 0
    while mask:
        low = mask & -mask
        total += PIPS[low.bit_length() - 1]
        mask ^= low
    return total


def negamax(mine, theirs, left, right, passed, yard, drawn, memo, budget):
    """Exact value for the side to move: +1 win, 0 tie, -1 loss. Stops looking at a win.

    yard is the boneyard in drawing order (tile bits) and drawn how many are already taken."""
    key = (mine, theirs, left, right, passed, drawn)
    if key in memo:
        return memo[key]
    if len(memo) > budget:
        raise TooBig
    playable = mine & (SHOWS[left] | SHOWS[right])
    if not playable:
        if drawn < len(yard):                         # draw and look again
            value = negamax(mine | yard[drawn], theirs, left, right, passed, yard, drawn + 1, memo, budget)
        elif passed:                                  # both passed in a row: blocked game
            a, b = mask_pips(mine), mask_pips(theirs)
            value = 1 if a < b else (-1 if a > b else 0)
        else:
            value = -negamax(theirs, mine, left, right, True, yard, drawn, memo, budget)
        memo[key] = value
        return value
    value = -2
    rest = playable
    while rest and value < 1:
        low = rest & -rest
        rest ^= low
        a, b = TILES[low.bit_length() - 1]
        after = mine ^ low
        if not after:
            value = 1
            break
        options = []
        if a == left or b == left:
            options.append((b if a == left else a, right))
        if (a == right or b == right) and left != right:
            options.append((left, b if a == right else a))
        for nl, nr in options:
            v = -negamax(theirs, after, nl, nr, False, yard, drawn, memo, budget)
            if v > value:
                value = v
                if value == 1:
                    break
    memo[key] = value
    return value


class ExpertBot:
    """seat       - which seat it plays
    time_limit - seconds to think per decision (default 0.3)
    samples    - optional fixed number of imagined opponent hands instead of a time limit
    sharpness  - how much it trusts the soft clues (0 = only the hard facts)
    seed       - optional, makes a game reproducible
    global_opening - True when the game opened by the engine's rule (the highest double of
                 BOTH hands opens), which tells us about the opponent's hand even when we
                 opened; False when each game's opener simply plays their own best tile
    """

    def __init__(self, seat, time_limit=0.3, samples=None, sharpness=1.0, seed=None, prune=True,
                 global_opening=True, mimic=True, exact_yard=EXACT_YARD, budget=BUDGET, me_like_model=True,
                 memory=None):
        self.seat = seat
        self.opponent = 1 - seat
        self.time_limit = time_limit
        self.samples = samples
        self.sharpness = sharpness
        self.prune = prune       # drop weak candidates early to think more about the good ones
        self.global_opening = global_opening
        self.mimic = mimic       # in playouts, the opponent plays like the learned model
        self.exact_yard = exact_yard
        self.budget = budget
        self.me_like_model = me_like_model
        # evidence for each style (log scale). Pass the same dict to the next game's bot and it
        # keeps learning the same opponent from game to game.
        self.style_evidence = memory if memory is not None else {name: 0.0 for name in STYLES}
        self.rng = random.Random(seed)
        self.lacks = set()       # numbers the opponent surely doesn't hold right now
        self.never = set()       # tiles the opening shows they weren't dealt (until they draw)
        self.clues = []          # opponent choices since their last draw (see _clue)
        self.my_lacks = set()    # numbers the opponent believes WE don't hold (from our draws)
        self._after_me = None    # the table right after our last move
        self._opening_read = False

    # --- what the opening says --------------------------------------------------------------
    def _read_opening(self, view, moves):
        """The opener plays their highest double, or their heaviest tile if they hold no double.
        So the opening shows tiles the opponent was not dealt: higher doubles, and if it wasn't a
        double, every double and every heavier tile. With the engine's rule (the highest double
        of both hands opens) this holds for the opponent whoever opened."""
        self._opening_read = True
        board = view["board"]
        if not board:
            tile, they_opened = norm(moves[0][0]), False
        elif len(board) == 1:
            tile, they_opened = norm(board[0]), True
        else:
            return
        if not they_opened and not self.global_opening:
            return
        heft = lambda t: (t[0] + t[1], max(t))
        if tile[0] == tile[1]:
            self.never = {t for t in TILES if t[0] == t[1] and t[0] > tile[0]}
        else:
            self.never = {t for t in TILES if t[0] == t[1] or heft(t) > heft(tile)}

    # The platform may call this after each opponent turn; the bot reads the table itself.
    def observe_opponent_turn(self, ends, draws, played):
        pass

    # --- what the opponent's turn showed -------------------------------------------------
    def _learn(self, view):
        before, self._after_me = self._after_me, None
        board = view["board"]
        if before is None:
            # first decision of the game: if the opponent opened, that's a forced move, no clue
            return
        grown = len(board) - before["board_len"]
        my_draws = len(view["my_hand"]) - before["hand_len"]
        their_draws = before["yard"] - view["boneyard_size"] - my_draws
        if grown == 2 and my_draws == 0 and their_draws == 0:
            # we passed in between (boneyard empty), so they played twice: what we knew still holds
            self._learn_two_plays(before, board)
            self._weigh_styles(view, 2)
            return
        if grown not in (0, 1) or my_draws < 0 or their_draws < 0:
            self.lacks, self.clues, self.never = set(), [], set()   # can't explain it: start over
            return
        ends = before["ends"]
        played = grown == 1
        if their_draws > 0:
            # all their tiles, old and newly drawn (bar the one they played), missed these ends
            self.lacks = set(ends)
            self.clues = []
            self.never = set()      # a drawn tile may be one they weren't dealt
        elif not played:
            self.lacks |= set(ends)
        if played:
            if board[1:] == before["board"]:
                tile, side = norm(board[0]), LEFT
            else:
                tile, side = norm(board[-1]), "R"
            self.clues.append(self._clue(ends, tile, side, before["board"], before["yard"] - their_draws))
            self.clues = self.clues[-6:]
            self._weigh_styles(view, 1)
        if my_draws > 0:
            # what the opponent learns from our draws, the way it reasons about them
            now = (board[0][0], board[-1][1])
            if my_draws > 1:
                self.my_lacks = set(now)
            else:
                self.my_lacks |= set(now)

    def _clue(self, ends, tile, side, board_before, yard):
        """One opponent choice and what they saw when they made it."""
        return (ends, tile, side, board_counts(board_before), yard, frozenset(self.my_lacks))

    def _learn_two_plays(self, before, board):
        """Two opponent plays in a row. If both went on the same side their order is clear and
        both become clues; one on each side, we can't tell which came first, so no clue."""
        old = before["board"]
        k = next((i for i in range(len(board) - len(old) + 1) if board[i:i + len(old)] == old), None)
        if k is None:
            self.lacks, self.clues, self.never = set(), [], set()
            return
        left_new, right_new = board[:k], board[k + len(old):]
        ends = before["ends"]
        if len(left_new) == 2:          # board[1] went down first, then board[0]
            plays = [(norm(board[1]), LEFT), (norm(board[0]), LEFT)]
        elif len(right_new) == 2:       # board[-2] first, then board[-1]
            plays = [(norm(board[-2]), "R"), (norm(board[-1]), "R")]
        else:
            return
        table = list(old)
        for n, (tile, side) in enumerate(plays):
            self.clues.append(self._clue(ends, tile, side, table, 0))
            table = [tile] + table if side == LEFT else table + [tile]
            ends = ends_after(ends, tile, side)
            if n == 0:
                self.my_lacks |= set(ends)      # then we passed on these ends
        self.clues = self.clues[-6:]

    def _remember(self, view, move):
        tile, side = move
        board = list(view["board"])
        if not board:
            new_board = [tuple(tile)]
        elif side == LEFT:
            left = board[0][0]
            new_board = [tile if tile[1] == left else (tile[1], tile[0])] + board
        else:
            right = board[-1][1]
            new_board = board + [tile if tile[0] == right else (tile[1], tile[0])]
        self._after_me = {
            "board": [tuple(t) for t in new_board],
            "board_len": len(new_board),
            "hand_len": len(view["my_hand"]) - 1,
            "yard": view["boneyard_size"],
            "ends": (new_board[0][0], new_board[-1][1]),
        }

    # --- how well an imagined hand explains the opponent's choices ------------------------
    # --- which style the opponent plays ---------------------------------------------------
    def _clue_log_prob(self, held, clue, style):
        """log P(the opponent made this choice | they held `held`, they play `style`)."""
        ends, tile, side, counts, yard, my_lacks = clue
        moves = legal(held, ends[0], ends[1])
        if len(moves) < 2:
            return 0.0
        scores = [self.sharpness * opponent_appeal(held, m[0], m[1], m[2], counts, my_lacks, yard, style)
                  for m in moves]
        top = max(scores)
        norm_sum = sum(math.exp(x - top) for x in scores)
        chosen = ends_after(ends, tile, side)
        for m, x in zip(moves, scores):
            if m[0] == tile and (m[1], m[2]) == chosen:
                return x - top - math.log(norm_sum)
        return -50.0                                  # this hand couldn't have made that move

    def _weigh_styles(self, view, new):
        """The last `new` clues are fresh: average how likely each style made those choices over
        hands the opponent may hold, and add that to the evidence for each style."""
        their_n = view["players"][self.opponent]["tiles_left"]
        seen = {norm(t) for t in view["my_hand"]} | {norm(t) for t in view["board"]}
        unseen = [t for t in TILES if t not in seen]
        fits = [t for t in unseen
                if t[0] not in self.lacks and t[1] not in self.lacks and t not in self.never]
        if len(fits) < their_n or not self.clues:
            return
        fresh = self.clues[-new:]
        likely = {name: 0.0 for name in STYLES}
        hands = 40
        for _ in range(hands):
            held = self.rng.sample(fits, their_n)
            # before the fresh choices they also held the tiles they played in them
            for clue in reversed(fresh):
                held = held + [clue[1]]
                for name, style in STYLES.items():
                    likely[name] += math.exp(self._clue_log_prob(held, clue, style)) / hands
        for name in STYLES:
            self.style_evidence[name] += math.log(likely[name] / len(fresh) + 1e-9)
        top = max(self.style_evidence.values())
        for name in STYLES:                           # keep the numbers tame
            self.style_evidence[name] = max(self.style_evidence[name] - top, -30.0)

    def style_odds(self):
        """{style: probability} that the opponent plays that way, from the evidence so far."""
        top = max(self.style_evidence.values())
        raw = {name: math.exp(e - top) for name, e in self.style_evidence.items()}
        total = sum(raw.values())
        return {name: r / total for name, r in raw.items()}

    # --- how well an imagined hand explains the opponent's choices ------------------------
    def _log_weight(self, hand, odds=None):
        """log P(their recent choices | they now hold `hand`), mixing the styles by how much we
        believe in each."""
        if not self.sharpness or not self.clues:
            return 0.0
        odds = odds or self.style_odds()
        mix = 0.0
        for name, p in odds.items():
            if p < 0.02:
                continue
            style = STYLES[name]
            held = list(hand)
            total = 0.0
            # walk back through their choices: before each one they also held the tiles played since
            for clue in reversed(self.clues):
                held.append(clue[1])
                total += self._clue_log_prob(held, clue, style)
            mix += p * math.exp(max(total, -60.0))
        return math.log(mix) if mix > 0 else -60.0

    # --- what it believes the opponent holds ------------------------------------------------
    def belief(self, game, worlds=400):
        """{tile: probability the opponent holds it} for every tile we can't see, from what the
        bot knows right now (call it after choose, before the move is played)."""
        view = game.state(for_seat=self.seat)
        seen = {norm(t) for t in view["my_hand"]} | {norm(t) for t in view["board"]}
        unseen = [t for t in TILES if t not in seen]
        their_n = view["players"][self.opponent]["tiles_left"]
        fits = [t for t in unseen
                if t[0] not in self.lacks and t[1] not in self.lacks and t not in self.never]
        if len(fits) < their_n:
            fits = unseen
        held = {t: 0.0 for t in unseen}
        total = 0.0
        for _ in range(worlds):
            their = self.rng.sample(fits, their_n)
            w = math.exp(max(-30.0, self._log_weight(their)))
            total += w
            for t in their:
                held[t] += w
        return {t: held[t] / total for t in unseen}

    # --- the decision ----------------------------------------------------------------------
    def choose(self, game, moves):
        view = game.state(for_seat=self.seat)
        self._learn(view)
        if not self._opening_read:
            self._read_opening(view, moves)
        if len(moves) == 1:
            self._remember(view, moves[0])
            return moves[0]

        hand = [tuple(t) for t in view["my_hand"]]
        board = view["board"]
        their_n = view["players"][self.opponent]["tiles_left"]
        seen = {norm(t) for t in hand} | {norm(t) for t in board}
        unseen = [t for t in TILES if t not in seen]
        fits = [t for t in unseen
                if t[0] not in self.lacks and t[1] not in self.lacks and t not in self.never]
        if len(fits) < their_n:                       # our deductions don't add up: drop them
            self.lacks, self.clues, self.never = set(), [], set()
            fits = unseen
        must_be_yard = [t for t in unseen if t not in fits]
        left, right = view["ends"]
        table = board_counts(board)
        odds = self.style_odds()
        # in each imagined world the opponent plays one style, picked as likely as we believe it:
        # while we're unsure, the worlds cover every way they might play
        style_names = list(odds)
        style_odds = [odds[n] for n in style_names]

        # candidates: (move, new_left, new_right, rest of my hand)
        cands = []
        for tile, side in moves:
            nl, nr = ends_after((left, right), tile, side)
            cands.append(((tile, side), nl, nr, [t for t in hand if t != norm(tile) and t != tile]))
        for i, (_, _, _, rest) in enumerate(cands):
            if not rest:                                # going out wins on the spot
                self._remember(view, cands[i][0])
                return cands[i][0]

        totals = [0.0] * len(cands)
        weights = [0.0] * len(cands)
        alive = list(range(len(cands)))
        start = time.perf_counter()
        worlds = 0
        next_cut = 24
        too_big = 0                                   # exact solves that ran out of budget
        while True:
            opp_style = STYLES[self.rng.choices(style_names, style_odds)[0]]
            their = self.rng.sample(fits, their_n)
            taken = set(their)
            yard = must_be_yard + [t for t in fits if t not in taken]
            self.rng.shuffle(yard)
            w = math.exp(max(-30.0, self._log_weight(their, odds)))
            exact = len(yard) <= self.exact_yard and (too_big < 3 or not yard)
            if exact:
                theirs = sum(BIT[INDEX[t]] for t in their)
                order = tuple(BIT[INDEX[t]] for t in reversed(yard))
            for i in alive:
                _, nl, nr, rest = cands[i]
                v = None
                if exact:
                    mine = sum(BIT[INDEX[norm(t)]] for t in rest)
                    try:
                        v = -negamax(theirs, mine, nl, nr, False, order, 0, {}, self.budget)
                    except TooBig:
                        too_big += 1
                if v is None:
                    counts = list(table)
                    a, b = cands[i][0][0]
                    counts[a] += 1
                    if a != b:
                        counts[b] += 1
                    v = playout(list(rest), list(their), list(yard), nl, nr, 1, self.rng, self.mimic, counts,
                                self.me_like_model, opp_style)
                totals[i] += w * v
                weights[i] += w
            worlds += 1
            spent = time.perf_counter() - start
            if self.samples is not None:
                if worlds >= self.samples:
                    break
            elif worlds >= 12 and spent >= self.time_limit:
                break
            # successive halving: drop the weaker half of the candidates now and then
            if self.prune and worlds >= next_cut and len(alive) > 2:
                alive.sort(key=lambda i: totals[i] / weights[i] if weights[i] else -9, reverse=True)
                alive = alive[: max(2, (len(alive) + 1) // 2)]
                next_cut *= 2
            if not yard and not must_be_yard and len(fits) == their_n:
                break                                   # nothing hidden: one world says it all

        self.last_worlds = worlds                     # how much it looked at (for measuring)
        best = max(alive, key=lambda i: totals[i] / weights[i] if weights[i] else -9)
        self._remember(view, cands[best][0])
        return cands[best][0]


def main():
    from domino.game import Game
    from domino.player import Player
    from tools.play import show_board, tile_str
    from tools.play_scoring import bot_turn, your_turn

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
