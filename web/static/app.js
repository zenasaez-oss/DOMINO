// Draws the game and sends your moves to it.
// All the rules live in the Python engine (domino/), which runs in the page through
// Pyodide; web/session.py is the bridge. This file only displays, and gives the bot
// a face: the character you play against thinks for a moment before each move and comments on it.

const $ = (id) => document.getElementById(id);

// Python files the page loads into Pyodide, relative to this page
const PY_FILES = [
  "domino/__init__.py", "domino/board.py", "domino/deck.py", "domino/domino.py",
  "domino/game.py", "domino/hand.py", "domino/player.py", "domino/rules.py",
  "domino/turn_manager.py",
  "domino/bots/__init__.py", "domino/bots/greedy.py", "domino/bots/scoring.py",
  "domino/bots/montecarlo.py", "domino/bots/expert.py",
  "web/__init__.py", "web/session.py",
];
// the page lives in web/, the packages next to it (a page can set its own PY_ROOT)
const PY_ROOT = window.PY_ROOT || "../";

let session = null;     // the web.session Python module

// Which of the 9 cells (0-8) of a 3x3 grid hold a dot, for 0..6
const PIPS = {
  0: [], 1: [4], 2: [0, 8], 3: [0, 4, 8],
  4: [0, 2, 6, 8], 5: [0, 2, 4, 6, 8], 6: [0, 2, 3, 5, 6, 8],
};
const SIDE_NAME = { L: "izquierda", R: "derecha" };
const YOU = 0, BOT = 1;
const THINK_MS = [900, 1700];   // how long the character seems to think before a move

// Who you play against: one character per level, each with their own way of talking.
// In what they say, {t} is a tile and {n} a number of tiles.
const CHARACTERS = {
  easy: {
    name: "Paquito",
    think: "Mmm",
    says: {
      youOpen: ["¡Tú pimero! Con el {t}."],
      play: ["¡Ta! El {t}.", "¡Pon! {t}.", "¡Mía! El {t}, ji, ji."],
      open: ["¡Yo! ¡Yo! El {t}."],
      lastTile: ["¡El {t}! ¡Me queda una!"],
      drawPlay: ["Cojo {n}… ¡y el {t}!"],
      drawPass: ["Cojo {n}… ¡no hay! Paso."],
      pass: ["No teno… paso."],
      youDraw: ["¡Ji, ji! ¡A cogé!", "¡Al montón!"],
      botWins: ["¡Gané! ¡Gané! ¡Bibi!", "¡Dominó! ¡Aplausos!"],
      botWinsBlocked: ["¡Gané por puntitos!"],
      youWin: ["¡Buaaa! ¡Otra!", "¡No vale! ¡Buaaa!"],
      youWinBlocked: ["¡Buaaa! Otra…"],
      tie: ["¿Empate? ¡Otra!"],
    },
  },
  medium: {
    name: "Rosa",
    think: "Déjame pensar, mi arma",
    says: {
      youOpen: ["Venga, mi arma, sales tú con el {t}.", "Te toca abrir con el {t}, cielo."],
      play: ["¡Olé! Ahí va el {t}.", "El {t}, y que corra el aire.", "Toma el {t}, cariño."],
      open: ["Salgo yo con el {t}, con permiso."],
      lastTile: ["El {t}… ¡y me queda una, mi alma!"],
      drawPlay: ["Me ha tocado robar {n}… pero ahí va el {t}."],
      drawPass: ["Robo {n} y nada, hija. Paso."],
      pass: ["Paso, que no llevo ná."],
      youDraw: ["Ay, a robar, mi arma.", "¿No llevas? Al pozo, cielo."],
      botWins: ["¡Dominó! ¡Olé y olé!", "¡Dominó! Esto es arte, chiquillo."],
      botWinsBlocked: ["Cerrada, y gano por puntos. ¡Olé!"],
      youWin: ["¡Ay, madre! Me has ganado.", "¡Qué arte tienes! Otra, que me pico."],
      youWinBlocked: ["Cerrada y me ganas por puntos… ¡qué apuro!"],
      tie: ["Tablas, mi arma. ¿Otra?"],
    },
  },
  hard: {
    name: "Paco",
    think: "Mmm, déjame pensar",
    says: {
      youOpen: ["Venga, chaval, sales tú con el {t}.", "Te toca abrir con el {t}. Sin prisa, que no hay prisa."],
      play: ["¡Ahí va el {t}!", "El {t}, y a ver qué haces.", "Pongo el {t}. Te toca, chaval.",
             "El {t}, que lo tenía guardado.", "{t}. Cincuenta años jugando en la plaza…"],
      open: ["Salgo yo. ¡El {t}!", "Abro con el {t}, como manda la tradición."],
      lastTile: ["El {t}… y me queda una. ¡Ojo!"],
      drawPlay: ["He tenido que robar {n}… pero ahí va el {t}."],
      drawPass: ["Robo {n} y nada de nada. Paso."],
      pass: ["Paso. No llevo nada.", "Me has cerrado… paso."],
      youDraw: ["Je, je… a robar, chaval.", "¿No llevas? Al pozo."],
      botWins: ["¡Dominó! Así se juega en mi barrio.", "¡Dominó! Otra vez será, chaval.", "¡Dominó! ¡Salud!"],
      botWinsBlocked: ["Cerrada, y gano por puntos. ¡Je, je!"],
      youWin: ["¡Bah! Has tenido suerte. Esta no cuenta, ¿eh?", "¡Recórcholis! Otra, que me pico."],
      youWinBlocked: ["¿Cerrada y me ganas por puntos? ¡Hmpf! Revancha."],
      tie: ["Tablas. ¿Echamos otra?"],
    },
  },
  superhard: {
    name: "C06",
    think: "CALCULANDO",
    thinkMs: [200, 500],   // it really thinks for 1.5 s on top of this (web/session.py)
    says: {
      youOpen: ["INICIO DE PARTIDA. SALES TÚ CON EL {t}."],
      play: ["JUGADA ÓPTIMA: {t}.", "EJECUTANDO {t}.", "{t} COLOCADO. PROBABILIDAD DE VICTORIA: EN AUMENTO."],
      open: ["APERTURA: {t}."],
      lastTile: ["{t}. FICHAS RESTANTES: 1."],
      drawPlay: ["ROBO {n}. RECALCULANDO… {t}."],
      drawPass: ["ROBO {n}. SIN JUGADAS VÁLIDAS. PASO."],
      pass: ["SIN JUGADAS VÁLIDAS. PASO."],
      youDraw: ["NO TIENES ESE NÚMERO. ANOTADO.", "ROBAS. TOMO NOTA."],
      botWins: ["DOMINÓ. VICTORIA CALCULADA.", "DOMINÓ. ERA PREVISIBLE."],
      botWinsBlocked: ["PARTIDA CERRADA. GANO POR PUNTOS."],
      youWin: ["ERROR 404: VICTORIA NO ENCONTRADA.", "IMPOSIBLE… REINICIANDO ORGULLO."],
      youWinBlocked: ["CERRADA. PIERDO POR PUNTOS. ANALIZANDO…"],
      tie: ["TABLAS. SOLICITO REVANCHA."],
    },
  },
};
let level = "hard";
let character = CHARACTERS[level];
const pick = (list) => list[Math.floor(Math.random() * list.length)];

let state = null;
let selected = null;          // tile picked in your hand that fits on both ends
let boardBefore = new Set();  // tiles on the board before the last update
let handBefore = new Set();   // tiles in your hand before the last update
let thinking = false;         // the character is about to move
let botTimer = null;
let moodTimer = null;
let counted = false;          // this game's result is already in the scoreboard
let wins = loadWins();

// --- talking to the Python engine ---
async function loadEngine() {
  // a page can pass its own Pyodide options (e.g. where to find Python's standard library)
  const options = window.pyodideOptions ? await window.pyodideOptions() : {};
  const pyodide = await loadPyodide(options);
  const home = "/home/pyodide/";  // Pyodide's working folder, already on Python's import path
  for (const path of PY_FILES) {
    const res = await fetch(PY_ROOT + path, { cache: "no-cache" });  // always the latest version
    if (!res.ok) throw new Error(`No se pudo cargar ${path}`);
    pyodide.FS.mkdirTree(home + path.slice(0, path.lastIndexOf("/")));
    pyodide.FS.writeFile(home + path, await res.text());
  }
  return pyodide.pyimport("web.session");
}

// Each session function answers with the game as JSON, or {"error": ...}
function call(fn) {
  const data = JSON.parse(fn());
  if (data.error) {
    $("hint").textContent = data.error;
    $("hint").className = "hint error";
    return null;
  }
  return data;
}

// The face and drink of the character being played, and their name everywhere
function face() {
  return $(`char-${level}`);
}

function seatCharacter(chosen) {
  level = chosen;
  character = CHARACTERS[level];
  $("figure").dataset.char = level;
  // (SVG elements have no .hidden property, so set the attribute itself)
  for (const svg of document.querySelectorAll(".char")) svg.toggleAttribute("hidden", svg.id !== `char-${level}`);
  for (const drink of document.querySelectorAll(".posavasos")) drink.toggleAttribute("hidden", drink.dataset.for !== level);
  $("bot-name").textContent = character.name;
  $("score-bot-name").textContent = character.name;
  face().dataset.mood = "idle";
}

function newGame(chosen) {
  seatCharacter(chosen);
  clearTimeout(botTimer);
  thinking = false;
  boardBefore = new Set();
  handBefore = new Set();
  counted = false;
  selected = null;
  $("seat-bot").classList.remove("cheers");
  const data = call(() => session.new_game(level));
  if (!data) return;
  if (data.current_seat === YOU) say(pick(character.says.youOpen), { t: data.opening_tile }, "idle");
  render(data);
  maybeBotTurn();
}

function yourMove(fn, reaction) {
  selected = null;
  const data = call(fn);
  if (!data) return;
  render(data);
  if (state.finished) reactToEnd();
  else if (reaction) say(pick(reaction), {}, "happy", true);
  maybeBotTurn();
}

const playTile = ([a, b], side) => yourMove(() => session.play(a, b, side));

// The character thinks for a moment, then moves
function maybeBotTurn() {
  if (state.finished || state.current_seat !== BOT) return;
  thinking = true;
  sayThinking();
  render(state);
  const [low, high] = character.thinkMs || THINK_MS;
  const wait = low + Math.random() * (high - low);
  botTimer = setTimeout(() => {
    thinking = false;
    const opening = state.board.length === 0;
    const data = call(() => session.bot_turn());
    if (!data) return;
    render(data);
    if (state.finished) reactToEnd();
    else reactToBotTurn(opening);
  }, wait);
}

// --- the character's face and words ---
function setMood(mood, backToIdle = false) {
  face().dataset.mood = mood;
  clearTimeout(moodTimer);
  if (backToIdle) moodTimer = setTimeout(() => { face().dataset.mood = "idle"; }, 2200);
}

function say(template, { t, n } = {}, mood = "idle", backToIdle = false) {
  const bubble = $("bubble");
  bubble.replaceChildren();
  // put tiles in their own span so they stand out
  template.split(/(\{t\}|\{n\})/).forEach((part) => {
    if (part === "{t}") {
      const span = document.createElement("span");
      span.className = "tile-name";
      span.textContent = tileText(t);
      bubble.appendChild(span);
    } else {
      bubble.append(part === "{n}" ? String(n) : part);
    }
  });
  bubble.classList.remove("pop");
  void bubble.offsetWidth;  // restart the pop animation
  bubble.classList.add("pop");
  setMood(mood, backToIdle);
}

function sayThinking() {
  const bubble = $("bubble");
  bubble.replaceChildren(character.think);
  const dots = document.createElement("span");
  dots.className = "dots";
  dots.innerHTML = "<i></i><i></i><i></i>";
  bubble.appendChild(dots);
  setMood("think");
}

function reactToBotTurn(opening) {
  const turn = state.bot_turn;
  const draws = turn.filter((e) => e.action === "draw").length;
  const play = turn.find((e) => e.action === "play");
  const left = state.players[BOT].tiles_left;
  if (play && draws) say(pick(character.says.drawPlay), { t: play.tile, n: draws }, "idle");
  else if (play && opening) say(pick(character.says.open), { t: play.tile }, "happy", true);
  else if (play && left === 1) say(pick(character.says.lastTile), { t: play.tile }, "happy", true);
  else if (play) say(pick(character.says.play), { t: play.tile }, "happy", true);
  else if (draws) say(pick(character.says.drawPass), { n: draws }, "sad", true);
  else say(pick(character.says.pass), {}, "sad", true);
}

function reactToEnd() {
  const blocked = state.end_reason === "blocked";
  if (state.winner === BOT) {
    say(pick(blocked ? character.says.botWinsBlocked : character.says.botWins), {}, "happy");
    $("seat-bot").classList.add("cheers");  // he raises his glass
  } else if (state.winner === YOU) {
    say(pick(blocked ? character.says.youWinBlocked : character.says.youWin), {}, "angry");
    confetti();
  } else say(pick(character.says.tie), {}, "idle");
  renderResult();
}

// --- scoreboard (kept in this browser only) ---
function loadWins() {
  try {
    const saved = JSON.parse(localStorage.getItem("domino-wins"));
    if (saved && "you" in saved) return saved;
  } catch (e) { /* storage blocked: start from zero */ }
  return { you: 0, bot: 0, tie: 0 };
}

function countResult() {
  if (counted || !state.finished) return;
  counted = true;
  const key = state.winner === YOU ? "you" : state.winner === BOT ? "bot" : "tie";
  wins[key] += 1;
  try { localStorage.setItem("domino-wins", JSON.stringify(wins)); } catch (e) { /* fine */ }
}

// --- drawing tiles ---
function half(n) {
  const el = document.createElement("div");
  el.className = "half";
  for (let i = 0; i < 9; i++) {
    const cell = document.createElement("span");
    if (PIPS[n].includes(i)) cell.className = "pip";
    el.appendChild(cell);
  }
  return el;
}

function tileEl([a, b], { vertical = false } = {}) {
  const el = document.createElement("div");
  el.className = "tile" + (vertical ? " vertical" : "");
  el.title = `${a} | ${b}`;
  el.append(half(a), half(b));
  return el;
}

const sameTile = (t, u) => t[0] === u[0] && t[1] === u[1];
const tileKey = ([a, b]) => (a <= b ? `${a}${b}` : `${b}${a}`);
const isDouble = (t) => t[0] === t[1];
const movesFor = (tile) => state.my_moves.filter(([t]) => sameTile(t, tile));
const tileText = ([a, b]) => `[${a}|${b}]`;
const yourTurn = () => !state.finished && !thinking && state.current_seat === YOU;

// --- the board: one line of tiles laid out as a snake ---
function cssPx(name) {
  return parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name));
}

// Split the line into rows that fit the table; doubles stand crosswise and take less room
function snakeRows(board, width) {
  const gap = 3, wide = cssPx("--tile-w"), narrow = cssPx("--tile-h");
  const rows = [[]];
  let used = 0;
  board.forEach((tile, i) => {
    const w = (isDouble(tile) ? narrow : wide) + gap;
    if (used + w > width && rows.at(-1).length) {
      rows.push([]);
      used = 0;
    }
    rows.at(-1).push(i);
    used += w;
  });
  return rows;
}

function renderBoard() {
  const board = $("board");
  board.innerHTML = "";
  const tiles = state.board;

  if (tiles.length === 0) {
    const msg = document.createElement("p");
    msg.className = "board-msg";
    if (state.current_seat === YOU) {
      msg.append("Mesa limpia. Sales tú con el ");
      const name = document.createElement("span");
      name.className = "tile-name";
      name.textContent = tileText(state.opening_tile);
      msg.append(name, ".");
    } else {
      msg.textContent = `Mesa limpia. Sale ${character.name}.`;
    }
    board.appendChild(msg);
    boardBefore = new Set();
    return;
  }

  // which ends your selected tile can go to
  const targetSides = selected ? movesFor(selected).map(([, side]) => side) : [];
  const botPlayed = new Set(state.bot_turn.filter((e) => e.action === "play").map((e) => tileKey(e.tile)));
  const last = tiles.length - 1;

  const rows = snakeRows(tiles, board.clientWidth - 8);
  rows.forEach((indexes, r) => {
    const row = document.createElement("div");
    const back = r % 2 === 1;  // odd rows run right to left, so their tiles are shown turned
    row.className = "row" + (back ? " back" : "") + (rows.length === 1 ? " solo" : "");
    for (const i of indexes) {
      const t = tiles[i];
      const el = tileEl(back ? [t[1], t[0]] : t, { vertical: isDouble(t) });
      if (i === 0 || i === last) el.classList.add("open-end");
      const side = i === 0 ? "L" : i === last ? "R" : null;
      if (side && targetSides.includes(side)) {
        el.classList.add("target");
        el.title = `Poner ${tileText(selected)} aquí (${SIDE_NAME[side]})`;
        el.onclick = () => playTile(selected, side);
      }
      if (!boardBefore.has(tileKey(t)) && (boardBefore.size || tiles.length === 1)) {
        el.classList.add(botPlayed.has(tileKey(t)) ? "fresh-bot" : "fresh-you");
      }
      row.appendChild(el);
    }
    board.appendChild(row);
  });
  boardBefore = new Set(tiles.map(tileKey));
}

function renderSidePick() {
  const pickBox = $("side-pick");
  pickBox.hidden = !selected;
  if (!selected) return;
  const [left, right] = state.ends;
  $("pick-left").textContent = `◀ Izquierda (${left})`;
  $("pick-right").textContent = `Derecha (${right}) ▶`;
  $("pick-left").onclick = () => playTile(selected, "L");
  $("pick-right").onclick = () => playTile(selected, "R");
}

// --- seats ---
function renderYourHand() {
  const hand = $("your-hand");
  hand.innerHTML = "";

  for (const tile of state.my_hand) {
    const el = tileEl(tile, { vertical: true });
    if (handBefore.size && !handBefore.has(tileKey(tile))) el.classList.add("drawn");
    const moves = yourTurn() ? movesFor(tile) : [];
    if (moves.length) {
      el.classList.add("playable");
      el.tabIndex = 0;
      if (selected && sameTile(selected, tile)) el.classList.add("selected");
      const choose = () => {
        if (moves.length === 1) return playTile(tile, moves[0][1]);
        selected = selected && sameTile(selected, tile) ? null : tile;
        render(state);
      };
      el.onclick = choose;
      el.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choose(); } };
    } else if (yourTurn()) {
      el.classList.add("dim");
    }
    hand.appendChild(el);
  }
  handBefore = new Set(state.my_hand.map(tileKey));
}

function renderBot() {
  const left = state.players[BOT].tiles_left;
  $("bot-count").textContent = left === 1 ? "¡1 ficha!" : `${left} fichas`;
  // his tiles fan out in his hands: the more he holds, the tighter the fan
  const rack = $("bot-hand");
  rack.innerHTML = "";
  rack.style.setProperty("--n", left);
  rack.style.setProperty("--step", `${Math.min(11, 80 / Math.max(left, 1))}deg`);
  for (let i = 0; i < left; i++) {
    const back = document.createElement("span");
    back.className = "tile-back";
    back.style.setProperty("--i", i);
    rack.appendChild(back);
  }
}

// The boneyard as a pile of face-down tiles; when you must draw, it glows and you can tap it
function renderPile(canDraw) {
  const n = state.boneyard_size;
  const stack = $("pile-stack");
  const shown = Math.min(n, 14);
  const step = window.matchMedia("(max-width: 640px)").matches ? 3 : 4;
  stack.replaceChildren(...Array.from({ length: shown }, (_, i) => {
    const back = document.createElement("i");
    back.style.left = `${i * step}px`;
    back.style.bottom = `${(i % 2) * 1}px`;
    return back;
  }));
  stack.style.width = shown ? `${(shown - 1) * step + (step === 3 ? 16 : 20)}px` : "0";
  $("pile-count").textContent = n === 0 ? "vacío" : n;
  $("pile").classList.toggle("empty", n === 0);
  $("pile").disabled = !canDraw;
  $("pile").title = canDraw ? "Robar del pozo" : `Pozo: ${n} fichas`;
}

function renderStatus() {
  const mine = yourTurn();
  const turn = $("turn");
  turn.textContent = state.finished ? "Fin de la partida" : thinking ? `${character.name} está pensando…` : mine ? "Mi turno" : `Turno de ${character.name}`;
  turn.className = "turn" + (state.finished ? "" : mine ? " you" : " bot");
  $("seat-you").classList.toggle("active", mine);
  $("seat-bot").classList.toggle("active", !state.finished && !mine);

  // either side of the line: the number open at each end
  const first = state.board[0], last = state.board.at(-1);
  $("end-left").textContent = first ? first[0] : "—";
  $("end-right").textContent = last ? last[1] : "—";

  renderPile(mine && state.can_draw);

  const name = state.players[YOU].name;
  $("your-name").textContent = name;
  $("your-initial").textContent = name.charAt(0).toUpperCase();

  const hint = $("hint");
  hint.className = "hint" + (mine ? " prompt" : "");
  if (state.finished) hint.textContent = "Partida terminada.";
  else if (!mine) hint.textContent = `Espera a que juegue ${character.name}…`;
  else if (selected) hint.textContent = `¿Dónde pones el ${tileText(selected)}? Toca un extremo que brille.`;
  else if (state.my_moves.length) hint.textContent = "Toca una ficha iluminada para jugarla.";
  else if (state.can_draw) hint.textContent = "No llevas nada que case: roba del pozo.";
  else hint.textContent = "No llevas nada y el pozo está vacío: pasa.";

  $("draw-btn").disabled = !mine || !state.can_draw;
  $("pass-btn").disabled = !mine || !state.can_pass;
  $("draw-btn").classList.toggle("attention", mine && state.can_draw);
  $("pass-btn").classList.toggle("attention", mine && state.can_pass);
}

// The history as short sentences: "Paco abre con 6-6", "Tú pones 3-4 a la derecha"...
const pair = ([a, b]) => `${a}-${b}`;

function moveSentence(e, count) {
  const you = e.who === "you";
  if (e.action === "play") {
    if (e.opening) return `${you ? "abres" : "abre"} con ${pair(e.tile)}`;
    return `${you ? "pones" : "pone"} ${pair(e.tile)} a la ${SIDE_NAME[e.side]}`;
  }
  if (e.action === "draw") {
    if (you) return `robas un ${pair(e.tile)}`;
    return count > 1 ? `roba ${count} fichas` : "roba una ficha";
  }
  return you ? "pasas" : "pasa";
}

function renderLog() {
  // the character's draws in a row go on one line: you only see how many, not which
  const lines = [];
  for (const e of state.log) {
    const last = lines.at(-1);
    if (last && e.who === "bot" && e.action === "draw" && last.e.who === "bot" && last.e.action === "draw") last.count++;
    else lines.push({ e, count: 1 });
  }
  // newest first, so the last move is always in sight while you play
  $("log").replaceChildren(...lines.reverse().map(({ e, count }, i) => {
    const li = document.createElement("li");
    li.className = e.who + (i === 0 ? " latest" : "");
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = e.who === "you" ? "Tú" : character.name;
    li.append(who, ` ${moveSentence(e, count)}`);
    return li;
  }));
  $("log").scrollTop = 0;
}

function renderScore() {
  $("wins-you").textContent = wins.you;
  $("wins-bot").textContent = wins.bot;
  $("wins-tie").textContent = wins.tie;
}

function renderResult() {
  const dialog = $("result");
  const blocked = state.end_reason === "blocked";
  let title, text;
  if (state.winner === null) {
    title = "¡Tablas!";
    text = "La partida se ha cerrado y los dos sumáis lo mismo.";
  } else if (state.winner === YOU) {
    title = "¡Has ganado!";
    text = blocked ? "La partida se cerró y sumabas menos puntos." : `Te has quedado sin fichas antes que ${character.name}.`;
    text += ` Te llevas ${state.score} puntos.`;
  } else {
    title = `Gana ${character.name}`;
    text = blocked ? `La partida se cerró y ${character.name} sumaba menos puntos.`
                   : `${character.name} se ha quedado sin fichas antes que tú.`;
    text += ` Se lleva ${state.score} puntos.`;
  }
  // a close-up of the character, with the face they're making right now
  const svg = face().cloneNode(true);
  svg.removeAttribute("id");
  svg.removeAttribute("hidden");
  svg.setAttribute("viewBox", svg.dataset.face);
  const portrait = document.createElement("div");
  portrait.className = "portrait";
  portrait.appendChild(svg);
  $("result-face").replaceChildren(portrait);

  $("result-title").textContent = title;
  $("result-text").textContent = text + (state.bot_hand.length ? ` A ${character.name} le quedaban:` : "");
  const botHand = $("result-bot");
  botHand.innerHTML = "";
  state.bot_hand.forEach((t) => botHand.appendChild(tileEl(t, { vertical: true })));
  // let the last tile land before the window opens
  setTimeout(() => { if (state.finished && !dialog.open) dialog.showModal(); }, 900);
}

// --- the back wall: a wine cellar ---
// A fixed seed, so the room looks the same every time the page opens
function seeded(seed) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function drawCellar() {
  const W = 1600, H = 640;
  const rand = seeded(11);
  const f = (n) => n.toFixed(1);
  const parts = [`<defs>
  </defs>`, `<rect width="${W}" height="${H}" fill="#24120c"/>`];

  // brick wall, each row offset by half a brick
  const BW = 64, BH = 26, BRICKS = ["#4a2a1e", "#45261b", "#512e20", "#3f2318"];
  for (let row = 0, y = 0; y < H; row++, y += BH) {
    for (let x = row % 2 ? -BW / 2 : 0; x < W; x += BW) {
      parts.push(`<rect x="${x + 2}" y="${y + 2}" width="${BW - 4}" height="${BH - 4}" rx="2" fill="${BRICKS[Math.floor(rand() * BRICKS.length)]}"/>`);
    }
  }

  // the arch behind the character, with a rack of bottles lying in the dark
  parts.push(`<path d="M600 640 L600 270 A200 200 0 0 1 1000 270 L1000 640 Z" fill="#140906"/>`);
  parts.push(`<path d="M600 640 L600 270 A200 200 0 0 1 1000 270 L1000 640" fill="none" stroke="#5e3624" stroke-width="22"/>`);
  for (let a = 0; a <= 180; a += 15) {          // the arch's bricks
    const r = (Math.PI * a) / 180;
    const x1 = 800 - Math.cos(r) * 189, y1 = 270 - Math.sin(r) * 189;
    const x2 = 800 - Math.cos(r) * 211, y2 = 270 - Math.sin(r) * 211;
    parts.push(`<line x1="${f(x1)}" y1="${f(y1)}" x2="${f(x2)}" y2="${f(y2)}" stroke="#24120c" stroke-width="3"/>`);
  }
  const CELL = 46, LYING = ["#14281d", "#2a0d14", "#1b2a14", "#240b10"];
  for (let r = 0; r < 7; r++) {
    for (let c = 0; c < 7; c++) {
      const x = 640 + c * CELL, y = 200 + r * CELL;
      if ((x - 800) ** 2 + (y + CELL / 2 - 270) ** 2 > 170 ** 2 && y < 270) continue;  // keep inside the arch
      parts.push(`<rect x="${x + 2}" y="${y + 2}" width="${CELL - 4}" height="${CELL - 4}" fill="#0c0504" stroke="#3b2414" stroke-width="3"/>`);
      if (rand() < 0.15) continue;
      parts.push(`<circle cx="${x + CELL / 2}" cy="${y + CELL / 2}" r="15" fill="${LYING[Math.floor(rand() * LYING.length)]}"/>`);
      parts.push(`<circle cx="${x + CELL / 2 - 5}" cy="${y + CELL / 2 - 5}" r="4" fill="#fff" opacity="0.1"/>`);
    }
  }

  // the collection: two lit cabinets of wine bottles standing on display
  const GLASS = ["#1f4a2c", "#35491a", "#4a2a12", "#1c1c1c", "#5a1426", "#2b5233", "#d79aa8", "#3d5c24"];
  const CAPSULE = ["#a0203d", "#d4ac34", "#222", "#6e1229", "#efe8d8", "#8e1b34"];
  const LABEL = ["#f3e6c4", "#fbf7ee", "#222", "#e0bf63", "#ecd9b3"];
  const bottle = (cx, floor, h, kind) => {
    const w = kind === "champagne" ? 32 : 27, nw = 10, left = cx - w / 2, right = cx + w / 2;
    const body = kind === "burgundy" ? floor - h * 0.45 : floor - h * 0.58;
    const neck = kind === "burgundy" ? floor - h * 0.74 : floor - h * 0.7;
    const top = floor - h;
    const glass = kind === "champagne" ? "#2e4a1e" : GLASS[Math.floor(rand() * GLASS.length)];
    const k1 = kind === "burgundy" ? floor - h * 0.62 : body - h * 0.06;
    // the bottle's outline: body, shoulders, neck
    parts.push(`<path d="M${f(left)} ${f(floor - 3)} Q${f(left)} ${floor} ${f(left + 3)} ${floor} L${f(right - 3)} ${floor} Q${f(right)} ${floor} ${f(right)} ${f(floor - 3)} L${f(right)} ${f(body)} C${f(right)} ${f(k1)} ${f(cx + nw / 2)} ${f(neck + h * 0.05)} ${f(cx + nw / 2)} ${f(neck)} L${f(cx + nw / 2)} ${f(top + 2)} L${f(cx + nw / 2 + 1)} ${f(top)} L${f(cx - nw / 2 - 1)} ${f(top)} L${f(cx - nw / 2)} ${f(top + 2)} L${f(cx - nw / 2)} ${f(neck)} C${f(cx - nw / 2)} ${f(neck + h * 0.05)} ${f(left)} ${f(k1)} ${f(left)} ${f(body)} Z" fill="${glass}" stroke="#000" stroke-opacity="0.35" stroke-width="1"/>`);
    // the light catching the glass
    parts.push(`<rect x="${f(left + 4)}" y="${f(body + 2)}" width="4" height="${f(floor - body - 8)}" rx="2" fill="#fff" opacity="0.28"/>`);
    parts.push(`<rect x="${f(cx - nw / 2 + 2)}" y="${f(top + h * 0.18)}" width="2" height="${f(neck - top - h * 0.2)}" fill="#fff" opacity="0.22"/>`);
    // capsule over the cork, and the label
    parts.push(`<rect x="${f(cx - nw / 2 - 1)}" y="${f(top)}" width="${nw + 2}" height="${f(h * 0.17)}" rx="2" fill="${CAPSULE[Math.floor(rand() * CAPSULE.length)]}"/>`);
    const label = LABEL[Math.floor(rand() * LABEL.length)];
    const ly = floor - h * 0.42, lh = h * 0.25;
    parts.push(`<rect x="${f(left + 2.5)}" y="${f(ly)}" width="${f(w - 5)}" height="${f(lh)}" rx="1.5" fill="${label}"/>`);
    const ink = label === "#222" ? "#e0bf63" : "#7a1a2e";
    parts.push(`<rect x="${f(left + 6)}" y="${f(ly + lh * 0.28)}" width="${f(w - 12)}" height="2.4" fill="${ink}"/>`);
    parts.push(`<rect x="${f(left + 8)}" y="${f(ly + lh * 0.55)}" width="${f(w - 16)}" height="1.6" fill="${ink}" opacity="0.7"/>`);
    parts.push(`<circle cx="${cx}" cy="${f(ly + lh * 0.82)}" r="2" fill="${ink}" opacity="0.7"/>`);
  };
  parts.push(`<linearGradient id="shelf-light" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffd59a" stop-opacity="0.55"/>
    <stop offset="1" stop-color="#ffd59a" stop-opacity="0"/>
  </linearGradient>`);
  const KINDS = ["bordeaux", "bordeaux", "burgundy", "champagne"];
  for (const left of [30, 1040]) {
    const width = 530, shelves = [140, 262, 384], top = 16, bottom = shelves.at(-1) + 14;
    parts.push(`<rect x="${left}" y="${top}" width="${width}" height="${bottom - top}" rx="6" fill="#3b2212"/>`);
    parts.push(`<rect x="${left + 12}" y="${top + 12}" width="${width - 24}" height="${bottom - top - 24}" fill="#24130a"/>`);
    let shelfTop = top + 12;
    for (const floor of shelves) {
      // a warm strip light under each shelf above, washing down over the bottles
      parts.push(`<rect x="${left + 12}" y="${shelfTop}" width="${width - 24}" height="${floor - shelfTop}" fill="url(#shelf-light)"/>`);
      parts.push(`<rect x="${left + 16}" y="${shelfTop}" width="${width - 32}" height="3" rx="1.5" fill="#ffe2b0" opacity="0.9"/>`);
      let x = left + 34;
      while (x < left + width - 36) {
        const kind = KINDS[Math.floor(rand() * KINDS.length)];
        const h = kind === "champagne" ? 98 : 102 + rand() * 6;
        bottle(x, floor, h, kind);
        x += (kind === "champagne" ? 38 : 33) + rand() * 3;
      }
      parts.push(`<rect x="${left + 6}" y="${floor}" width="${width - 12}" height="12" fill="#7a4a26"/>`);
      parts.push(`<rect x="${left + 6}" y="${floor}" width="${width - 12}" height="3" fill="#a06a3a"/>`);
      shelfTop = floor + 12;
    }
    // the frame between the two glass doors
    parts.push(`<rect x="${left + width / 2 - 4}" y="${top}" width="8" height="${bottom - top}" fill="#3b2212"/>`);
  }

  // barrels stacked at the foot of each cabinet
  let id = 0;
  const barrel = (cx, cy, r) => {
    const clip = `staves${id++}`;
    parts.push(`<clipPath id="${clip}"><circle cx="${cx}" cy="${cy}" r="${r}"/></clipPath>`);
    parts.push(`<circle cx="${cx}" cy="${cy}" r="${r}" fill="#7a4a28"/>`);
    for (let y = cy - r; y < cy + r; y += 16) {
      parts.push(`<line x1="${cx - r}" y1="${y}" x2="${cx + r}" y2="${y}" stroke="#5c3519" stroke-width="2" clip-path="url(#${clip})"/>`);
    }
    parts.push(`<circle cx="${cx}" cy="${cy}" r="${r - 4}" fill="none" stroke="#2b2522" stroke-width="7"/>`);
    parts.push(`<circle cx="${cx}" cy="${cy}" r="${r - 22}" fill="none" stroke="#2b2522" stroke-width="4" opacity="0.8"/>`);
    parts.push(`<circle cx="${cx}" cy="${cy + r * 0.45}" r="5" fill="#2a160b"/>`);
  };
  for (const [cx, cy] of [[130, 620], [290, 620], [450, 620], [210, 545], [370, 545]]) barrel(cx, cy, 70);
  for (const [cx, cy] of [[1470, 620], [1310, 620], [1150, 620], [1390, 545], [1230, 545]]) barrel(cx, cy, 70);

  $("cellar").innerHTML = parts.join("");
}

function confetti() {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const box = $("confetti");
  const colours = ["#ffbe0b", "#ff7b54", "#2ec4b6", "#fffaf0", "#8ecae6"];
  for (let i = 0; i < 70; i++) {
    const bit = document.createElement("i");
    bit.style.left = `${Math.random() * 100}%`;
    bit.style.background = colours[i % colours.length];
    bit.style.animationDuration = `${2 + Math.random() * 1.8}s`;
    bit.style.animationDelay = `${Math.random() * 0.6}s`;
    box.appendChild(bit);
  }
  setTimeout(() => box.replaceChildren(), 4500);
}

function render(next) {
  state = next;
  countResult();
  renderBoard();
  renderSidePick();
  renderBot();
  renderYourHand();
  renderStatus();
  renderLog();
  renderScore();
  if (!state.finished && $("result").open) $("result").close();
}

// --- buttons ---
$("new-game").addEventListener("submit", (e) => {
  e.preventDefault();
  newGame($("level").value);
});
$("draw-btn").onclick = () => yourMove(() => session.draw(), character.says.youDraw);
$("pile").onclick = () => yourMove(() => session.draw(), character.says.youDraw);
$("pass-btn").onclick = () => yourMove(() => session.pass_turn());
$("again-btn").onclick = () => newGame($("level").value);
// choosing a character starts a game against them
$("level").addEventListener("change", () => { if (session) newGame($("level").value); });
// the rules open as a sheet; tap outside it or "Entendido" to close
$("rules-btn").onclick = () => $("rules-sheet").showModal();
$("rules-close").onclick = () => $("rules-sheet").close();
$("rules-sheet").addEventListener("click", (e) => {
  const r = $("rules-sheet").getBoundingClientRect();
  const outside = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
  if (outside) $("rules-sheet").close();
});
window.addEventListener("resize", () => { if (state) renderBoard(); });

drawCellar();
renderScore();
loadEngine()
  .then((module) => {
    session = module;
    $("new-game").querySelector("button").disabled = false;
    newGame($("level").value);
  })
  .catch((err) => {
    const msg = document.createElement("p");
    msg.className = "board-msg";
    msg.textContent = `No se pudo cargar el juego: ${err.message || err.name || err}`;
    $("board").replaceChildren(msg);
  });
