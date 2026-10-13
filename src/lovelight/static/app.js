"use strict";

const MOCK = new URLSearchParams(location.search).has("mock");
const $ = (sel, root = document) => root.querySelector(sel);

const ACCOUNTS = {
  "1220": "Inventarier", "1510": "Kundfordringar", "1930": "Företagskonto", "2081": "Aktiekapital", "2091": "Balanserad vinst",
  "2099": "Årets resultat", "2440": "Leverantörsskulder", "2611": "Utgående moms 25 %", "2640": "Ingående moms",
  "3001": "Försäljning tjänster 25 %", "4010": "Inköp material", "5010": "Lokalhyra", "5410": "Förbrukningsinventarier",
  "5420": "Programvaror", "5460": "Förbrukningsmaterial", "5800": "Resekostnader", "5810": "Biljetter",
  "6071": "Representation", "6110": "Kontorsmateriel", "6212": "Mobiltelefon", "6540": "IT-tjänster", "6570": "Bankkostnader",
  "3740": "Öres- och kronutjämning", "3960": "Valutakursvinster", "5060": "Städning och renhållning", "6550": "Konsultarvoden", "7960": "Valutakursförluster",
};
if (window.LovelightMock) window.LovelightMock.ACCOUNTS = ACCOUNTS;

// ---------- icons ----------
const I = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const ICON = {
  grid: I('<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
  inbox: I('<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'),
  link: I('<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'),
  book: I('<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15z"/><path d="M8 7h8M8 11h6"/>'),
  shield: I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'),
  shieldX: I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9.5 9.5 5 5M14.5 9.5l-5 5"/>'),
  shieldCheck: I('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>'),
  mail: I('<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>'),
  upload: I('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5M12 3v12"/>'),
  table: I('<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18"/>'),
  check: I('<path d="M20 6 9 17l-5-5"/>'),
  alert: I('<path d="m10.29 3.86-8.47 14.14A2 2 0 0 0 3.54 21h16.92a2 2 0 0 0 1.72-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4M12 17h.01"/>'),
  info: I('<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>'),
  play: I('<path d="m6 3 14 9-14 9V3z"/>'),
  reset: I('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>'),
  download: I('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5M12 15V3"/>'),
  eye: I('<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'),
  x: I('<path d="M18 6 6 18M6 6l12 12"/>'),
  sparkle: I('<path d="M12 3l1.9 5.8L20 10.7l-6.1 1.9L12 18.4l-1.9-5.8L4 10.7l6.1-1.9z"/>'),
  lock: I('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'),
  cpu: I('<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>'),
  csv: I('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8"/>'),
  bank: I('<path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v3M12 14v3M16 14v3"/>'),
};

// ---------- formatting ----------
const nf = new Intl.NumberFormat("sv-SE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const kr = (x) => (x === null || x === undefined || x === "" ? "—" : nf.format(+x).replace(/−/g, "−") + " kr");
const krShort = (x) => new Intl.NumberFormat("sv-SE", { maximumFractionDigits: 0 }).format(+x) + " kr";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (c) => Math.round(+c * 100) + "%";
const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString("sv-SE", { dateStyle: "short", timeStyle: "short" }) : "—");
const confTone = (c) => (c >= 0.95 ? "green" : c >= 0.8 ? "amber" : "red");
const confColor = (c) => ({ green: "var(--green)", amber: "var(--amber)", red: "var(--red)" }[confTone(c)]);

// ---------- api ----------
const api = MOCK
  ? {
      state: async () => window.LovelightMock.getState(),
      replay: async () => window.LovelightMock.replay(),
      reset: async () => window.LovelightMock.reset(),
      upload: async (files) => window.LovelightMock.upload(files),
      approve: async (id) => window.LovelightMock.approve(id),
      approveAll: async () => window.LovelightMock.approveAll(),
      sie4: async () => window.LovelightMock.sie4(),
      fileUrl: () => null,
    }
  : {
      state: async () => (await ok(fetch("/api/state"))).json(),
      replay: () => ok(fetch("/api/demo/replay", { method: "POST" })),
      reset: () => ok(fetch("/api/demo/reset", { method: "POST" })),
      upload: (files) => {
        const fd = new FormData();
        Array.from(files).forEach((f) => fd.append("files", f));
        return ok(fetch("/api/upload", { method: "POST", body: fd }));
      },
      approve: (id) => ok(fetch(`/api/matches/${encodeURIComponent(id)}/approve`, { method: "POST" })),
      approveAll: () => ok(fetch("/api/matches/approve-all", { method: "POST" })),
      sie4: async () => decodePc8(await (await ok(fetch("/api/export/sie4"))).arrayBuffer()),
      fileUrl: (doc) => `/api/documents/${encodeURIComponent(doc.id)}/file`,
    };
// SIE4 is PC8 (cp437); browsers have no cp437 TextDecoder, so map the Nordic code points by hand.
const CP437_HIGH = { 0x81: "ü", 0x82: "é", 0x84: "ä", 0x86: "å", 0x8e: "Ä", 0x8f: "Å", 0x90: "É", 0x94: "ö", 0x99: "Ö", 0x9a: "Ü" };
const decodePc8 = (buf) => Array.from(new Uint8Array(buf), (b) => (b < 0x80 ? String.fromCharCode(b) : CP437_HIGH[b] || "?")).join("");
async function ok(p) {
  const r = await p;
  if (!r.ok) {
    toast("red", "Request failed", `${r.status} ${r.statusText}`);
    throw new Error(`HTTP ${r.status}`);
  }
  return r;
}

// ---------- state ----------
let S = null;
const QS = new URLSearchParams(location.search);
let view = QS.get("view") || "inbox";
if (QS.has("static")) document.documentElement.classList.add("static");
let filter = "all";
let drawerDoc = null;
let menuOpen = false;
const seen = new Set();
const shownStats = { docs: 0, pct: 0, hours: 0 };

const docById = (id) => S.documents.find((d) => d.id === id);
const bankById = (id) => S.bank.find((b) => b.id === id);

async function refresh() {
  S = await api.state();
  render();
}
let debounce = null;
function scheduleRefresh() {
  clearTimeout(debounce);
  debounce = setTimeout(refresh, MOCK ? 30 : 200);
}

function onEvent(ev) {
  const p = ev.payload || {};
  if (ev.type === "anomaly.found") toast(p.severity === "high" ? "red" : "amber", p.title || "Anomaly found", p.rule ? `Deterministic rule: ${p.rule}` : p.explanation || "");
  if (ev.type === "doc.quarantined") toast("red", "Document quarantined", `${p.filename || "Document"} — prompt injection blocked`, ICON.shieldX);
  if (ev.type === "state.reset") seen.clear();
  if (ev.type === "doc.received" && view !== "inbox" && view !== "bureau") { /* stay put; live counters update */ }
  scheduleRefresh();
}

// ---------- render ----------
const NAV = [
  ["bureau", "Bureau overview", ICON.grid],
  ["inbox", "Live Inbox", ICON.inbox],
  ["recon", "Reconciliation", ICON.link],
  ["books", "Books", ICON.book],
  ["trust", "Trust Center", ICON.shield],
];

function render() {
  if (!S) return;
  renderNav();
  renderTop();
  const v = $("#view");
  const fresh = v.dataset.view !== view;
  v.dataset.view = view;
  if (view === "inbox") renderInbox(v, fresh);
  else {
    v.innerHTML = { bureau: viewBureau, recon: viewRecon, books: viewBooks, trust: viewTrust }[view]();
    v.classList.toggle("fresh", fresh);
  }
  if (drawerDoc) renderDrawer();
}

function go(v) {
  view = v;
  $("#view").scrollTop = 0;
  render();
}

function renderNav() {
  const open = S.matches.filter((m) => !m.approved).length;
  const high = S.anomalies.filter((a) => a.severity === "high").length;
  const review = S.documents.filter((d) => d.source !== "light_csv" && (d.status === "needs_review" || d.status === "quarantined")).length;
  const badge = { inbox: review ? `<span class="badge amber">${review}</span>` : "", recon: open ? `<span class="badge amber">${open}</span>` : "", trust: high ? `<span class="badge">${high}</span>` : "" };
  $("#nav").innerHTML =
    `<div class="nav-section">Bureau</div>` +
    NAV.map(([k, label, ic], i) => (i === 1 ? `<div class="nav-section">${esc(S.client.name)}</div>` : "") +
      `<button class="nav-item ${view === k ? "active" : ""}" data-go="${k}">${ic}<span>${label}</span>${badge[k] || ""}</button>`).join("");
}

function renderTop() {
  const cs = $("#clientSwitch");
  const name = view === "bureau" ? "Nordic Redovisning AB" : S.client.name;
  const sub = view === "bureau" ? `${CLIENTS.length} clients · Bureau` : `Org.nr ${S.client.org_nr}`;
  cs.innerHTML = `<button class="client-btn" data-act="menu"><span class="avatar">${initials(name)}</span><span class="meta">${esc(name)}<small>${esc(sub)}</small></span><span class="muted">▾</span></button>` +
    (menuOpen ? `<div class="client-menu"><button data-go="bureau"><span class="avatar" style="background:#2a2d3a">${ICON.grid.replace("<svg", '<svg width="14" height="14"')}</span>All clients</button>${CLIENTS.map((c) =>
      `<button data-client="${esc(c.name)}"><span class="avatar" style="${c.live ? "" : "background:#262938;color:#aab"}">${initials(c.name)}</span><span style="flex:1">${esc(c.name)}</span>${c.live ? '<span class="pill green">LIVE</span>' : ""}</button>`).join("")}</div>` : "");
  const st = S.stats || {};
  const hours = (st.minutes_saved || 0) / 60;
  const el = $("#stats");
  if (!el.children.length) {
    el.innerHTML = `<div class="stat"><div class="v" id="stDocs">0</div><div class="k">Docs processed</div></div>
      <div class="stat"><div class="v" id="stPct">0%</div><div class="k">Auto-posted</div></div>
      <div class="stat hl"><div class="v" id="stHours">0,0 h</div><div class="k">Hours saved</div></div>`;
  }
  tween("docs", st.docs_total || 0, (x) => ($("#stDocs").textContent = Math.round(x)));
  tween("pct", st.auto_posted_pct || 0, (x) => ($("#stPct").textContent = Math.round(x) + "%"));
  tween("hours", hours, (x) => ($("#stHours").textContent = x.toLocaleString("sv-SE", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " h"));
}
const initials = (n) => n.replace(/\b(AB|HB|Brf)\b/g, "").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

const tweens = {};
function tween(key, to, draw) {
  const from = shownStats[key];
  cancelAnimationFrame(tweens[key]);
  const t0 = performance.now(), dur = QS.has("static") ? 1 : 900;
  const step = (t) => {
    const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
    shownStats[key] = from + (to - from) * e;
    draw(shownStats[key]);
    if (k < 1) tweens[key] = requestAnimationFrame(step);
  };
  tweens[key] = requestAnimationFrame(step);
}

// ---------- 0. bureau ----------
const CLIENTS = [
  "Lovelight Design AB", "Nordljus Bygg AB", "Fjällräv Konsult AB", "Söderberg & Lind Advokatbyrå AB", "Kafé Kanelbullen HB",
  "Göta Elteknik AB", "Brf Solgläntan", "Västkust Marin AB", "Stjärnfall Media AB", "Ekholm Tandvård AB",
  "Malmö Cykelverkstad AB", "Hälsingegård Livs AB", "Norrsken Fastigheter AB", "Blåbär Digital AB", "Uppsala Rör & Värme AB",
  "Studio Linnea AB", "Granit Logistik AB", "Vinterviken Event AB", "Kvarnby Bageri AB", "Tre Kronor Städ AB",
].map((name, i) => ({
  name, live: i === 0,
  org: `55${(9012345 + i * 731).toString().slice(0, 4)}-${(1000 + i * 377) % 9000 + 1000}`,
  pending: [0, 7, 3, 12, 22, 4, 1, 9, 15, 2, 6, 31, 0, 5, 11, 8, 3, 18, 14, 2][i],
  auto: [0, 94, 97, 88, 76, 91, 99, 85, 92, 96, 89, 71, 98, 95, 83, 93, 90, 79, 87, 97][i],
  flags: [0, 0, 1, 0, 2, 0, 0, 1, 0, 0, 0, 3, 0, 0, 1, 0, 0, 2, 0, 0][i],
}));

function viewBureau() {
  const st = S.stats || {};
  const pending = S.documents.filter((d) => d.status !== "posted").length;
  const flags = S.anomalies.filter((a) => a.severity !== "low").length;
  const card = (c) => {
    const p = c.live ? pending : c.pending, a = c.live ? Math.round(st.auto_posted_pct || 0) : c.auto, f = c.live ? flags : c.flags;
    return `<div class="card client ${c.live ? "live-client" : ""}" ${c.live ? 'data-go="inbox"' : `data-client="${esc(c.name)}"`}>
      ${c.live ? '<span class="pill green live-tag"><span class="pulse" style="width:6px;height:6px"></span>LIVE</span>' : ""}
      <div class="row"><span class="avatar" style="${c.live ? "" : "background:#262938;color:#aab"}">${initials(c.name)}</span>
        <div style="min-width:0"><div class="name">${esc(c.name)}</div><div class="org">${c.live ? esc(S.client.org_nr) : c.org}</div></div></div>
      <div class="kpis"><div><b>${p}</b>pending</div><div><b>${a}%</b>auto-posted</div>
        <div><b style="color:${f ? "var(--red)" : "var(--text)"}">${f}</b>flags</div></div>
      <div class="bar"><i style="width:${a}%"></i></div></div>`;
  };
  const totalDocs = CLIENTS.reduce((s, c) => s + (c.live ? 0 : c.pending * 9 + 40), st.docs_total || 0);
  return `<div class="view-head"><div><h1>Good morning, Anna</h1><div class="sub">${CLIENTS.length} clients · ${totalDocs.toLocaleString("sv-SE")} documents this month · ${CLIENTS.reduce((s, c) => s + c.flags, flags)} need your judgement</div></div>
    <div class="btn-row"><button class="btn primary" data-go="inbox">${ICON.sparkle}Open live client</button></div></div>
    <div class="clients">${CLIENTS.map(card).join("")}</div>`;
}

// ---------- 1. inbox ----------
const STEP_NAMES = ["Received", "Extracted", "Matched", "Posted"];
const STEP_IDX = { received: 0, extracted: 1, matched: 2, posted: 3, needs_review: 1, quarantined: 0 };
const toneOf = (d) => (d.status === "quarantined" ? "red" : d.status === "needs_review" ? "amber" : d.status === "posted" ? "green" : "");

function renderInbox(v, fresh) {
  if (fresh || !$("#docs", v)) {
    v.innerHTML = `<div class="view-head"><div><h1>Live Inbox</h1><div class="sub">Email, uploads and Light exports land here. Claude extracts, deterministic code posts.</div></div>
      <div class="btn-row"><button class="btn primary" data-act="replay">${ICON.play}Replay demo batch</button><button class="btn ghost" data-act="reset">${ICON.reset}Reset</button></div></div>
      <div class="hero" id="hero"></div>
      <label class="dropzone" id="dropzone"><input type="file" id="fileInput" multiple hidden>
        <div class="icon">${ICON.upload}</div><div class="big">Drop the shoebox — 1 or 1000 files</div>
        <div class="hint">PDF, JPG, PNG, CSV · or forward to <span class="mono">inbox+lovelight@bureau.se</span></div>
        <div class="pipeline-legend"><span>① Claude extracts (no tools)</span><span>② Schema validated</span><span>③ Code posts &amp; balances</span><span>④ You approve</span></div></label>
      <div class="inbox-toolbar"><div class="filters" id="filters"></div><div class="muted" id="docCount"></div></div>
      <div class="docs" id="docs"></div><div id="docsEmpty"></div>`;
    v.classList.toggle("fresh", fresh);
    wireDropzone();
  }
  const inboxDocs = S.documents.filter((d) => d.source !== "light_csv");
  const st = S.stats || {};
  const hrs = ((st.minutes_saved || 0) / 60).toLocaleString("sv-SE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const th = threats();
  $("#hero").innerHTML = `<div class="kpi"><div class="v">${st.docs_total || 0}</div><div class="k">Documents processed</div></div>
    <div class="kpi green"><div class="v">${Math.round(st.auto_posted_pct || 0)}%</div><div class="k">Auto-posted, balanced</div></div>
    <div class="kpi grad"><div class="v">${hrs} h</div><div class="k">Accountant hours saved</div></div>
    <div class="kpi ${th.length ? "red" : ""}" data-go="trust" style="cursor:pointer"><div class="v">${th.length}</div><div class="k">Threats caught</div></div>`;
  const lightDocs = S.documents.filter((d) => d.source === "light_csv");
  const counts = { all: inboxDocs.length, review: 0, quarantined: 0, posted: 0, light: lightDocs.length };
  inboxDocs.forEach((d) => {
    if (d.status === "needs_review") counts.review++;
    if (d.status === "quarantined") counts.quarantined++;
    if (d.status === "posted") counts.posted++;
  });
  $("#filters").innerHTML = [["all", "All"], ["posted", "Posted"], ["review", "Needs review"], ["quarantined", "Quarantined"], ...(counts.light ? [["light", "Light AR"]] : [])]
    .map(([k, l]) => `<button class="btn sm ${filter === k ? "" : "ghost"}" data-filter="${k}">${l} <span class="muted">${counts[k]}</span></button>`).join("");
  $("#docCount").textContent = `${counts.posted}/${counts.all} posted${counts.light ? ` · ${counts.light} Light AR invoices in Books` : ""}`;

  const grid = $("#docs");
  const visible = (filter === "light" ? lightDocs : inboxDocs.filter((d) => filter === "all" || (filter === "review" ? d.status === "needs_review" : d.status === filter))).slice().reverse();
  const keep = new Set(visible.map((d) => d.id));
  [...grid.children].forEach((el) => { if (!keep.has(el.dataset.id)) el.remove(); });
  let prev = null;
  visible.forEach((d) => {
    let el = grid.querySelector(`[data-id="${CSS.escape(d.id)}"]`);
    if (!el) {
      el = document.createElement("div");
      el.className = "card doc" + (seen.has(d.id) || fresh ? "" : " enter");
      el.dataset.id = d.id;
      el.innerHTML = `<div class="top"><div class="src"></div><div class="info"><div class="vendor"></div><div class="fn"></div></div><div class="gross"></div></div>
        <div class="steps">${STEP_NAMES.map((n) => `<div class="step"><i></i>${n}</div>`).join("")}</div><div class="status-line"></div>`;
      seen.add(d.id);
    }
    updateDocCard(el, d);
    if (prev ? prev.nextSibling !== el : grid.firstChild !== el) grid.insertBefore(el, prev ? prev.nextSibling : grid.firstChild);
    prev = el;
  });
  $("#docsEmpty").innerHTML = visible.length ? "" : `<div class="empty">No documents yet. Drop files above or hit <b>Replay demo batch</b>.</div>`;
}

function updateDocCard(el, d) {
  const e = d.extraction;
  const tone = toneOf(d);
  if (el.dataset.status && el.dataset.status !== d.status) { el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); }
  el.dataset.status = d.status;
  el.dataset.tone = tone;
  $(".src", el).innerHTML = d.status === "quarantined" ? ICON.shieldX : d.source === "email" ? ICON.mail : d.source === "light_csv" ? ICON.csv : ICON.upload;
  $(".vendor", el).innerHTML = e ? esc(e.vendor) : `<span class="shimmer"></span>`;
  $(".fn", el).innerHTML = esc(d.filename) + (d.source === "email" ? `<br><span class="via">${ICON.mail}via email${d.sender ? " · " + esc(d.sender) : ""}</span>` : "");
  $(".gross", el).innerHTML = e ? `${money(e.gross, e.currency)}<small>${esc(e.date)}</small>` : "";
  const idx = STEP_IDX[d.status] ?? 0;
  const live = !["posted", "needs_review", "quarantined"].includes(d.status);
  el.querySelectorAll(".step").forEach((s, i) => { s.classList.toggle("done", i <= idx); s.classList.toggle("cur", live && i === idx + 1); });
  const line = {
    received: `<span class="muted">Claude is reading…</span>`,
    extracted: e ? `<span class="pill ${confTone(e.confidence)}">${pct(e.confidence)} confidence</span><span class="acct">${esc(e.suggested_account)}</span> <span>${esc(ACCOUNTS[e.suggested_account] || "")}</span>` : "",
    matched: `<span class="pill violet">${ICON.link}Bank match found</span><span>awaiting approval</span>`,
    posted: `<span class="pill green">${ICON.check}Posted</span>${e ? `<span class="acct">${esc(e.suggested_account)}</span> <span>${esc(ACCOUNTS[e.suggested_account] || "")}</span>` : ""}`,
    needs_review: `<span class="pill amber">${ICON.alert}Needs review</span><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(d.note || "")}</span>`,
    quarantined: `<span class="pill red">${ICON.shieldX}Quarantined</span><span>prompt injection blocked</span>`,
  }[d.status] || "";
  $(".status-line", el).innerHTML = line;
}

function wireDropzone() {
  const dz = $("#dropzone"), input = $("#fileInput");
  ["dragenter", "dragover"].forEach((t) => dz.addEventListener(t, (e) => { e.preventDefault(); dz.classList.add("over"); }));
  ["dragleave", "drop"].forEach((t) => dz.addEventListener(t, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
  dz.addEventListener("drop", (e) => uploadFiles(e.dataTransfer.files));
  input.addEventListener("change", () => { uploadFiles(input.files); input.value = ""; });
}
async function uploadFiles(files) {
  if (!files || !files.length) return;
  toast("green", `Uploading ${files.length} file${files.length > 1 ? "s" : ""}`, "Hashing, extracting, posting…", ICON.upload);
  await api.upload(files);
  scheduleRefresh();
}

// ---------- drawer ----------
function openDrawer(id) {
  drawerDoc = id;
  renderDrawer();
  $("#drawer").classList.add("on");
  $("#scrim").classList.add("on");
}
function closeDrawer() {
  drawerDoc = null;
  $("#drawer").classList.remove("on");
  $("#scrim").classList.remove("on");
}

function renderDrawer() {
  const d = docById(drawerDoc);
  if (!d) return closeDrawer();
  const e = d.extraction;
  const v = S.vouchers.find((x) => x.document_id === d.id);
  const anoms = S.anomalies.filter((a) => a.document_id === d.id);
  const url = d.source === "light_csv" ? null : api.fileUrl(d);
  const isImg = /\.(png|jpe?g|gif|webp)$/i.test(d.filename);
  const preview = url
    ? isImg ? `<img class="preview" src="${url}" alt="${esc(d.filename)}">` : `<iframe class="preview" src="${url}" title="${esc(d.filename)}"></iframe>`
    : paper(d);
  const conf = e ? e.confidence : 0;
  const F = (k, val, c = conf) => `<div class="field"><div class="k"><span>${k}</span><span style="color:${confColor(c)}">${pct(c)}</span></div><div class="v">${val ?? "—"}</div><div class="conf"><i style="width:${pct(c)};background:${confColor(c)}"></i></div></div>`;
  const tone = toneOf(d);
  let sumD = 0, sumC = 0;
  const voucher = v ? (() => {
    const rows = v.lines.map((l) => { sumD += +l.debit; sumC += +l.credit; return `<tr><td><span class="acct">${esc(l.account)}</span></td><td>${esc(ACCOUNTS[l.account] || "")}</td><td class="num">${+l.debit ? kr(l.debit) : ""}</td><td class="num">${+l.credit ? kr(l.credit) : ""}</td></tr>`; }).join("");
    const bal = Math.abs(sumD - sumC) < 0.005;
    return `<div class="section"><div class="section-title">Proposed voucher · A${v.number} <span class="pill ${v.status === "posted" ? "green" : "violet"}">${esc(v.status)}</span>
      <span style="margin-left:auto" class="balanced" ${bal ? "" : 'style="color:var(--red)"'}>${bal ? ICON.check.replace("<svg", '<svg width="14" height="14"') + "Balanced" : "Unbalanced"}</span></div>
      <div class="card" style="padding:6px 8px"><table><thead><tr><th>Konto</th><th>Namn</th><th class="num">Debet</th><th class="num">Kredit</th></tr></thead>
      <tbody>${rows}<tr class="total"><td></td><td>Summa</td><td class="num">${kr(sumD)}</td><td class="num">${kr(sumC)}</td></tr></tbody></table></div></div>`;
  })() : `<div class="section"><div class="section-title">Voucher</div><div class="empty" style="padding:22px">${d.status === "quarantined" ? "Never posted — quarantined documents cannot reach the ledger." : d.status === "needs_review" ? "Held for accountant review." : "Waiting for extraction…"}</div></div>`;

  $("#drawer").innerHTML = `<div class="drawer-head"><div class="src" style="${tone === "red" ? "color:var(--red)" : ""}">${d.status === "quarantined" ? ICON.shieldX : d.source === "email" ? ICON.mail : d.source === "light_csv" ? ICON.csv : ICON.upload}</div>
    <div style="min-width:0"><div style="font-weight:600">${esc(e ? e.vendor : d.filename)}</div><div class="mono muted">${esc(d.filename)}</div></div>
    <span class="pill ${tone || "violet"}">${esc(d.status.replace("_", " "))}</span>
    <button class="btn sm ghost x" data-act="close">${ICON.x}</button></div>
    <div class="drawer-body"><div><div class="section-title">Source document</div>${preview}</div>
    <div>
      ${anoms.map((a) => `<div class="card anom ${a.severity}" style="padding:12px;grid-template-columns:30px 1fr"><div class="ic">${a.kind === "injection" ? ICON.shieldX : ICON.alert}</div><div><div class="title">${esc(a.title)}</div><div class="expl">${esc(a.explanation)}</div><div class="rule">Deterministic rule: <code>${esc(a.rule)}</code></div></div></div>`).join("")}
      ${e ? `<div class="section"><div class="section-title">Extracted by Claude ${ICON.sparkle.replace("<svg", '<svg width="12" height="12"')}</div><div class="fields">
        ${F("Vendor", esc(e.vendor))}${F("Org.nr", esc(e.vendor_org_nr || "—"), e.vendor_org_nr ? conf : 0.6)}
        ${F("Type", esc(e.doc_type.replace("_", " ")))}${F("Invoice no.", esc(e.invoice_number || "—"))}
        ${F("Date", esc(e.date))}${F("Account", `<span class="acct">${esc(e.suggested_account)}</span> ${esc(ACCOUNTS[e.suggested_account] || "")}`, Math.max(0, conf - 0.04))}
        ${F("Net", money(e.net, e.currency))}${F(`VAT ${Math.round(+e.vat_rate * 100)}%`, money(e.vat, e.currency))}
        ${F("Gross", `<b>${money(e.gross, e.currency)}</b>`)}${F("Bankgiro / IBAN", esc(e.bankgiro || e.iban || "—"), d.status === "needs_review" && e.bankgiro ? 0.5 : conf)}
      </div>${e.injection_suspected ? `<div class="rule" style="color:var(--red)">${ICON.shieldX.replace("<svg", '<svg width="13" height="13"')} Model flagged embedded instructions — output discarded</div>` : ""}</div>` : ""}
      ${voucher}
      <div class="section"><div class="section-title">Audit trail</div>
        <div class="audit">
          <div class="ev"><b></b><span>Received via ${esc(d.source)}${d.sender ? ` from <span class="mono">${esc(d.sender)}</span>` : ""}</span><span class="muted">${fmtTime(d.received_at)}</span></div>
          ${e ? `<div class="ev"><b></b><span>Extracted · schema validated</span><span class="muted">${pct(e.confidence)}</span></div>` : ""}
          ${v ? `<div class="ev"><b></b><span>Voucher A${v.number} built by deterministic rules · debit = credit</span><span class="muted">${esc(v.date)}</span></div>` : ""}
          ${d.status === "posted" ? `<div class="ev"><b style="background:var(--green);box-shadow:0 0 8px var(--green)"></b><span>Posted to append-only ledger</span><span class="muted">✓</span></div>` : ""}
          ${d.status === "quarantined" ? `<div class="ev"><b style="background:var(--red);box-shadow:0 0 8px var(--red)"></b><span>Quarantined — never reaches ledger</span><span class="muted">⛔</span></div>` : ""}
        </div>
        <dl class="kv"><dt>SHA-256</dt><dd title="${esc(d.sha256)}">${esc(d.sha256.slice(0, 12))}…${esc(d.sha256.slice(-6))}</dd>
          <dt>Model</dt><dd>${esc((v && v.model) || "claude-sonnet-5-5")}</dd><dt>Prompt version</dt><dd>${esc((v && v.prompt_version) || "extract-v3")}</dd>
          <dt>Document id</dt><dd>${esc(d.id)}</dd></dl>
      </div>
    </div></div>`;
}

const money = (x, cur) => (cur && cur !== "SEK" ? `${nf.format(+x)} ${esc(cur)}` : kr(x));

function paper(d) {
  const e = d.extraction;
  if (!e) return `<div class="empty">Rendering preview…</div>`;
  const inj = d.status === "quarantined" && d.note ? `<div class="inj">${esc(d.note)}</div>` : "";
  return `<div class="paper"><h3>${esc(e.vendor)}</h3><div class="meta">${esc(e.vendor_org_nr ? "Org.nr " + e.vendor_org_nr : "")} ${e.invoice_number ? "· Nr " + esc(e.invoice_number) : ""}<br>${esc(e.date)}${e.due_date ? " · Förfallodag " + esc(e.due_date) : ""}</div>
    <div class="r"><span>${esc(e.description || "")}</span><span>${money(e.net, e.currency)}</span></div>
    <div class="r"><span>Moms ${Math.round(+e.vat_rate * 100)} %</span><span>${money(e.vat, e.currency)}</span></div>
    <div class="r t"><span>Att betala</span><span>${money(e.gross, e.currency)}</span></div>
    ${e.bankgiro ? `<div class="meta" style="margin-top:14px">Bankgiro ${esc(e.bankgiro)}${e.ocr_reference ? " · OCR " + esc(e.ocr_reference) : ""}</div>` : ""}${inj}</div>`;
}

// ---------- 2. reconciliation ----------
function viewRecon() {
  const matchedBank = new Set(S.matches.map((m) => m.bank_tx_id));
  const unmatched = S.bank.filter((b) => !matchedBank.has(b.id));
  const ready = S.matches.filter((m) => !m.approved && m.confidence >= 0.95).length;
  const bankSide = (b) => `<div class="side"><div class="s"><span>${esc(b.date)}</span><span class="mono">${esc(b.reference || "")}</span></div>
    <div style="display:flex;justify-content:space-between;gap:10px"><span class="t">${esc(b.text)}</span><span class="amt ${+b.amount > 0 ? "pos" : "neg"}">${kr(b.amount)}</span></div></div>`;
  const docSide = (d) => d ? `<div class="side" data-doc="${esc(d.id)}" style="cursor:pointer"><div class="s"><span>${esc(d.extraction ? d.extraction.date : "")}</span><span class="mono">${esc(d.filename)}</span></div>
    <div style="display:flex;justify-content:space-between;gap:10px"><span class="t">${esc(d.extraction ? d.extraction.vendor : d.filename)}</span><span class="amt">${d.extraction ? money(d.extraction.gross, d.extraction.currency) : ""}</span></div></div>` : "";
  const rows = S.matches.slice().sort((a, b) => a.approved - b.approved || b.confidence - a.confidence).map((m) => {
    const b = bankById(m.bank_tx_id);
    const docs = m.document_ids.map(docById).filter(Boolean);
    const n = docs.length;
    const paths = n > 1 ? docs.map((_, i) => `<path d="M0,50 C50,50 50,${(100 / n) * (i + 0.5)} 100,${(100 / n) * (i + 0.5)}"/>`).join("") : `<path d="M0,50 L100,50"/>`;
    return `<div class="card mrow ${m.approved ? "approved" : ""}" data-match="${esc(m.id)}" data-n="${n}">${b ? bankSide(b) : ""}
      <div class="connector"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><defs><linearGradient id="cg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="100" y2="0"><stop offset="0" stop-color="#8b6cff"/><stop offset="1" stop-color="#3dd6f5"/></linearGradient></defs>${paths}</svg>
        <span class="pill ${confTone(m.confidence)}">${pct(m.confidence)}${n > 1 ? ` · 1:${n}` : ""}</span></div>
      <div>${docs.map(docSide).join("")}</div>
      <div class="actions">${m.approved ? `<span class="pill green">${ICON.check}Approved</span>` : `<button class="btn sm green" data-approve="${esc(m.id)}">${ICON.check}Approve</button>`}<span class="method">${esc(m.method)}</span></div></div>`;
  }).join("");
  return `<div class="view-head"><div><h1>Reconciliation</h1><div class="sub">${S.matches.length} matches · ${S.matches.filter((m) => m.approved).length} approved · ${unmatched.length} bank lines without a document</div></div>
    <div class="btn-row"><button class="btn primary" data-act="approveAll" ${ready ? "" : "disabled"}>${ICON.check}Approve all ≥95% (${ready})</button></div></div>
    <div class="recon"><div style="display:grid;grid-template-columns:1fr 150px 1fr 130px;padding:0 14px" class="muted"><span>${ICON.bank.replace("<svg", '<svg width="13" height="13" style="vertical-align:-2px"')} Bank (SEB företagskonto)</span><span></span><span>Documents</span><span></span></div>
    ${rows || '<div class="empty">No matches yet.</div>'}</div>
    <h2 style="margin-top:26px">Unmatched bank lines</h2>
    <div class="grid3 unmatched">${unmatched.map((b) => `<div>${bankSide(b)}</div>`).join("") || '<div class="muted">All bank lines matched.</div>'}</div>`;
}

// ---------- 3. books ----------
function viewBooks() {
  const R = S.reports || {};
  const pnl = R.pnl || { revenue: 0, expenses: {}, result: 0 };
  const bs = R.balance_sheet || { assets: {}, liabilities_equity: {} };
  const vat = R.vat_return || {};
  const rowsOf = (obj) => Object.entries(obj || {}).sort(([a], [b]) => a.localeCompare(b)).map(([a, x]) => `<tr><td><span class="acct">${esc(a)}</span></td><td>${esc(ACCOUNTS[a] || "")}</td><td class="num">${kr(x)}</td></tr>`).join("");
  const sum = (obj) => Object.values(obj || {}).reduce((s, x) => s + +x, 0);
  const expTotal = sum(pnl.expenses);
  const VB = [["05", "Momspliktig försäljning"], ["10", "Utgående moms 25 %"], ["48", "Ingående moms att dra av"], ["49", "Moms att betala eller få tillbaka"]];
  const journal = S.vouchers.slice().sort((a, b) => a.number - b.number).map((v) => {
    const tot = v.lines.reduce((s, l) => s + +l.debit, 0);
    return `<tr ${v.document_id ? `data-doc="${esc(v.document_id)}" style="cursor:pointer"` : ""}><td class="mono">A${v.number}</td><td class="mono">${esc(v.date)}</td><td>${esc(v.description)}</td>
      <td><div class="journal-lines">${v.lines.map((l) => `<span><span class="acct">${esc(l.account)}</span><span class="num" style="text-align:right">${+l.debit ? nf.format(+l.debit) : ""}</span><span class="num muted" style="text-align:right">${+l.credit ? nf.format(+l.credit) : ""}</span></span>`).join("")}</div></td>
      <td class="num">${kr(tot)}</td><td><span class="pill ${v.status === "posted" ? "green" : "violet"}">${esc(v.status)}</span></td></tr>`;
  }).join("");
  return `<div class="view-head"><div><h1>Books</h1><div class="sub">${esc(S.client.name)} · Räkenskapsår 2026 · BAS 2024</div></div></div>
    <div class="card export-card"><div class="logo" style="width:44px;height:44px">${ICON.download.replace("<svg", '<svg width="20" height="20" style="color:#fff"')}</div>
      <div class="txt"><b>Export SIE4 → Fortnox / Visma</b><div class="muted">${S.vouchers.length} vouchers · balanced · ready to import into any Swedish ledger</div></div>
      <div class="btn-row"><button class="btn ghost" data-act="siePreview">${ICON.eye}SIE4 preview</button><button class="btn primary xl" data-act="sieExport">${ICON.download}Export SIE4</button></div></div>
    <div class="grid2">
      <div class="card"><h2>Resultaträkning</h2><table><tbody>
        <tr><td><span class="acct">3xxx</span></td><td>Nettoomsättning</td><td class="num">${kr(pnl.revenue)}</td></tr>${rowsOf(pnl.expenses)}
        <tr class="total"><td></td><td>Summa kostnader</td><td class="num">${kr(-expTotal)}</td></tr></tbody></table>
        <div style="display:flex;justify-content:space-between;align-items:end;margin-top:14px"><span class="muted">Resultat</span><span class="result" style="color:${+pnl.result >= 0 ? "var(--green)" : "var(--red)"}">${kr(pnl.result)}</span></div></div>
      <div class="card"><h2>Balansräkning</h2><table><thead><tr><th colspan="3">Tillgångar</th></tr></thead><tbody>${rowsOf(bs.assets)}
        <tr class="total"><td></td><td>Summa tillgångar</td><td class="num">${kr(sum(bs.assets))}</td></tr></tbody></table>
        <table style="margin-top:12px"><thead><tr><th colspan="3">Eget kapital &amp; skulder</th></tr></thead><tbody>${rowsOf(bs.liabilities_equity)}
        <tr class="total"><td></td><td>Summa EK &amp; skulder</td><td class="num">${kr(sum(bs.liabilities_equity))}</td></tr></tbody></table></div>
    </div>
    <div class="card" style="margin-top:16px"><h2>Momsdeklaration · Skatteverket</h2><div class="vat-boxes">${VB.map(([k, l]) => `<div class="vbox ${k === "49" ? "pay" : ""}"><span class="code">Ruta ${k}</span><div class="lbl">${l}</div><div class="v">${kr(vat[k])}</div></div>`).join("")}</div></div>
    <div class="card" style="margin-top:16px"><h2>Verifikationslista</h2><div class="table-wrap"><table><thead><tr><th>Ver</th><th>Datum</th><th>Text</th><th>Konto · Debet · Kredit</th><th class="num">Belopp</th><th>Status</th></tr></thead><tbody>${journal || '<tr><td colspan="6" class="muted">No vouchers yet.</td></tr>'}</tbody></table></div></div>`;
}

async function siePreview() {
  const m = $("#modal");
  m.hidden = false;
  m.innerHTML = `<div class="box"><header>${ICON.table.replace("<svg", '<svg width="16" height="16"')}<b>SIE4 preview</b><span class="pill violet">PC8 · SIETYP 4</span><button class="btn sm ghost" style="margin-left:auto" data-act="closeModal">${ICON.x}</button></header><pre>Loading…</pre></div>`;
  const text = await api.sie4();
  $("pre", m).textContent = text;
}

// ---------- 4. trust ----------
const THREAT_KINDS = new Set(["injection", "iban_change", "duplicate"]);
function threats() {
  const ids = new Set();
  S.anomalies.forEach((a) => {
    const d = a.document_id && docById(a.document_id);
    if (THREAT_KINDS.has(a.kind) && d && d.source !== "light_csv") ids.add(d.id);
  });
  S.documents.forEach((d) => { if (d.status === "quarantined") ids.add(d.id); });
  return [...ids].map(docById);
}

function viewTrust() {
  const sev = { high: [], medium: [], low: [] };
  S.anomalies.forEach((a) => (sev[a.severity] || sev.low).push(a));
  const inj = S.anomalies.find((a) => a.kind === "injection");
  const injDoc = inj && inj.document_id ? docById(inj.document_id) : S.documents.find((d) => d.status === "quarantined");
  const attack = (injDoc && injDoc.note) || (inj && (inj.explanation.match(/["“'](.+?)["”']/) || [])[1]) || "";
  const injCard = inj || injDoc ? `<div class="card inject-card"><div class="head"><div class="shield">${ICON.shieldX}</div>
      <div><div style="font-weight:650;font-size:16px;letter-spacing:-.01em">Prompt injection blocked</div><div class="muted">${esc(injDoc ? injDoc.filename : "")}${injDoc && injDoc.sender ? " · from " + esc(injDoc.sender) : ""}</div></div>
      <span class="pill red" style="margin-left:auto">Quarantined</span></div>
      <pre class="attack">${esc(attack || (inj ? inj.explanation : ""))}</pre>
      <div class="verdict"><span class="pill green">${ICON.check}LLM had no tools to act</span><span class="pill green">${ICON.check}Output schema-validated</span><span class="pill green">${ICON.check}Never posted</span><span class="pill green">${ICON.check}0 kr moved</span></div></div>` : "";
  const SEVL = { high: "High severity", medium: "Medium", low: "Low" };
  const groups = ["high", "medium", "low"].filter((k) => sev[k].length).map((k) => `<div class="sev-group"><div class="section-title"><span class="pill ${k === "high" ? "red" : k === "medium" ? "amber" : "violet"}">${SEVL[k]} · ${sev[k].length}</span></div>
    ${sev[k].map((a) => `<div class="card anom ${k}" ${a.document_id ? `data-doc="${esc(a.document_id)}" style="cursor:pointer"` : ""}><div class="ic">${a.kind === "injection" ? ICON.shieldX : k === "low" ? ICON.info : ICON.alert}</div>
      <div><div class="title">${esc(a.title)}</div><div class="expl">${esc(a.explanation)}</div><div class="rule">Deterministic rule: <code>${esc(a.rule)}</code></div></div>
      <div style="text-align:right">${a.invoice_number ? `<span class="pill">${ICON.csv}Light AR · ${esc(a.invoice_number)}</span>` : a.bank_tx_id ? `<span class="pill">${ICON.bank}Bank</span>` : `<span class="pill">${ICON.inbox}Inbox</span>`}</div></div>`).join("")}</div>`).join("");
  const SEC = [
    ["LLM has no tools", "Claude only reads and returns JSON. It cannot pay, post, email or call anything."],
    ["Schema-validated output", "Every extraction is parsed into a strict Pydantic model; anything else is rejected."],
    ["Deterministic posting + balance check", "Vouchers are built by code from BAS rules. Debit must equal credit or nothing is written."],
    ["Sender allowlist & quarantine", "Unknown senders and suspected injections are isolated before they touch the books."],
    ["Append-only ledger & audit trail", "Corrections are reversals, never edits. Every doc keeps its SHA-256, model and prompt version."],
    ["EU hosting (roadmap)", "Runs locally today. Production: EU-hosted Postgres + EU-region inference, Bokföringslagen 7-year retention."],
  ];
  const th = threats();
  const injLeaked = S.documents.filter((d) => d.status === "quarantined").some((d) => S.vouchers.some((v) => v.document_id === d.id && v.status === "posted"));
  const hero = th.length ? `<div class="trust-hero"><span class="r">${th.length} threat${th.length > 1 ? "s" : ""} caught</span> · <span class="g">${injLeaked ? "check ledger" : "0 injections reached the ledger"}</span></div>` : "";
  return `${hero}<div class="view-head"><div><h1>Trust Center</h1><div class="sub">${S.anomalies.length} findings · ${sev.high.length} high severity · every flag comes from a deterministic rule, not a model's opinion</div></div></div>
    <div style="display:grid;grid-template-columns:minmax(0,1.6fr) minmax(280px,1fr);gap:16px;align-items:start">
      <div>${injCard}${groups || '<div class="empty">No anomalies. 🛡</div>'}</div>
      <div class="card security"><h2 style="display:flex;align-items:center;gap:8px">${ICON.lock.replace("<svg", '<svg width="16" height="16"')}Security model</h2>
        <ul>${SEC.map(([t, s]) => `<li><span class="ck">${ICON.check}</span><div><b>${t}</b><span>${s}</span></div></li>`).join("")}</ul></div>
    </div>`;
}

// ---------- toasts ----------
function toast(tone, title, body, icon) {
  const el = document.createElement("div");
  el.className = `toast ${tone}`;
  el.innerHTML = `<div class="ic">${icon || (tone === "red" ? ICON.alert : tone === "green" ? ICON.check : ICON.info)}</div><div><b>${esc(title)}</b><span>${esc(body || "")}</span></div>`;
  const box = $("#toasts");
  box.appendChild(el);
  while (box.children.length > 4) box.firstChild.remove();
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 320); }, 5200);
}

// ---------- events ----------
document.addEventListener("click", async (e) => {
  const t = e.target.closest("[data-go],[data-act],[data-filter],[data-approve],[data-doc],[data-client],.doc");
  if (!t) { if (menuOpen) { menuOpen = false; renderTop(); } return; }
  if (t.dataset.act !== "menu" && menuOpen) menuOpen = false;
  if (t.dataset.go) return go(t.dataset.go);
  if (t.dataset.client) { toast("amber", t.dataset.client, "Demo: only Lovelight Design AB is connected live."); return render(); }
  if (t.dataset.filter) { filter = t.dataset.filter; return render(); }
  if (t.dataset.approve) { await api.approve(t.dataset.approve); toast("green", "Match approved", "Voucher posted to ledger"); return scheduleRefresh(); }
  if (t.dataset.doc) return openDrawer(t.dataset.doc);
  if (t.classList.contains("doc")) return openDrawer(t.dataset.id);
  switch (t.dataset.act) {
    case "menu": menuOpen = !menuOpen; return renderTop();
    case "replay": toast("green", "Replaying demo batch", "15 documents incoming from email + Light", ICON.play); await api.replay(); return scheduleRefresh();
    case "reset": closeDrawer(); await api.reset(); seen.clear(); return scheduleRefresh();
    case "approveAll": await api.approveAll(); toast("green", "Approved all ≥95%", "Deterministic vouchers posted"); return scheduleRefresh();
    case "sieExport": if (!MOCK) window.open("/api/export/sie4", "_blank"); return siePreview();
    case "siePreview": return siePreview();
    case "closeModal": $("#modal").hidden = true; return;
    case "close": return closeDrawer();
  }
});
$("#scrim").addEventListener("click", closeDrawer);
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") e.currentTarget.hidden = true; });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeDrawer(); $("#modal").hidden = true; } });

function connect() {
  const liveEl = $(".live");
  if (MOCK) { window.LovelightMock.on(onEvent); return; }
  const es = new EventSource("/api/events");
  es.onopen = () => liveEl.classList.remove("off");
  es.onerror = () => liveEl.classList.add("off");
  es.onmessage = (m) => onEvent(JSON.parse(m.data));
}

connect();
const ready = refresh().then(() => { if (QS.get("doc")) openDrawer(QS.get("doc")); });

window.Lovelight = {
  ready, api, ICON, MOCK, go, refresh, toast, openDrawer, closeDrawer, siePreview,
  state: () => S,
  view: () => view,
};
