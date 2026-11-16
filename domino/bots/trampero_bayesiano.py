"""Bot «Trampero bayesiano»: deduce la mano del rival con Bayes y juega la jugada con más
probabilidad de ganar.

El dominó es un juego con información oculta (no vemos las fichas del rival ni las del pozo),
así que el bot combina las tres partes del tema de razonamiento con incertidumbre:

1. Inferencia bayesiana (tema 4.1). Del historial público saca dos tipos de pruebas:

   * Pruebas seguras: si el rival roba o pasa, en ese momento no tenía ninguna ficha con los
     números de las puntas; y quien abre la partida revela que no tenía un doble más alto (o
     ningún doble). Una mano que contradiga eso tiene probabilidad 0. El bot recuerda CUÁNDO
     se supo cada cosa, porque las fichas que el rival robó después pueden llevar esos números.
   * Pruebas blandas: la ficha que elige el rival dice algo de las que se guardó. El bot
     considera cuatro estilos de jugador (al azar; «pesado», que suelta primero las fichas con
     más puntos; «puntuador», que valora puntos, dobles y quedarse con fichas que encajen; y
     «estratega», una heurística ajustada con un algoritmo evolutivo, tema 5.3),
     y actualiza con el teorema de Bayes la probabilidad de cada estilo y el peso de cada mano
     imaginada:  P(mano | jugadas) ∝ P(jugadas | mano) · P(mano).

2. Árbol de decisión con MEU (tema 4.2). Imagina muchas manos del rival coherentes con todo
   lo anterior («mundos»), juega cada candidata hasta el final en cada mundo y se queda con la
   de mayor utilidad esperada (ganar 1, empatar 0,5, perder 0), ponderando cada mundo por su
   probabilidad. Las candidatas flojas se descartan pronto para dedicar el tiempo a las buenas.

3. Expectiminimax exacto en el final (temas 4.2 y 4.3). Cuando en el pozo quedan pocas fichas,
   en cada mundo resuelve el resto de la partida de forma exacta: minimax con poda en los
   turnos de los jugadores y nodos de probabilidad cuando alguien tiene que robar (cada ficha
   del pozo con la misma probabilidad). No da por conocido el orden del pozo.

Solo usa la librería estándar. Piensa un tiempo fijo por jugada (``think``, 1 s por
defecto), así que en la web, donde Python es más lento, piensa lo mismo con menos mundos.
"""

import math
import random
import time

from ..board import LEFT
from .base import Bot

# --- fichas como bits: 28 fichas, (a, b) con a <= b --------------------------------------
TILES = [(a, b) for a in range(7) for b in range(a, 7)]
INDEX = {t: i for i, t in enumerate(TILES)}
BIT = [1 << i for i in range(len(TILES))]
PIPS = [a + b for a, b in TILES]
SHOWS = [sum(BIT[i] for i, t in enumerate(TILES) if n in t) for n in range(7)]   # fichas con n

WIN, TIE, LOSS = 1.0, 0.5, 0.0          # utilidad: la misma que el ranking (gana / empata / pierde)
EXACT_YARD = 3                          # resolver exacto con 3 fichas o menos en el pozo
EXACT_BUDGET = 20000                    # posiciones por mundo antes de rendirse y simular
STYLES = ("azar", "pesado", "puntuador", "estratega")
SHARPNESS = {"pesado": 1.5, "puntuador": 0.6, "estratega": 0.6}   # cuánto se fía cada estilo

# Pesos de la heurística «estratega», ajustados con un algoritmo evolutivo (tema 5.3): 16
# individuos, 15 generaciones, fitness = victorias de la heurística sola contra el bot Scoring
# en 4.000 partidas. Validada en 20.000 partidas nuevas: 52,7 % frente al 46,9 % de la
# heurística «puntuador» de partida. Rasgos: puntos de la ficha, es doble, fichas mías que
# encajan después, números distintos que me quedan, deja las dos puntas iguales.
EVOLVED = (-0.37, 4.02, 1.52, 0.18, 6.57)


def norm(tile):
    a, b = tile
    return (a, b) if a <= b else (b, a)


def ends_after(ends, tile, side):
    """Números abiertos tras poner `tile` en `side` (ends es None con la mesa vacía)."""
    if ends is None:
        return tile[0], tile[1]
    left, right = ends
    if side == LEFT:
        return (tile[0] if tile[1] == left else tile[1]), right
    return left, (tile[1] if tile[0] == right else tile[0])


def legal(hand, left, right):
    """Jugadas como (ficha, nueva_izquierda, nueva_derecha, lado)."""
    out = []
    for t in hand:
        a, b = t
        if a == left or b == left:
            out.append((t, b if a == left else a, right, "L"))
        if (a == right or b == right) and left != right:
            out.append((t, left, b if a == right else a, "R"))
    return out


def opening_key(tile):
    """Cómo compara la regla de apertura dos fichas que no son dobles."""
    return (tile[0] + tile[1], max(tile))


# --- cómo puntúa una jugada cada estilo de jugador ---------------------------------------
def strategist_score(hand, tile, nl, nr):
    """Estilo «puntuador»: puntos, dobles y quedarse con fichas que encajen."""
    a, b = tile
    s = a + b + (4 if a == b else 0)
    for o in hand:
        if o != tile and (nl in o or nr in o):
            s += 2.5
    return s


def evolved_score(hand, tile, nl, nr):
    """Estilo «estratega»: la heurística ajustada con el algoritmo evolutivo."""
    a, b = tile
    follow = 0
    nums = set()
    for o in hand:
        if o != tile:
            if nl in o or nr in o:
                follow += 1
            nums.update(o)
    w = EVOLVED
    return (w[0] * (a + b) + w[1] * (a == b) + w[2] * follow + w[3] * len(nums)
            + w[4] * (nl == nr))


SCORERS = {"puntuador": strategist_score, "estratega": evolved_score}


def style_probs(style, hand, left, right):
    """P(jugada | mano, estilo) para cada jugada legal: un softmax de la puntuación del estilo."""
    moves = legal(hand, left, right)
    if style == "azar" or not moves:
        return {(m[0], m[3]): 1 / len(moves) for m in moves} if moves else {}
    if style == "pesado":
        scores = [m[0][0] + m[0][1] + (0.5 if m[0][0] == m[0][1] else 0) for m in moves]
    else:
        scores = [SCORERS[style](hand, m[0], m[1], m[2]) for m in moves]
    k = SHARPNESS[style]
    top = max(scores)
    ws = [math.exp(k * (s - top)) for s in scores]
    total = sum(ws)
    return {(m[0], m[3]): w / total for m, w in zip(moves, ws)}


def pick(style, hand, moves, rng, other=(), block=0.0):
    """Jugada que haría un jugador de ese estilo en una simulación.

    `block` premia las jugadas que dejan al otro sin ficha que encaje (le obligan a robar o pasar).
    """
    if style == "azar":
        return rng.choice(moves)
    best, best_s = None, -1e9
    for m in moves:
        t = m[0]
        if style == "pesado":
            s = t[0] + t[1] + (0.5 if t[0] == t[1] else 0)
        else:
            s = SCORERS[style](hand, t, m[1], m[2])
            if block:
                nl, nr = m[1], m[2]
                if not any(nl in o or nr in o for o in other):
                    s += block
        s += rng.random() * 0.3
        if s > best_s:
            best, best_s = m, s
    return best


# --- simulación rápida hasta el final ----------------------------------------------------
def playout(me, opp, yard, left, right, turn, rng, opp_style, block=0.0):
    """Juega el resto de la partida. Devuelve la utilidad para mí. turn: 0 yo, 1 el rival."""
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
            if passes >= 2:                          # nadie puede jugar: gana quien tenga menos puntos
                a = sum(t[0] + t[1] for t in me)
                b = sum(t[0] + t[1] for t in opp)
                return WIN if a < b else (LOSS if a > b else TIE)
            turn ^= 1
            continue
        passes = 0
        t, left, right, _ = pick("estratega" if turn == 0 else opp_style, hand, moves, rng,
                                 hands[turn ^ 1], block)
        hand.remove(t)
        if not hand:
            return WIN if turn == 0 else LOSS
        turn ^= 1


# --- expectiminimax exacto ---------------------------------------------------------------
class TooBig(Exception):
    pass


def _mask_pips(mask):
    total = 0
    while mask:
        low = mask & -mask
        total += PIPS[low.bit_length() - 1]
        mask ^= low
    return total


def expectiminimax(mine, theirs, yard, left, right, passes, memo):
    """Valor exacto (0-1) para el jugador al que le toca. mine/theirs/yard son máscaras de bits.

    Nodo de decisión: el máximo sobre sus jugadas (el rival minimiza mi valor, que es 1 - el suyo).
    Nodo de probabilidad: si no puede jugar y queda pozo, roba; cada ficha del pozo igual de probable.
    """
    key = (mine, theirs, yard, left, right, passes)
    hit = memo.get(key)
    if hit is not None:
        return hit
    if len(memo) > EXACT_BUDGET:
        raise TooBig
    playable = mine & (SHOWS[left] | SHOWS[right])
    if not playable:
        if yard:                                     # nodo de probabilidad: roba una ficha al azar
            total, n, rest = 0.0, 0, yard
            while rest:
                low = rest & -rest
                rest ^= low
                total += expectiminimax(mine | low, theirs, yard ^ low, left, right, passes, memo)
                n += 1
            value = total / n
        elif passes >= 1:                            # cerrado: gana quien tenga menos puntos
            a, b = _mask_pips(mine), _mask_pips(theirs)
            value = WIN if a < b else (LOSS if a > b else TIE)
        else:
            value = 1 - expectiminimax(theirs, mine, yard, left, right, passes + 1, memo)
    else:
        value = 0.0
        rest = playable
        while rest and value < WIN:
            low = rest & -rest
            rest ^= low
            a, b = TILES[low.bit_length() - 1]
            new_mine = mine ^ low
            if not new_mine:
                value = WIN
                break
            options = set()
            if a == left or b == left:
                options.add((b if a == left else a, right))
            if (a == right or b == right) and left != right:
                options.add((left, b if a == right else a))
            for nl, nr in options:
                v = 1 - expectiminimax(theirs, new_mine, yard, nl, nr, 0, memo)
                if v > value:
                    value = v
    memo[key] = value
    return value


def _mask(tiles):
    m = 0
    for t in tiles:
        m |= BIT[INDEX[t]]
    return m


class TramperoBayesianoBot(Bot):
    """Bayes para deducir la mano del rival, MEU para elegir y expectiminimax en el final.

    seat  - el asiento (0 o 1)
    think - segundos de pensar por jugada
    seed  - para que la partida se pueda repetir
    """

    @classmethod
    def get_name(cls):
        return "Trampero bayesiano"

    @classmethod
    def get_authors(cls):
        return ["Marcos Felgueroso"]

    @classmethod
    def get_description(cls):
        return ("Deduces the opponent's hand with Bayes (draws, passes, the opening and the tiles "
                "they choose), plays out many possible hands and keeps the move with the highest "
                "expected chance of winning; solves the endgame exactly, draws included.")

    @classmethod
    def create(cls, seat, seed=None, **options):
        return cls(seat, seed=seed, **options)

    def __init__(self, seat, think=1.0, seed=None, block=8.0, soft=True, exact_yard=EXACT_YARD):
        self.seat = seat
        self.think = think
        self.block = block
        self.soft = soft
        self.exact_yard = exact_yard
        self.rng = random.Random(seed)
        self.styles = {s: 1 / len(STYLES) for s in STYLES}   # P(estilo), se actualiza con Bayes
        self._seen_plays = set()                              # jugadas del rival ya usadas
        self.last_info = {}

    # --- 1. lo que dice el historial (pruebas seguras y blandas) ---------------------------
    def _read_history(self, view):
        me, opp = self.seat, 1 - self.seat
        ends = None
        constraints = []          # (momento, máscara de fichas que el rival NO tenía entonces)
        opp_draws = []            # momentos en que el rival robó
        plays = []                # jugadas libres del rival: (momento, ficha, lado, puntas antes)
        drew = {0: False, 1: False}
        for i, e in enumerate(view["history"]):
            seat, action = e["seat"], e["action"]
            if action == "play":
                tile, side = tuple(e["tile"]), e["side"]
                before = ends
                ends = ends_after(ends, tile, side)
                if before is None:
                    constraints.extend(self._opening_constraints(seat, norm(tile), i))
                elif seat == opp:
                    if drew[opp]:     # robó hasta poder jugar: ninguna de las que guarda encaja
                        constraints.append((i, SHOWS[before[0]] | SHOWS[before[1]]))
                    else:
                        plays.append((i, norm(tile), side, before))
                drew[seat] = False
            elif action == "draw":
                drew[seat] = True
                if seat == opp:
                    opp_draws.append(i)
            elif action == "pass":
                if seat == opp and ends is not None:
                    constraints.append((i, SHOWS[ends[0]] | SHOWS[ends[1]]))
                drew[seat] = False
        return constraints, opp_draws, plays

    def _opening_constraints(self, opener, tile, i):
        """Se abre con el doble más alto de la mesa (o, sin dobles, con la ficha más alta).

        Abra quien abra, eso dice qué fichas NO había en la mano inicial del rival: ningún doble
        mayor que el de la apertura (o ningún doble y ninguna ficha más alta, si no fue un doble).
        """
        a, b = tile
        if a == b:
            bad = _mask((d, d) for d in range(a + 1, 7))
        else:
            bad = _mask((d, d) for d in range(7))
            bad |= _mask(t for t in TILES if t[0] != t[1] and opening_key(t) > opening_key(tile))
        return [(i, bad)]

    # --- 2. imaginar manos del rival coherentes con las pruebas seguras --------------------
    def _sampler(self, view, constraints, opp_draws):
        known = set(norm(t) for t in view["my_hand"]) | set(norm(t) for t in view["board"])
        unseen = [t for t in TILES if t not in known]
        need = {}
        for t in unseen:
            bit = BIT[INDEX[t]]
            times = [when for when, bad in constraints if bad & bit]
            need[t] = max(times) if times else -1     # debió robarla después de ese momento
        thresholds = sorted(set(need.values()) - {-1})
        cap = {th: sum(1 for d in opp_draws if d > th) for th in thresholds}
        k = view["opponent_tiles"]

        def sample():
            order = unseen[:]
            self.rng.shuffle(order)
            counts = dict.fromkeys(thresholds, 0)
            hand = []
            for t in order:
                nt = need[t]
                if nt >= 0:
                    if any(counts[th] >= cap[th] for th in thresholds if th <= nt):
                        continue
                    for th in thresholds:
                        if th <= nt:
                            counts[th] += 1
                hand.append(t)
                if len(hand) == k:
                    break
            if len(hand) < k:                         # deducciones incoherentes: no las uses
                hand = self.rng.sample(unseen, k)
            hs = set(hand)
            return hand, [t for t in unseen if t not in hs]

        return sample

    # --- Bayes sobre las jugadas libres del rival ------------------------------------------
    def _recent_plays(self, plays, opp_draws):
        last_draw = opp_draws[-1] if opp_draws else -1
        return [p for p in plays if p[0] > last_draw]

    def _world_weights(self, hand, recent):
        """P(jugadas recientes | mano, estilo) para cada estilo."""
        lik = {}
        for s in STYLES:
            p = 1.0
            for idx, (when, tile, side, before) in enumerate(recent):
                then = hand + [r[1] for r in recent[idx:]]   # la mano que tenía al jugar
                probs = style_probs(s, then, before[0], before[1])
                p *= probs.get((tile, side), probs.get((tile, "L"), 1e-6))
            lik[s] = p
        return lik

    def _update_styles(self, recent, worlds):
        """Teorema de Bayes sobre el estilo del rival, con las jugadas que aún no había usado."""
        new = [r for r in recent if r[0] not in self._seen_plays]
        if not new or not worlds:
            return
        for s in STYLES:
            avg = 0.0
            for hand, _ in worlds:
                p = 1.0
                for idx, r in enumerate(recent):
                    if r[0] not in self._seen_plays and r in new:
                        then = hand + [q[1] for q in recent[idx:]]
                        probs = style_probs(s, then, r[3][0], r[3][1])
                        p *= probs.get((r[1], r[2]), probs.get((r[1], "L"), 1e-6))
                avg += p
            self.styles[s] *= avg / len(worlds)
        total = sum(self.styles.values()) or 1.0
        self.styles = {s: max(v / total, 1e-4) for s, v in self.styles.items()}
        total = sum(self.styles.values())
        self.styles = {s: v / total for s, v in self.styles.items()}
        self._seen_plays.update(r[0] for r in new)

    # --- 3. elegir: MEU sobre los mundos, con descarte progresivo --------------------------
    def choose(self, view, moves):
        start = time.perf_counter()
        hand = [norm(t) for t in view["my_hand"]]
        if len(moves) == 1:
            return moves[0]
        for m in moves:                                     # si puedo quedarme sin fichas, gano ya
            if len(hand) == 1 and norm(m[0]) == hand[0]:
                return m

        constraints, opp_draws, plays = self._read_history(view)
        sample = self._sampler(view, constraints, opp_draws)
        recent = self._recent_plays(plays, opp_draws)
        probe = [sample() for _ in range(24)]
        if self.soft:
            self._update_styles(recent, probe)

        left, right = view["ends"]
        yard_n = view["boneyard_size"]
        cands = list(range(len(moves)))
        score = [0.0] * len(moves)
        weight = [0.0] * len(moves)
        after = [(norm(t), *ends_after((left, right), t, side)) for t, side in moves]
        deadline = start + self.think
        hard_stop = start + max(2 * self.think, 1.0)    # muy lejos de los 5 s del límite
        batch, rounds, worlds_used = 12, 0, 0
        while True:
            for _ in range(batch):
                opp_hand, yard = sample()
                lik = self._world_weights(opp_hand, recent if self.soft else [])
                w = sum(self.styles[s] * lik[s] for s in STYLES)
                if w <= 0:
                    continue
                post = [self.styles[s] * lik[s] / w for s in STYLES]
                memo = {} if yard_n <= self.exact_yard else None
                for i in cands:
                    tile, nl, nr = after[i]
                    rest = [t for t in hand if t != tile]
                    if not rest:
                        v = WIN
                    else:
                        v = None
                        if memo is not None:
                            try:
                                v = 1 - expectiminimax(_mask(opp_hand), _mask(rest), _mask(yard), nl, nr, 0, memo)
                            except TooBig:
                                memo = None
                        if v is None:
                            style = self.rng.choices(STYLES, post)[0]
                            pool = yard[:]
                            self.rng.shuffle(pool)
                            v = playout(rest, list(opp_hand), pool, nl, nr, 1, self.rng, style, self.block)
                    score[i] += w * v
                    weight[i] += w
                worlds_used += 1
                if time.perf_counter() > hard_stop:
                    break
            rounds += 1
            now = time.perf_counter()
            if now > deadline or now > hard_stop or len(cands) == 1:
                break
            if rounds >= 2 and len(cands) > 2:           # descarta la mitad peor
                cands.sort(key=lambda i: score[i] / weight[i] if weight[i] else -1, reverse=True)
                cands = cands[: max(2, (len(cands) + 1) // 2)]
            batch = min(batch * 2, 96)

        best = max(cands, key=lambda i: score[i] / weight[i] if weight[i] else -1)
        self.last_info = {
            "styles": dict(self.styles),
            "worlds": worlds_used,
            "expected": {str(moves[i]): round(score[i] / weight[i], 3) for i in range(len(moves)) if weight[i]},
            "seconds": round(time.perf_counter() - start, 3),
        }
        return moves[best]
