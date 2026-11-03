// The sections around the game: home, the tournament, the ranking and the information page.
// app.js plays the game itself; this file loads the engine, moves between the sections (by the
// # in the address, so each one has its own link) and fills them. The bots come from the
// registry (session.list_bots), so every bot in domino/bots/ shows up here by itself.

const VIEWS = { "#jugar": "play", "#torneo": "tournament", "#ranking": "ranking", "#info": "info" };
let botProblems = [];   // bot files that didn't load, as the registry describes them
let started = false;    // the first game starts the first time you open "Jugar"
let ranking = null;     // the published ranking, once loaded
let touring = false;    // a tournament is being played

// Build an element: el("p", { className: "x" }, "some text", otherElement)
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  node.append(...children.filter((child) => child !== null && child !== undefined));
  return node;
}

const percent = (rate) => `${(rate * 100).toFixed(1).replace(".", ",")} %`;
const authorsText = (bot) => bot.authors.join(", ");

// --- moving between the sections ---
function showView() {
  const view = VIEWS[location.hash] || "home";
  for (const node of document.querySelectorAll("[data-view]")) node.hidden = node.dataset.view !== view;
  for (const node of document.querySelectorAll("[data-only]")) node.hidden = node.dataset.only !== view;
  for (const link of document.querySelectorAll(".nav a")) {
    if (VIEWS[link.getAttribute("href")] === view) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  if (view === "play") {
    startFirstGame();
    if (state) renderBoard();   // the board is laid out to its width, which is 0 while hidden
  }
  if (view === "ranking") loadRanking();
  window.scrollTo(0, 0);
}

function startFirstGame() {
  if (!session || started || !bots.length) return;
  started = true;
  newGame($("level").value);
}

// "Jugar contra este bot" on the information page
function playAgainst(id) {
  $("level").value = id;
  rememberRival();
  started = true;
  newGame(id);
  location.hash = "#jugar";
}

// --- who you can play against ---
function rememberRival() {
  try { localStorage.setItem("domino-rival", $("level").value); } catch (e) { /* fine */ }
}

function fillBotMenu() {
  const ours = el("optgroup", { label: "Personajes" });
  const others = el("optgroup", { label: "Bots de la comunidad" });
  for (const bot of bots) {
    const own = CHARACTERS[bot.character];
    (own ? ours : others).append(el("option", { value: bot.id, textContent: own ? `${own.name} · ${own.level}` : bot.name }));
  }
  $("level").replaceChildren(...[ours, others].filter((group) => group.children.length));
  let saved = null;
  try { saved = localStorage.getItem("domino-rival"); } catch (e) { /* fine */ }
  const paco = bots.find((bot) => bot.character === "hard") || bots[0];
  $("level").value = bots.some((bot) => bot.id === saved) ? saved : paco.id;
}
$("level").addEventListener("change", rememberRival);

function renderHome() {
  const community = bots.filter((bot) => !bot.character).length;
  $("home-count").textContent = `${bots.length} bots listos para jugar`
    + (community ? ` · ${community} de la comunidad` : "");
}

// --- information: the rules and every bot ---
function copyRules() {
  const sections = [...document.querySelectorAll("#rules-sheet section")].map((section) => section.cloneNode(true));
  $("rules-inline").replaceChildren(...sections);
}

function problemsList(title) {
  if (!botProblems.length) return null;
  return el("div", { className: "problems" },
    el("h4", { textContent: title }),
    el("ul", {}, ...botProblems.map((problem) => el("li", { textContent: problem }))));
}

function renderBotCards() {
  $("bot-cards").replaceChildren(...bots.map((bot) => {
    const own = CHARACTERS[bot.character];
    return el("article", { className: "bot-card" + (own ? "" : " guest") },
      el("div", { className: "bot-card-head" },
        el("h4", { className: "bot-card-name", textContent: bot.name }),
        el("span", { className: "tag", textContent: own ? `${own.name} · ${own.level}` : "Comunidad" })),
      el("p", { className: "bot-card-authors", textContent: `por ${authorsText(bot)}` }),
      el("p", { className: "bot-card-text", textContent: bot.description }),
      el("button", { type: "button", className: "btn btn-play btn-small", textContent: "Jugar contra este bot",
                     onclick: () => playAgainst(bot.id) }));
  }));
  $("bot-problems").replaceChildren(...[problemsList("No se han podido cargar")].filter(Boolean));
}

// --- a table of standings, for the ranking and the tournament ---
function standingsTable(rows, { champion = false } = {}) {
  const faults = rows.some((row) => row.faults);
  const columns = [["#", ""], ["Bot", ""], ["PJ", "Partidas jugadas"], ["G", "Ganadas"], ["E", "Empatadas"],
                   ["P", "Perdidas"], ["Puntos", "Puntos ganados"], ["% victorias", "Partidas ganadas"]];
  if (faults) columns.push(["Faltas", "Partidas perdidas por romper las reglas"]);
  const number = (value) => el("td", { textContent: value });
  return el("table", { className: "standings" + (champion ? " finished" : "") },
    el("thead", {}, el("tr", {}, ...columns.map(([label, title]) => el("th", { scope: "col", textContent: label, title })))),
    el("tbody", {}, ...rows.map((row) => {
      const bar = el("i");
      bar.style.width = `${row.win_rate * 100}%`;
      return el("tr", { className: row.played && row.rank <= 3 ? `podium-${row.rank}` : "" },
        el("td", { className: "rank" }, el("span", { className: "rank-badge", textContent: row.rank })),
        el("td", { className: "who" },
          el("span", { className: "who-name", textContent: row.name }),
          el("span", { className: "who-authors", textContent: authorsText(row) })),
        number(row.played), number(row.wins), number(row.ties), number(row.losses), number(row.points),
        el("td", { className: "rate" }, el("span", { className: "rate-bar" }, bar),
           el("span", { className: "rate-num", textContent: percent(row.win_rate) })),
        ...(faults ? [number(row.faults)] : []));
    })));
}

// How each bot (rows) did against each other bot (columns)
function headToHeadTable(rows, record) {
  const names = rows.map((row) => row.name);
  return el("table", { className: "h2h" },
    el("thead", {}, el("tr", {}, el("th", {}), ...names.map((name) => el("th", { scope: "col", textContent: name })))),
    el("tbody", {}, ...names.map((a) => el("tr", {},
      el("th", { scope: "row", textContent: a }),
      ...names.map((b) => {
        if (a === b) return el("td", { className: "self", textContent: "—" });
        const { wins, played } = record[a][b];
        const rate = played ? wins / played : 0.5;
        return el("td", { className: rate > 0.55 ? "good" : rate < 0.45 ? "bad" : "even",
                          textContent: played ? percent(rate) : "—", title: `${a} gana ${wins} de ${played} a ${b}` });
      })))));
}

// --- the ranking, published by GitHub with the site (tools/tournament.py) ---
async function loadRanking() {
  if (ranking) return;
  try {
    const res = await fetch("ranking.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(res.status);
    ranking = await res.json();
    renderRanking();
  } catch (e) {
    $("ranking-body").replaceChildren(
      el("h3", { className: "panel-title", textContent: "Todavía no hay ranking publicado" }),
      el("p", { className: "page-text", textContent: "GitHub lo calcula y lo publica con la web cada vez que cambia la rama main. Para verlo en tu ordenador, desde la carpeta del proyecto:" }),
      el("pre", { className: "code", textContent: "python -m tools.tournament --out web/ranking.json" }));
  }
}

function renderRanking() {
  const when = new Date(ranking.generated).toLocaleString("es-ES", { dateStyle: "long", timeStyle: "short" });
  const parts = [
    el("p", { className: "muted ranking-meta",
              textContent: `Actualizado el ${when}${ranking.commit ? ` (versión ${ranking.commit})` : ""} · `
                + `${ranking.games_per_pair} partidas por pareja · máximo ${ranking.time_limit} s por jugada` }),
    el("div", { className: "table-wrap" }, standingsTable(ranking.bots)),
  ];
  if (ranking.bots.length > 1) {
    parts.push(el("h3", { className: "panel-title sub", textContent: "Cara a cara" }),
               el("p", { className: "muted", textContent: "Partidas que gana el bot de cada fila contra el de cada columna." }),
               el("div", { className: "table-wrap" }, headToHeadTable(ranking.bots, ranking.head_to_head)));
  }
  const unranked = bots.filter((bot) => !ranking.bots.some((row) => row.name === bot.id));
  if (unranked.length) {
    parts.push(el("p", { className: "hint", textContent: `Aún sin clasificar: ${unranked.map((bot) => bot.name).join(", ")}. `
      + "Entrarán la próxima vez que se publique el ranking." }));
  }
  if (ranking.problems.length) {
    parts.push(el("div", { className: "problems" }, el("h4", { textContent: "Se quedaron fuera" }),
                  el("ul", {}, ...ranking.problems.map((problem) => el("li", { textContent: problem })))));
  }
  $("ranking-body").replaceChildren(...parts);
}

// --- a tournament, played here one game at a time (web/session.py) ---
function renderTournamentPicker() {
  $("t-bots").replaceChildren(...bots.map((bot) => el("label", { className: "pick" },
    el("input", { type: "checkbox", value: bot.id, checked: true }),
    el("span", { className: "pick-name", textContent: bot.name }),
    el("span", { className: "pick-authors", textContent: authorsText(bot) }))));
  $("t-start").disabled = bots.length < 2;
}

function lastGameText(game) {
  const [a, b] = game.seats;
  if (game.winner === null) return `Última partida: ${a} y ${b} empatan.`;
  const loser = game.winner === a ? b : a;
  if (game.fault) return `Última partida: ${loser} pierde contra ${game.winner} por ${FAULT_NAME[game.fault]}.`;
  return `Última partida: ${game.winner} gana a ${loser}${game.end_reason === "blocked" ? " (cerrada)" : ""} `
    + `y se lleva ${game.score} puntos.`;
}

function renderTournament(data) {
  $("t-live").hidden = false;
  $("t-live").classList.toggle("done", data.finished);
  $("t-status").textContent = data.finished ? `Campeón: ${data.table[0].name}` : touring ? "Jugando…" : "Torneo parado";
  $("t-count").textContent = `Partida ${data.played} de ${data.total}`;
  $("t-bar").style.width = `${(100 * data.played) / data.total}%`;
  $("t-last").textContent = data.last ? lastGameText(data.last) : "Empieza la primera partida…";
  $("t-table").replaceChildren(standingsTable(data.table, { champion: data.finished }));
}

function setTouring(on) {
  touring = on;
  $("t-start").hidden = on;
  $("t-stop").hidden = !on;
  for (const input of document.querySelectorAll("#t-bots input, #t-games")) input.disabled = on;
}

function tournamentHint(text, error = false) {
  $("t-hint").textContent = text;
  $("t-hint").className = "hint" + (error ? " error" : "");
}

async function runTournament() {
  const names = [...document.querySelectorAll("#t-bots input:checked")].map((box) => box.value);
  if (names.length < 2) return tournamentHint("Elige al menos dos bots.", true);
  tournamentHint("Puedes pararlo cuando quieras: la tabla se queda como esté.");
  const seed = Math.floor(Math.random() * 1000000);
  let data = JSON.parse(session.tournament_start(JSON.stringify(names), Number($("t-games").value), seed));
  if (data.error) return tournamentHint(data.error, true);
  setTouring(true);
  renderTournament(data);
  try {
    while (touring && !data.finished) {
      await new Promise((resolve) => setTimeout(resolve, 30));   // let the page draw between games
      data = JSON.parse(session.tournament_step());
      renderTournament(data);
    }
  } catch (err) {
    tournamentHint(`El torneo se ha parado por un error: ${err.message || err}`, true);
  }
  setTouring(false);
  renderTournament(data);
  $("t-start").textContent = "Otro torneo";
}
$("t-start").onclick = runTournament;
$("t-stop").onclick = () => { touring = false; };

// --- starting the page ---
drawCellar();
renderScore();
copyRules();
showView();
window.addEventListener("hashchange", showView);
loadEngine()
  .then((module) => {
    session = module;
    ({ bots, problems: botProblems } = JSON.parse(session.list_bots()));
    if (!bots.length) throw new Error("no hay ningún bot que funcione");
    fillBotMenu();
    renderHome();
    renderBotCards();
    renderTournamentPicker();
    if (ranking) renderRanking();
    $("new-game").querySelector("button").disabled = false;
    if (VIEWS[location.hash] === "play") startFirstGame();
  })
  .catch((err) => {
    const text = `No se pudo cargar el juego: ${err.message || err.name || err}`;
    $("board").replaceChildren(el("p", { className: "board-msg", textContent: text }));
    $("home-count").textContent = text;
    for (const id of ["bot-cards", "t-bots"]) $(id).replaceChildren(el("p", { className: "hint error", textContent: text }));
  });
