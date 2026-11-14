const API_BASE = "https://steamcount.duckdns.org";

const qInput = document.getElementById("q");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const detailEl = document.getElementById("detail");

let searchSeq = 0;
let timer = null;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setStatus(msg) {
  statusEl.textContent = msg || "";
}

async function api(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) {
    throw new Error(res.status === 404 ? "Game not found" : "Server error (" + res.status + ")");
  }
  return res.json();
}

function describe(err) {
  return err instanceof TypeError ? "Can't reach the server. Is it running?" : err.message;
}

qInput.addEventListener("input", () => {
  clearTimeout(timer);
  const q = qInput.value.trim();
  showSearch();
  if (q.length < 2) {
    resultsEl.replaceChildren();
    setStatus("");
    return;
  }
  timer = setTimeout(() => doSearch(q), 300);
});

qInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const first = resultsEl.querySelector("button");
    if (first) first.click();
  }
});

async function doSearch(q) {
  const seq = ++searchSeq;
  setStatus("Searching...");
  try {
    const games = await api("/search?q=" + encodeURIComponent(q));
    if (seq !== searchSeq) return;
    renderResults(games);
    setStatus(games.length ? "" : "No games found");
  } catch (err) {
    if (seq !== searchSeq) return;
    resultsEl.replaceChildren();
    setStatus(describe(err));
  }
}

function renderResults(games) {
  const items = games.map((g) => {
    const li = el("li");
    const btn = el("button", "", g.name);
    btn.addEventListener("click", () => showGame(g.app_id));
    li.appendChild(btn);
    return li;
  });
  resultsEl.replaceChildren(...items);
}

function showSearch() {
  detailEl.hidden = true;
  resultsEl.hidden = false;
  qInput.hidden = false;
}

async function showGame(appId) {
  resultsEl.hidden = true;
  qInput.hidden = true;
  detailEl.hidden = false;
  detailEl.replaceChildren();
  setStatus("Loading...");
  try {
    const g = await api("/game/" + appId);
    setStatus("");
    renderGame(g);
  } catch (err) {
    setStatus("");
    detailEl.replaceChildren(backButton(), el("p", "note", describe(err)));
  }
}

function backButton() {
  const b = el("button", "back", "\u2190 Back to search");
  b.addEventListener("click", () => {
    showSearch();
    qInput.focus();
  });
  return b;
}

function changeCell(label, value) {
  const cell = el("div", "chg");
  cell.appendChild(el("span", "when", label));
  const val = el("span", "val");
  if (value === null || value === undefined) {
    val.textContent = "\u2013";
    val.classList.add("na");
  } else {
    val.textContent = (value > 0 ? "+" : "") + value.toFixed(1) + "%";
    val.classList.add(value > 0 ? "up" : value < 0 ? "down" : "flat");
  }
  cell.appendChild(val);
  return cell;
}

function agoText(iso) {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return mins + " min ago";
  return Math.round(mins / 60) + " h ago";
}

function renderGame(g) {
  const changes = el("div", "changes");
  changes.append(
    changeCell("vs 5 min ago", g.change_pct["5m"]),
    changeCell("vs 1 hour ago", g.change_pct["1h"]),
    changeCell("vs 1 day ago", g.change_pct["1d"])
  );
  const parts = [
    backButton(),
    el("p", "name", g.name),
    el("p", "players", g.current_players.toLocaleString()),
    el("p", "label", "playing now \u00b7 updated " + agoText(g.as_of)),
    changes,
  ];
  if (g.note) parts.push(el("p", "note", g.note));
  detailEl.replaceChildren(...parts);
}