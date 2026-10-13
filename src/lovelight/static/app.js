"use strict";

const MOCK = new URLSearchParams(location.search).has("mock");
const $ = (sel, root = document) => root.querySelector(sel);

// BAS 2024 account names in English. GET /api/knowledge (accounts.yaml) overrides these at startup.
const ACCOUNTS = {
  "1220": "Equipment and fixtures", "1510": "Accounts receivable", "1930": "Business bank account", "2081": "Share capital",
  "2091": "Retained earnings", "2099": "Profit for the year", "2440": "Accounts payable", "2611": "Output VAT 25%",
  "2640": "Input VAT", "3001": "Sales of services, 25% VAT", "3740": "Rounding", "3960": "Exchange-rate gains",
  "4010": "Purchased materials", "5010": "Premises rent", "5060": "Cleaning", "5410": "Low-value equipment", "5420": "Software",
  "5460": "Consumables", "5611": "Fuel", "5800": "Travel", "5810": "Tickets", "5910": "Advertising", "6071": "Client entertainment",
  "6110": "Office supplies", "6212": "Mobile phone", "6530": "Accounting services", "6540": "IT services", "6550": "Consulting fees",
  "6570": "Bank fees", "6990": "Other external costs", "7960": "Exchange-rate losses",
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
  chain: I('<path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 1 1 0 10h-2"/><path d="M8 12h8"/>'),
  brain: I('<path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/><path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/><path d="M12 5v13"/>'),
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
const M = () => window.LovelightMock;
const api = MOCK
  ? {
      state: async () => M().getState(),
      replay: async () => M().replay(),
      reset: async () => M().reset(),
      upload: async (files) => M().upload(files),
      approve: async (id) => M().approve(id),
      approveAll: async () => M().approveAll(),
      sie4: async () => M().sie4(),
      fileUrl: () => null,
      knowledge: async () => M().knowledge(),
      audit: async (id) => M().audit(id),
      auditVerify: async () => M().auditVerify(),
      correct: async (id, body) => M().correct(id, body),
      review: async () => { throw new Error("Approving and rejecting needs the live server."); },
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
      knowledge: () => optional("/api/knowledge"),
      audit: async (id) => {
        const r = await optional(id ? `/api/audit?entity_id=${encodeURIComponent(id)}` : "/api/audit");
        return r && (Array.isArray(r) ? r : r.events || []);
      },
      auditVerify: () => optional("/api/audit/verify"),
      correct: (id, body) => postJson(`/api/documents/${encodeURIComponent(id)}/correct`, body),
      review: (id, verdict, body) => postJson(`/api/documents/${encodeURIComponent(id)}/${verdict}`, body),
    };
async function postJson(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(errDetail(j) || `HTTP ${r.status}`), { status: r.status });
  return j;
}
// Endpoints a backend may not expose yet: null instead of a toast, so the UI degrades quietly.
async function optional(path) {
  const r = await fetch(path).catch(() => null);
  return r && r.ok ? r.json() : null;
}
const errDetail = (j) => (typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((x) => x.msg).join("; ") : "");
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
let KB = null; // GET /api/knowledge
const AUD = { verify: null, all: null, byId: {}, filter: "all" };
const corrected = {}; // docId -> last POST /correct response, shown in the drawer
const docConf = (d) => (d.extraction ? (d.extraction.confidence_detail ? d.extraction.confidence_detail.score : d.extraction.confidence) : 0);
const docAcct = (d) => (d.classification ? d.classification.account : d.extraction ? d.extraction.suggested_account : "");
let menuOpen = false;
const seen = new Set();
const shownStats = { docs: 0, pct: 0, hours: 0 };

const docById = (id) => S.documents.find((d) => d.id === id);
const bankById = (id) => S.bank.find((b) => b.id === id);

async function refresh() {
  S = await api.state();
  render();
  loadAudit();
}
async function loadKnowledge() {
  const k = await api.knowledge();
  if (!k) return;
  KB = k;
  Object.assign(ACCOUNTS, k.accounts || {});
  if (S) render();
}
let auditBusy = false;
async function loadAudit() {
  if (auditBusy) return;
  auditBusy = true;
  try {
    const [v, all, mine] = await Promise.all([
      api.auditVerify(),
      view === "audit" ? api.audit(null) : null,
      drawerDoc ? api.audit(drawerDoc) : null,
    ]);
    AUD.verify = v;
    if (all) AUD.all = all;
    if (drawerDoc && mine) AUD.byId[drawerDoc] = mine;
  } finally {
    auditBusy = false;
  }
  if (S) render();
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
  ["audit", "Audit trail", ICON.chain],
  ["knowledge", "Knowledge base", ICON.brain],
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
    v.innerHTML = { bureau: viewBureau, recon: viewRecon, books: viewBooks, trust: viewTrust, audit: viewAudit, knowledge: viewKnowledge }[view]();
    v.classList.toggle("fresh", fresh);
  }
  if (drawerDoc) renderDrawer();
}

function go(v) {
  view = v;
  $("#view").scrollTop = 0;
  closePop();
  render();
  if (v === "audit") loadAudit();
  if (v === "knowledge") loadKnowledge();
}

function renderNav() {
  const open = S.matches.filter((m) => !m.approved).length;
  const high = S.anomalies.filter((a) => a.severity === "high").length;
  const review = S.documents.filter((d) => d.source !== "light_csv" && (d.status === "needs_review" || d.status === "quarantined")).length;
  const broken = AUD.verify && !AUD.verify.ok;
  const badge = { inbox: review ? `<span class="badge amber">${review}</span>` : "", recon: open ? `<span class="badge amber">${open}</span>` : "", trust: high ? `<span class="badge">${high}</span>` : "",
    audit: broken ? `<span class="badge">!</span>` : "" };
  $("#nav").innerHTML =
    `<div class="nav-section">Bureau</div>` +
    NAV.map(([k, label, ic], i) => (i === 1 ? `<div class="nav-section">${esc(S.client.name)}</div>` : "") +
      `<button class="nav-item ${view === k ? "active" : ""}" data-go="${k}">${ic}<span>${label}</span>${badge[k] || ""}</button>`).join("");
}

function renderTop() {
  const cs = $("#clientSwitch");
  const name = view === "bureau" ? "Nordic Redovisning AB" : S.client.name;
  const sub = view === "bureau" ? `${CLIENTS.length} clients · Bureau` : `Org no. ${S.client.org_nr}`;
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
  const hrs = ((st.minutes_saved || 0) / 60).toLocaleString("en-GB", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
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
    extracted: e ? `${whyPill("doc", d.id, docConf(d))}<span class="acct">${esc(docAcct(d))}</span> <span>${esc(ACCOUNTS[docAcct(d)] || "")}</span>` : "",
    matched: `<span class="pill violet">${ICON.link}Bank match found</span><span class="ellip">awaiting approval</span>${e ? whyPill("doc", d.id, docConf(d), true) : ""}`,
    posted: `<span class="pill green">${ICON.check}Posted</span>${e ? `<span class="acct">${esc(docAcct(d))}</span> <span class="ellip">${esc(ACCOUNTS[docAcct(d)] || "")}</span>${whyPill("doc", d.id, docConf(d), true)}` : ""}`,
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

// ---------- confidence breakdown ----------
const CHECK_LABEL = {
  arithmetic: "Net + VAT = gross", vat_rate_legal: "Legal Swedish VAT rate", vat_activity: "VAT fits the activity",
  required_fields: "Required fields present", identifier_checksum: "Org no. / bankgiro checksum", date_plausible: "Dates plausible",
  model_self_report: "Model self-report", vendor_history: "Consistent with vendor history",
  amount: "Amount", reference: "OCR / invoice reference", name: "Counterparty name", date: "Date proximity",
};
const checkLabel = (n) => CHECK_LABEL[n] || n.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
const fmtRates = (rates) => (rates && rates.length ? rates.map((r) => Math.round(+r * 100)).join(" / ") + "%" : "—");

function whyPill(kind, id, score, small) {
  return `<button class="pill ${confTone(score)} why ${small ? "sm" : ""}" data-why="${kind}:${esc(id)}" title="Show the checks behind this score">${small ? pct(score) : `Why ${pct(score)}?`}</button>`;
}

function confPanel(c, selfReport) {
  if (!c) {
    return `<div class="cb"><div class="cb-head"><div class="cb-score" style="color:${confColor(selfReport)}">${pct(selfReport)}</div>
      <div><b>Model self-report</b><div class="muted">No composite score for this item. This is the model's own, uncalibrated estimate.</div></div></div></div>`;
  }
  const appl = c.components.filter((x) => x.passed !== null && x.passed !== undefined);
  const wsum = appl.reduce((s, x) => s + x.weight, 0) || 1;
  const self = c.components.find((x) => x.name === "model_self_report");
  const rows = c.components.map((x) => {
    const na = x.passed === null || x.passed === undefined;
    const share = na ? 0 : x.weight / wsum;
    const pts = share * x.value * 100;
    const cls = na ? "na" : x.passed ? "ok" : "bad";
    return `<div class="cb-row ${cls}"><span class="cb-tick">${na ? "n/a" : x.passed ? ICON.check : ICON.x}</span>
      <div class="cb-mid"><div class="cb-name">${esc(checkLabel(x.name))}<span class="muted">weight ${x.weight.toFixed(2)}</span></div>
        <div class="cb-detail">${esc(x.detail || "")}</div>
        <div class="cb-bar" title="Bar length = share of the score; fill = how well the check passed"><i style="width:${(share * 100).toFixed(1)}%"><b style="width:${(x.value * 100).toFixed(0)}%"></b></i></div></div>
      <span class="cb-pts tnum">${na ? "—" : "+" + pts.toFixed(1)}</span></div>`;
  }).join("");
  const gates = (c.gates || []).map((g) => `<div class="cb-gate ${g.startsWith("floor") ? "floor" : ""}">${g.startsWith("floor") ? ICON.info : ICON.alert}${g.startsWith("floor") ? `Floor applied: <code>${esc(g)}</code>` : `Hard gate failed: <code>${esc(g)}</code>, score capped`}</div>`).join("");
  return `<div class="cb"><div class="cb-head"><div class="cb-score" style="color:${confColor(c.score)}">${pct(c.score)}</div>
      <div><b>Weighted mean of ${appl.length} applicable check${appl.length === 1 ? "" : "s"}</b><div class="muted mono">${esc(c.method)} · ${esc(c.version)}</div></div></div>
    ${gates}<div class="cb-rows">${rows}</div>
    <div class="cb-foot">${self ? `The model's own score is one check (weight ${self.weight.toFixed(2)}${selfReport !== undefined ? `, it reported ${pct(selfReport)}` : ""}). ` : ""}Every other check is deterministic code.</div></div>`;
}

let popFor = null;
function openPop(trigger, html) {
  closePop();
  const pop = document.createElement("div");
  pop.className = "pop";
  pop.id = "pop";
  pop.innerHTML = html;
  document.body.appendChild(pop);
  const r = trigger.getBoundingClientRect();
  const w = pop.offsetWidth, h = pop.offsetHeight;
  const left = Math.max(12, Math.min(innerWidth - w - 12, r.left + r.width / 2 - w / 2));
  const below = r.bottom + 8 + h < innerHeight - 12;
  pop.style.left = `${left}px`;
  pop.style.top = `${below ? r.bottom + 8 : Math.max(12, r.top - h - 8)}px`;
  popFor = trigger.dataset.why;
}
function closePop() {
  const p = $("#pop");
  if (p) p.remove();
  popFor = null;
}
function showWhy(trigger) {
  if (popFor === trigger.dataset.why) return closePop();
  const [kind, id] = trigger.dataset.why.split(/:(.*)/s);
  if (kind === "doc") {
    const d = docById(id);
    if (!d || !d.extraction) return;
    openPop(trigger, `<div class="pop-title">${esc(d.extraction.vendor)}<span class="muted">extraction confidence</span></div>${confPanel(d.extraction.confidence_detail, d.extraction.confidence)}`);
  } else {
    const m = S.matches.find((x) => x.id === id);
    if (!m) return;
    openPop(trigger, `<div class="pop-title">Bank match<span class="muted">${esc(m.method)}</span></div>${confPanel(m.confidence_detail, m.confidence_detail ? undefined : m.confidence)}`);
  }
}

// ---------- audit helpers ----------
const ACTION_LABEL = {
  "doc.received": "Received", "doc.extracted": "Extracted, schema-validated", "kb.hit": "Knowledge-base hit", "kb.miss": "Not in knowledge base",
  "doc.classified": "Account chosen", "doc.quarantined": "Quarantined", "doc.needs_review": "Held for review", "voucher.proposed": "Voucher proposed",
  "voucher.posted": "Voucher posted", "voucher.corrected": "Corrected by accountant", "ledger.reverse": "Reversal posted", "match.approved": "Bank match approved",
  "match.found": "Bank match found", "kb.proposed": "Knowledge-base entry proposed", "doc.duplicate_skipped": "Duplicate skipped",
  "doc.extract_retry": "Extraction retried", "books.reset": "Books reset",
};
const shortHash = (h) => (h ? `${h.slice(0, 8)}…` : "—");
const actorTone = (a) => (a.startsWith("user:") ? "green" : a.startsWith("model:") ? "violet" : "cyan");
function evSummary(ev) {
  const x = ev.data || {};
  switch (ev.action) {
    case "doc.received": return [x.filename, x.source && `via ${x.source}`, x.sender].filter(Boolean).join(" · ");
    case "doc.extracted": return [x.model, x.prompt_version && `prompt ${x.prompt_version}`, x.output_sha256 && `output ${shortHash(x.output_sha256)}`].filter(Boolean).join(" · ");
    case "kb.hit": return `${x.entry_id || ""}${x.matched_on ? ` on ${x.matched_on.replace("_", " ")}` : ""}${x.matched_value ? ` "${x.matched_value}"` : ""}`;
    case "kb.miss": return [x.vendor, x.activity && `model activity: ${x.activity}`].filter(Boolean).join(" · ");
    case "doc.classified": {
      const c = x.classification || x;
      const score = x.score !== undefined ? x.score : x.confidence_detail && x.confidence_detail.score;
      return `${c.account || ""} ${ACCOUNTS[c.account] || ""}${c.source ? ` · ${c.source}` : ""}${c.overridden_model_account ? ` (model said ${c.overridden_model_account})` : ""}${score !== undefined ? ` · ${pct(score)}` : ""}`;
    }
    case "voucher.posted": return [x.number !== undefined && `A${x.number}`, x.lines && x.lines.length && x.lines.map((l) => l.account).join(" / "), x.date].filter(Boolean).join(" · ") || evSummaryDefault(x);
    case "voucher.corrected": return `${(x.before || {}).account || "?"} → ${(x.after || {}).account || "?"} · "${x.reason || ""}"`;
    case "match.found": return `${(x.document_ids || []).length} document${(x.document_ids || []).length === 1 ? "" : "s"} · ${x.method || ""}${x.confidence !== undefined ? ` · ${pct(x.confidence)}` : ""}`;
    case "kb.proposed": return [x.vendor, x.account && `→ ${x.account}`, x.activity].filter(Boolean).join(" ");
    case "books.reset": return [x.bank_txs !== undefined && `${x.bank_txs} bank lines`, x.ar_vouchers_posted && `${x.ar_vouchers_posted.length} AR vouchers`, x.ar_held_for_review && `${x.ar_held_for_review.length} held`].filter(Boolean).join(" · ");
    case "match.approved": return `${(x.document_ids || []).length} document${(x.document_ids || []).length === 1 ? "" : "s"}${x.confidence !== undefined ? ` · ${pct(x.confidence)}` : ""}`;
    case "doc.needs_review": return x.note || "";
    default: return evSummaryDefault(x);
  }
}
function evSummaryDefault(x) {
  return Object.entries(x).filter(([, v]) => v !== null && typeof v !== "object").slice(0, 3).map(([k, v]) => `${k}: ${v}`).join(" · ");
}
function auditRows(events, showEntity) {
  return events.slice().reverse().map((ev) => {
    const tone = actorTone(ev.actor);
    const docId = ev.entity === "document" ? ev.entity_id : (ev.data || {}).document_id;
    const ent = showEntity ? `<span class="aev-ent mono" ${docId && docById(docId) ? `data-doc="${esc(docId)}"` : ""}>${esc(ev.entity)}/${esc(ev.entity_id)}</span>` : "";
    return `<div class="aev"><span class="aev-seq mono">#${ev.seq}</span><i class="aev-dot ${tone}"></i>
      <div class="aev-main"><div class="aev-top"><b>${esc(ACTION_LABEL[ev.action] || ev.action)}</b><span class="pill sm ${tone}">${esc(ev.actor)}</span>${ent}</div>
        <div class="aev-sum">${esc(evSummary(ev))}</div></div>
      <div class="aev-meta"><span>${fmtTime(ev.ts)}</span><span class="mono hash" title="prev ${esc(ev.prev_hash)}&#10;hash ${esc(ev.hash)}">${esc(shortHash(ev.prev_hash))} → ${esc(shortHash(ev.hash))}</span></div></div>`;
  }).join("");
}
function chainBadge(big) {
  const v = AUD.verify;
  if (!v) return `<span class="chain-badge off ${big ? "big" : ""}">${ICON.chain}Audit log unavailable</span>`;
  const n = typeof v.events === "number" ? v.events : (v.events || []).length;
  return v.ok
    ? `<span class="chain-badge ok ${big ? "big" : ""}" title="Every hash recomputed from the first event">${ICON.shieldCheck}Chain verified · ${n} events · head <span class="mono">${esc((v.head || "").slice(0, 6))}…</span></span>`
    : `<span class="chain-badge bad ${big ? "big" : ""}">${ICON.shieldX}Chain broken at event #${esc(v.first_bad_seq)} · ${n} events</span>`;
}

// ---------- drawer ----------
function openDrawer(id) {
  if (!S || !docById(id)) return;
  drawerDoc = id;
  closePop();
  renderDrawer();
  $("#drawer").classList.add("on");
  $("#scrim").classList.add("on");
  loadAudit();
}
function closeDrawer() {
  drawerDoc = null;
  $("#drawer").classList.remove("on");
  $("#scrim").classList.remove("on");
}

const SOURCE_BADGE = {
  correction: ["green", "Learned from correction"], policy: ["cyan", "Activity policy"], model: ["violet", "Model, policy-consistent"], fallback: ["amber", "Fallback"],
};

function voucherCard(v) {
  let sumD = 0, sumC = 0;
  const rows = v.lines.map((l) => { sumD += +l.debit; sumC += +l.credit; return `<tr><td><span class="acct">${esc(l.account)}</span></td><td>${esc(ACCOUNTS[l.account] || "")}</td><td class="num">${+l.debit ? kr(l.debit) : ""}</td><td class="num">${+l.credit ? kr(l.credit) : ""}</td></tr>`; }).join("");
  const bal = Math.abs(sumD - sumC) < 0.005;
  const orig = v.reverses_id && S.vouchers.find((x) => x.id === v.reverses_id);
  const tone = v.status === "reversed" ? "red" : v.status === "posted" ? "green" : "violet";
  return `<div class="section voucher ${v.status === "reversed" ? "is-reversed" : ""}"><div class="section-title">${v.reverses_id ? `Reversal of A${orig ? orig.number : "?"}` : "Voucher"} · A${v.number} <span class="pill ${tone}">${esc(v.status)}</span>
      <span style="margin-left:auto" class="balanced ${bal ? "" : "off"}">${bal ? ICON.check.replace("<svg", '<svg width="14" height="14"') + "Balanced" : "Unbalanced"}</span></div>
    <div class="card" style="padding:6px 8px"><table><thead><tr><th>Account</th><th>Name</th><th class="num">Debit</th><th class="num">Credit</th></tr></thead>
    <tbody>${rows}<tr class="total"><td></td><td>Total</td><td class="num">${kr(sumD)}</td><td class="num">${kr(sumC)}</td></tr></tbody></table></div></div>`;
}

function whyAccount(d, liveVoucher) {
  const e = d.extraction, c = d.classification, k = d.kb_match;
  if (!e) return "";
  const acct = docAcct(d);
  const [tone, label] = c ? SOURCE_BADGE[c.source] || ["violet", c.source] : ["amber", "Model suggestion (not classified)"];
  const actId = (c && c.activity) || (k && k.activity) || e.activity;
  const act = KB && KB.activities ? (Array.isArray(KB.activities) ? KB.activities.find((a) => a.id === actId) : KB.activities[actId]) : null;
  const rates = c && c.expected_vat_rates && c.expected_vat_rates.length ? c.expected_vat_rates : null;
  const kbCard = k
    ? `<div class="kb-card hit"><div class="kb-top"><span class="pill violet">${ICON.brain}Knowledge base</span><b>${esc(k.vendor_name)}</b><span class="muted">matched on ${esc(k.matched_on.replace("_", " "))} <span class="mono">"${esc(k.matched_value)}"</span> · ${pct(k.score)}</span></div>
        <div class="kb-body">${esc(k.vendor_profile)} → activity <b>${esc(k.activity)}</b>${k.vat_rates && k.vat_rates.length ? ` · vendor VAT narrowed to ${fmtRates(k.vat_rates)}` : ""}</div></div>`
    : `<div class="kb-card miss"><div class="kb-top"><span class="pill">${ICON.brain}Not in knowledge base</span><span class="muted">vendor profile and activity inferred by the model</span></div>
        <div class="kb-body">${esc(e.vendor_profile || "No vendor profile")}${e.activity ? ` → activity <b>${esc(e.activity)}</b>` : ""}</div></div>`;
  const vatNote = c && c.vat_ambiguous
    ? `<div class="note amber">${ICON.alert}<div><b>VAT ambiguous.</b> ${esc(act ? act.label : actId || "This activity")} allows ${fmtRates(c.expected_vat_rates)}. Booked ${Math.round(+e.vat_rate * 100)}% as printed on the document; flagged, not guessed.${act && act.vat_note ? `<div class="muted">${esc(act.vat_note)}</div>` : ""}</div></div>` : "";
  const cands = (e.account_candidates || []).slice().sort((a, b) => b.probability - a.probability);
  const candList = cands.length ? `<div class="cands"><div class="sub-title">Model's ranked options <span class="muted">self-reported</span></div>${cands.map((x) =>
    `<div class="cand ${x.account === acct ? "on" : ""}"><span class="acct">${esc(x.account)}</span><span class="cand-name">${esc(x.name || ACCOUNTS[x.account] || "")}</span>
      <span class="cand-bar"><i style="width:${Math.round(x.probability * 100)}%"></i></span><span class="tnum muted">${pct(x.probability)}</span>
      ${x.rationale ? `<div class="cand-why">${esc(x.rationale)}</div>` : ""}</div>`).join("")}</div>` : "";
  const canCorrect = liveVoucher && e.doc_type !== "customer_invoice";
  const cost = Object.keys(ACCOUNTS).filter((a) => /^[4-7]/.test(a));
  const order = [...new Set([...cands.map((x) => x.account), ...(act ? act.accounts || [] : []), ...cost])].filter((a) => ACCOUNTS[a]);
  const firstAlt = order.find((a) => a !== acct) || acct;
  const form = canCorrect ? `<form class="correct-form" data-correct="${esc(d.id)}"><div class="sub-title">Change account</div>
      <div class="cf-row"><select name="account" aria-label="New account">${order.map((a) => `<option value="${a}" ${a === firstAlt ? "selected" : ""}>${a} ${esc(ACCOUNTS[a])}${a === acct ? " (current)" : ""}</option>`).join("")}</select>
      <input name="reason" placeholder="Reason, e.g. annual pass, not a single ride" aria-label="Reason" autocomplete="off">
      <button class="btn sm primary" type="submit">Reverse &amp; re-post</button></div>
      <div class="cf-hint">The original voucher stays. A reversal and a corrected voucher are added, and the correction is logged and proposed to the knowledge base.</div>
      <div class="cf-err" hidden></div></form>` : "";
  return `<div class="section why-acct"><div class="section-title">Why this account</div>
    <div class="card acct-card"><div class="acct-head"><span class="acct big">${esc(acct)}</span><b>${esc(ACCOUNTS[acct] || (c && c.account_name) || "")}</b><span class="pill ${tone}" style="margin-left:auto">${esc(label)}</span></div>
      <div class="acct-why">${esc(c ? c.rationale : "No classification recorded; showing the model's suggested account.")}</div>
      ${c && c.overridden_model_account ? `<div class="note">${ICON.info}<div>Model suggested <span class="acct">${esc(c.overridden_model_account)}</span> ${esc(ACCOUNTS[c.overridden_model_account] || "")}. ${c.source === "correction" ? "An accountant's correction" : "The activity policy"} overrode it.</div></div>` : ""}
      ${rates ? `<div class="acct-vat muted">Expected VAT for this activity: <b>${fmtRates(rates)}</b> · document says <b>${Math.round(+e.vat_rate * 100)}%</b></div>` : ""}
      ${vatNote}${kbCard}${candList}${form}</div></div>`;
}

function renderDrawer() {
  const d = docById(drawerDoc);
  if (!d) return closeDrawer();
  const keep = $("#drawer .correct-form input[name=reason]");
  const draft = keep && keep.closest("form").dataset.correct === d.id ? { reason: keep.value, account: $("#drawer .correct-form select").value, focus: document.activeElement === keep } : null;
  const scroll = $("#drawer .drawer-body") ? $("#drawer .drawer-body").scrollTop : 0;
  const e = d.extraction;
  const vs = S.vouchers.filter((x) => x.document_id === d.id).sort((a, b) => a.number - b.number);
  const liveVoucher = vs.filter((x) => x.status !== "reversed" && !x.reverses_id).pop();
  const anoms = S.anomalies.filter((a) => a.document_id === d.id);
  const url = d.source === "light_csv" ? null : api.fileUrl(d);
  const isImg = /\.(png|jpe?g|gif|webp)$/i.test(d.filename);
  // Chrome's PDF viewer will not load inside a sandboxed frame; the server only serves application/pdf after
  // verifying the magic bytes, and everything else stays sandboxed.
  const isPdf = /\.pdf$/i.test(d.filename);
  const preview = url
    ? isImg ? `<img class="preview" src="${url}" alt="${esc(d.filename)}">`
      : `<iframe class="preview" ${isPdf ? "" : 'sandbox=""'} referrerpolicy="no-referrer" src="${url}" title="${esc(d.filename)}"></iframe>`
    : paper(d);
  const F = (k, val, flag) => `<div class="field ${flag ? "flag" : ""}"><div class="k"><span>${k}</span></div><div class="v">${val ?? "—"}</div></div>`;
  const tone = toneOf(d);
  const ibanFlag = anoms.some((a) => a.kind === "iban_change");
  const vouchers = vs.length ? vs.map(voucherCard).join("")
    : `<div class="section"><div class="section-title">Voucher</div><div class="empty" style="padding:22px">${d.status === "quarantined" ? "Never posted. Quarantined documents cannot reach the ledger." : d.status === "needs_review" ? "Held for accountant review." : "Waiting for extraction…"}</div></div>`;
  const fix = corrected[d.id];
  const fixOrig = fix && fix.reversal && S.vouchers.find((x) => x.id === fix.reversal.reverses_id);
  const fixHow = !fix ? "" : fix.reversal
    ? `A${fix.reversal.number} reverses A${fixOrig ? fixOrig.number : "?"}; A${fix.corrected.number} re-posts it. Nothing was edited.`
    : `The unposted proposal was superseded by A${fix.corrected.number}${fix.corrected.status === "proposed" ? ", which still awaits approval" : ""}. Nothing was edited.`;
  const fixCard = fix ? `<div class="card fixcard">${ICON.check}<div><b>Corrected to ${esc(fix.correction.account)} ${esc(ACCOUNTS[fix.correction.account] || "")}</b>
      <div>${fixHow}</div>
      ${fix.kb_proposal ? `<div class="muted">Knowledge-base proposal: <b>${esc(fix.kb_proposal.vendor)}</b> → ${esc(fix.kb_proposal.account)}${fix.kb_proposal.activity ? ` (${esc(fix.kb_proposal.activity)})` : ""} · ${esc(fix.kb_proposal.status)}</div>` : ""}</div></div>` : "";
  const evs = AUD.byId[d.id];
  const extEv = evs && evs.find((x) => x.action === "doc.extracted");
  const trail = evs && evs.length
    ? `<div class="aud-list compact">${auditRows(evs, false)}</div>`
    : `<div class="muted" style="padding:6px 0">${evs ? "No audit events for this document yet." : AUD.verify === null && !MOCK ? "Audit log unavailable on this server." : "Loading audit events…"}</div>`;
  const model = (extEv && extEv.data.model) || (liveVoucher && liveVoucher.model) || "—";
  const prompt = (extEv && extEv.data.prompt_version) || (liveVoucher && liveVoucher.prompt_version) || "—";

  $("#drawer").innerHTML = `<div class="drawer-head"><div class="src" style="${tone === "red" ? "color:var(--red)" : ""}">${d.status === "quarantined" ? ICON.shieldX : d.source === "email" ? ICON.mail : d.source === "light_csv" ? ICON.csv : ICON.upload}</div>
    <div style="min-width:0"><div style="font-weight:600">${esc(e ? e.vendor : d.filename)}</div><div class="mono muted">${esc(d.filename)}</div></div>
    ${e ? whyPill("doc", d.id, docConf(d)) : ""}<span class="pill ${tone || "violet"}">${esc(d.status.replace("_", " "))}</span>
    <button class="btn sm ghost x" data-act="close">${ICON.x}</button></div>
    <div class="drawer-body"><div><div class="section-title">Source document</div>${preview}</div>
    <div>
      ${anoms.map((a) => `<div class="card anom ${a.severity}" style="padding:12px;grid-template-columns:30px 1fr"><div class="ic">${a.kind === "injection" ? ICON.shieldX : ICON.alert}</div><div><div class="title">${esc(a.title)}</div><div class="expl">${esc(a.explanation)}</div><div class="rule">Deterministic rule: <code>${esc(a.rule)}</code></div></div></div>`).join("")}
      ${e ? `<div class="section"><div class="section-title">Extracted by Claude ${ICON.sparkle.replace("<svg", '<svg width="12" height="12"')}</div><div class="fields">
        ${F("Vendor", esc(e.vendor))}${F("Org no.", esc(e.vendor_org_nr || "—"))}
        ${F("Type", esc(e.doc_type.replace("_", " ")))}${F("Invoice no.", esc(e.invoice_number || "—"))}
        ${F("Date", esc(e.date))}${F("Activity", esc(e.activity || "—"))}
        ${F("Net", money(e.net, e.currency))}${F(`VAT ${Math.round(+e.vat_rate * 100)}%`, money(e.vat, e.currency))}
        ${F("Gross", `<b>${money(e.gross, e.currency)}</b>`)}${F("Bankgiro / IBAN", esc(e.bankgiro || e.iban || "—"), ibanFlag)}
      </div>${e.injection_suspected ? `<div class="rule" style="color:var(--red)">${ICON.shieldX.replace("<svg", '<svg width="13" height="13"')} Model flagged embedded instructions. Output discarded.</div>` : ""}</div>` : ""}
      ${d.status === "quarantined" ? "" : whyAccount(d, liveVoucher)}
      ${e ? `<div class="section why-conf"><div class="section-title">Why ${pct(docConf(d))}? · confidence breakdown</div>${confPanel(e.confidence_detail, e.confidence)}</div>` : ""}
      ${reviewCard(d, vs)}${fixCard}${vouchers}
      <div class="section aud-sec"><div class="section-title">Audit trail ${chainBadge(false)}</div>${trail}
        <dl class="kv"><dt>SHA-256</dt><dd title="${esc(d.sha256)}">${esc(d.sha256.slice(0, 12))}…${esc(d.sha256.slice(-6))}</dd>
          <dt>Model</dt><dd>${esc(model)}</dd><dt>Prompt version</dt><dd>${esc(prompt)}</dd>
          <dt>Document id</dt><dd>${esc(d.id)}</dd></dl>
      </div>
    </div></div>`;
  $("#drawer .drawer-body").scrollTop = scroll;
  if (draft) {
    const f = $("#drawer .correct-form");
    if (f) {
      f.reason.value = draft.reason;
      f.account.value = draft.account;
      if (draft.focus) f.reason.focus();
    }
  }
}

function reviewCard(d, vs) {
  if (d.status !== "needs_review" && d.status !== "quarantined") return "";
  const proposed = vs.find((x) => x.status === "proposed" && !x.bank_tx_id);
  const canApprove = d.status === "needs_review" && proposed;
  return `<form class="card review-form" data-review="${esc(d.id)}"><div class="sub-title">Accountant review</div>
    <div class="muted">${esc(d.note || "Held for review.")}</div>
    <div class="cf-row"><input name="reason" placeholder="Note (required to reject)" aria-label="Review note" autocomplete="off">
      ${canApprove ? `<button class="btn sm primary" type="submit" value="approve">Approve &amp; post A${proposed.number}</button>` : ""}
      <button class="btn sm" type="submit" value="reject">Reject</button></div>
    <div class="cf-err" hidden></div></form>`;
}

async function submitReview(form, verdict) {
  const id = form.dataset.review;
  const err = $(".cf-err", form);
  const note = form.reason.value.trim();
  err.hidden = true;
  if (verdict === "reject" && !note) {
    err.textContent = "Add a reason. It goes into the audit log.";
    err.hidden = false;
    return form.reason.focus();
  }
  try {
    const res = await api.review(id, verdict, verdict === "reject" ? { reason: note, user: "accountant" } : { note, user: "accountant" });
    toast("green", verdict === "approve" ? `Posted A${res.voucher.number}` : "Document rejected", "Logged in the audit chain under your name.", ICON.chain);
    await refresh();
  } catch (x) {
    err.textContent = x.message;
    err.hidden = false;
  }
}

async function submitCorrection(form) {
  const id = form.dataset.correct;
  const err = $(".cf-err", form);
  const body = { account: form.account.value, reason: form.reason.value.trim(), user: "accountant" };
  err.hidden = true;
  if (!body.reason) {
    err.textContent = "Add a reason. It goes into the audit log.";
    err.hidden = false;
    return form.reason.focus();
  }
  const btn = $("button", form);
  btn.disabled = true;
  try {
    const res = await api.correct(id, body);
    corrected[id] = res;
    form.reason.value = "";
    loadKnowledge();
    const how = res.reversal ? `A${res.reversal.number} reverses, A${res.corrected.number} re-posts.` : res.corrected.status === "proposed" ? `A${res.corrected.number} proposed; approve it to post.` : `A${res.corrected.number} posted.`;
    toast("green", `Re-booked to ${body.account}`, `${how} Logged in the audit chain.`, ICON.chain);
    await refresh();
  } catch (x) {
    err.textContent = x.message;
    err.hidden = false;
  } finally {
    btn.disabled = false;
  }
}

const money = (x, cur) => (cur && cur !== "SEK" ? `${nf.format(+x)} ${esc(cur)}` : kr(x));

function paper(d) {
  const e = d.extraction;
  if (!e) return `<div class="empty">Rendering preview…</div>`;
  const inj = d.status === "quarantined" && d.note ? `<div class="inj">${esc(d.note)}</div>` : "";
  return `<div class="paper"><h3>${esc(e.vendor)}</h3><div class="meta">${esc(e.vendor_org_nr ? "Org no. " + e.vendor_org_nr : "")} ${e.invoice_number ? "· No. " + esc(e.invoice_number) : ""}<br>${esc(e.date)}${e.due_date ? " · Due " + esc(e.due_date) : ""}</div>
    <div class="r"><span>${esc(e.description || "")}</span><span>${money(e.net, e.currency)}</span></div>
    <div class="r"><span>VAT ${Math.round(+e.vat_rate * 100)}%</span><span>${money(e.vat, e.currency)}</span></div>
    <div class="r t"><span>Total due</span><span>${money(e.gross, e.currency)}</span></div>
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
        <button class="pill ${confTone(m.confidence)} why" data-why="match:${esc(m.id)}" title="Show the checks behind this score">${pct(m.confidence)}${n > 1 ? ` · 1:${n}` : ""} ?</button></div>
      <div>${docs.map(docSide).join("")}</div>
      <div class="actions">${m.approved ? `<span class="pill green">${ICON.check}Approved</span>` : `<button class="btn sm green" data-approve="${esc(m.id)}">${ICON.check}Approve</button>`}<span class="method">${esc(m.method)}</span></div></div>`;
  }).join("");
  return `<div class="view-head"><div><h1>Reconciliation</h1><div class="sub">${S.matches.length} matches · ${S.matches.filter((m) => m.approved).length} approved · ${unmatched.length} bank lines without a document · click a score to see its checks</div></div>
    <div class="btn-row"><button class="btn primary" data-act="approveAll" ${ready ? "" : "disabled"}>${ICON.check}Approve all ≥95% (${ready})</button></div></div>
    <div class="recon"><div style="display:grid;grid-template-columns:1fr 150px 1fr 130px;padding:0 14px" class="muted"><span>${ICON.bank.replace("<svg", '<svg width="13" height="13" style="vertical-align:-2px"')} Bank (SEB business account)</span><span></span><span>Documents</span><span></span></div>
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
  const VB = [["05", "Taxable sales"], ["10", "Output VAT 25%"], ["48", "Deductible input VAT"], ["49", "VAT to pay or reclaim"]];
  const journal = S.vouchers.slice().sort((a, b) => a.number - b.number).map((v) => {
    const tot = v.lines.reduce((s, l) => s + +l.debit, 0);
    return `<tr ${v.document_id ? `data-doc="${esc(v.document_id)}" style="cursor:pointer"` : ""} class="${v.status === "reversed" ? "is-reversed" : ""}"><td class="mono">A${v.number}</td><td class="mono">${esc(v.date)}</td><td>${esc(v.description)}</td>
      <td><div class="journal-lines">${v.lines.map((l) => `<span><span class="acct">${esc(l.account)}</span><span class="num" style="text-align:right">${+l.debit ? nf.format(+l.debit) : ""}</span><span class="num muted" style="text-align:right">${+l.credit ? nf.format(+l.credit) : ""}</span></span>`).join("")}</div></td>
      <td class="num">${kr(tot)}</td><td><span class="pill ${v.status === "posted" ? "green" : v.status === "reversed" ? "red" : "violet"}">${esc(v.status)}</span></td></tr>`;
  }).join("");
  return `<div class="view-head"><div><h1>Books</h1><div class="sub">${esc(S.client.name)} · Fiscal year 2026 · BAS 2024 chart · amounts in SEK</div></div></div>
    <div class="card export-card"><div class="logo" style="width:44px;height:44px">${ICON.download.replace("<svg", '<svg width="20" height="20" style="color:#fff"')}</div>
      <div class="txt"><b>Export SIE4 → Fortnox / Visma</b><div class="muted">${S.vouchers.length} vouchers · balanced · ready to import into any Swedish ledger</div></div>
      <div class="btn-row"><button class="btn ghost" data-act="siePreview">${ICON.eye}SIE4 preview</button><button class="btn primary xl" data-act="sieExport">${ICON.download}Export SIE4</button></div></div>
    <div class="grid2">
      <div class="card"><h2>Profit &amp; loss</h2><table><tbody>
        <tr><td><span class="acct">3xxx</span></td><td>Net revenue</td><td class="num">${kr(pnl.revenue)}</td></tr>${rowsOf(pnl.expenses)}
        <tr class="total"><td></td><td>Total expenses</td><td class="num">${kr(-expTotal)}</td></tr></tbody></table>
        <div style="display:flex;justify-content:space-between;align-items:end;margin-top:14px"><span class="muted">Net profit</span><span class="result" style="color:${+pnl.result >= 0 ? "var(--green)" : "var(--red)"}">${kr(pnl.result)}</span></div></div>
      <div class="card"><h2>Balance sheet</h2><table><thead><tr><th colspan="3">Assets</th></tr></thead><tbody>${rowsOf(bs.assets)}
        <tr class="total"><td></td><td>Total assets</td><td class="num">${kr(sum(bs.assets))}</td></tr></tbody></table>
        <table style="margin-top:12px"><thead><tr><th colspan="3">Equity &amp; liabilities</th></tr></thead><tbody>${rowsOf(bs.liabilities_equity)}
        <tr class="total"><td></td><td>Total equity &amp; liabilities</td><td class="num">${kr(sum(bs.liabilities_equity))}</td></tr></tbody></table></div>
    </div>
    <div class="card" style="margin-top:16px"><h2>VAT return · Swedish Tax Agency boxes</h2><div class="vat-boxes">${VB.map(([k, l]) => `<div class="vbox ${k === "49" ? "pay" : ""}"><span class="code">Box ${k}</span><div class="lbl">${l}</div><div class="v">${kr(vat[k])}</div></div>`).join("")}</div></div>
    <div class="card" style="margin-top:16px"><h2>Voucher journal</h2><div class="table-wrap"><table><thead><tr><th>No.</th><th>Date</th><th>Text</th><th>Account · Debit · Credit</th><th class="num">Amount</th><th>Status</th></tr></thead><tbody>${journal || '<tr><td colspan="6" class="muted">No vouchers yet.</td></tr>'}</tbody></table></div></div>`;
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
    ["Explainable confidence", "Each score is a weighted mean of named checks. The model's own score is one check; failed arithmetic or an illegal VAT rate caps it."],
    ["Deterministic posting + balance check", "Vouchers are built by code from BAS rules. Debit must equal credit or nothing is written."],
    ["Sender allowlist & quarantine", "Unknown senders and suspected injections are isolated before they touch the books."],
    ["Hash-chained audit log", "Every step is an append-only event whose hash covers the one before. Corrections are reversals, never edits."],
    ["EU hosting (roadmap)", "Runs locally today. Production: EU-hosted Postgres + EU-region inference, 7-year retention under the Swedish Bookkeeping Act."],
  ];
  const th = threats();
  const injLeaked = S.documents.filter((d) => d.status === "quarantined").some((d) => S.vouchers.some((v) => v.document_id === d.id && v.status === "posted"));
  const hero = th.length ? `<div class="trust-hero"><span class="r">${th.length} threat${th.length > 1 ? "s" : ""} caught</span> · <span class="g">${injLeaked ? "check ledger" : "0 injections reached the ledger"}</span></div>` : "";
  return `${hero}<div class="view-head"><div><h1>Trust Center</h1><div class="sub">${S.anomalies.length} findings · ${sev.high.length} high severity · every flag comes from a deterministic rule, not a model's opinion</div></div>
    <div class="btn-row"><button class="chain-btn" data-go="audit">${chainBadge(true)}</button></div></div>
    <div class="trust-grid">
      <div>${injCard}${groups || '<div class="empty">No anomalies.</div>'}</div>
      <div class="card security"><h2 style="display:flex;align-items:center;gap:8px">${ICON.lock.replace("<svg", '<svg width="16" height="16"')}Security model</h2>
        <ul>${SEC.map(([t, s]) => `<li><span class="ck">${ICON.check}</span><div><b>${t}</b><span>${s}</span></div></li>`).join("")}</ul></div>
    </div>`;
}

// ---------- 5. audit ----------
const AUDIT_FILTERS = [
  ["all", "All", () => true], ["document", "Documents", (e) => e.entity === "document" && !e.action.startsWith("kb.")],
  ["kb", "Knowledge base", (e) => e.action.startsWith("kb.")], ["voucher", "Vouchers", (e) => e.entity === "voucher" || e.action.startsWith("ledger.")],
  ["user", "People", (e) => e.actor.startsWith("user:")],
];
function viewAudit() {
  const all = AUD.all;
  const [, , fn] = AUDIT_FILTERS.find(([k]) => k === AUD.filter) || AUDIT_FILTERS[0];
  const shown = all ? all.filter(fn) : null;
  const byActor = all ? ["system", "model:", "user:"].map((p) => all.filter((e) => e.actor.startsWith(p)).length) : [0, 0, 0];
  return `<div class="view-head"><div><h1>Audit trail</h1><div class="sub">Append-only and hash-chained: each event's hash covers the previous one, so editing any row breaks every hash after it.</div></div>
    <div class="btn-row"><button class="btn ghost" data-act="verify">${ICON.reset}Re-verify</button></div></div>
    <div class="chain-hero card">${chainBadge(true)}
      <div class="chain-facts"><div><b class="tnum">${byActor[0]}</b>system</div><div><b class="tnum">${byActor[1]}</b>model</div><div><b class="tnum">${byActor[2]}</b>people</div>
        <div class="mono muted chain-head" title="${esc((AUD.verify && AUD.verify.head) || "")}">head ${esc(((AUD.verify && AUD.verify.head) || "").slice(0, 24))}…</div></div></div>
    <div class="inbox-toolbar"><div class="filters">${AUDIT_FILTERS.map(([k, l, f]) => `<button class="btn sm ${AUD.filter === k ? "" : "ghost"}" data-afilter="${k}">${l} <span class="muted">${all ? all.filter(f).length : 0}</span></button>`).join("")}</div>
      <div class="muted">newest first · hover a hash for the full value</div></div>
    <div class="card aud-list audit-list">${shown ? auditRows(shown.slice(-400), true) || '<div class="empty">No events.</div>' : `<div class="empty">${AUD.verify === null ? "Audit log unavailable on this server." : "Loading…"}</div>`}</div>`;
}

// ---------- 6. knowledge ----------
function viewKnowledge() {
  if (!KB) return `<div class="view-head"><div><h1>Knowledge base</h1><div class="sub">Not available from this server yet.</div></div></div>`;
  const acts = Array.isArray(KB.activities) ? KB.activities : Object.entries(KB.activities || {}).map(([id, a]) => ({ id, ...a }));
  const st = KB.stats || {};
  const hits = st.hits || 0, misses = st.misses || 0;
  const vendorsBy = {};
  (KB.vendors || []).forEach((v) => (vendorsBy[v.activity] = vendorsBy[v.activity] || []).push(v));
  const props = KB.proposals || [];
  return `<div class="view-head"><div><h1>Knowledge base</h1><div class="sub">Curated, editable data, not code. Looked up on every ingest by org no., email domain and vendor name as a prior for the posting policy; in live mode, entries found in the email body and PDF/text content are also passed to Claude as context · ${esc(KB.version || "")}</div></div></div>
    <div class="hero kb-hero"><div class="kpi"><div class="v">${(KB.vendors || []).length}</div><div class="k">Vendors</div></div>
      <div class="kpi"><div class="v">${acts.length}</div><div class="k">Activities</div></div>
      <div class="kpi green"><div class="v">${hits + misses ? Math.round((100 * hits) / (hits + misses)) : 0}%</div><div class="k">Hit rate · ${hits} hits / ${misses} misses</div></div>
      <div class="kpi ${props.length ? "grad" : ""}"><div class="v">${props.length}</div><div class="k">Proposals from corrections</div></div></div>
    ${props.length ? `<div class="card" style="margin-bottom:16px"><h2>Proposed entries</h2><table><thead><tr><th>Vendor</th><th>Account</th><th>Activity</th><th>Aliases</th><th>Status</th></tr></thead><tbody>${props.map((p) =>
      `<tr><td>${esc(p.vendor)}</td><td><span class="acct">${esc(p.account)}</span> ${esc(ACCOUNTS[p.account] || "")}</td><td>${esc(p.activity || "—")}</td><td class="muted">${esc((p.aliases || []).join(", "))}</td><td><span class="pill amber">${esc(p.status)}</span></td></tr>`).join("")}</tbody></table></div>` : ""}
    <div class="card"><h2>Activities → account and VAT</h2><div class="table-wrap"><table><thead><tr><th>Activity</th><th>Account</th><th>Expected VAT</th><th>Vendors</th><th>What it covers</th></tr></thead><tbody>${acts.map((a) =>
      `<tr><td><b>${esc(a.label || a.id)}</b><div class="mono muted">${esc(a.id)}</div></td><td>${(a.accounts || []).map((x, i) => `<div><span class="acct">${esc(x)}</span> <span class="${i ? "muted" : ""}">${esc(ACCOUNTS[x] || "")}</span></div>`).join("")}</td>
        <td><span class="pill ${(a.vat_rates || []).length > 1 ? "amber" : ""}">${fmtRates(a.vat_rates)}</span></td>
        <td>${(vendorsBy[a.id] || []).map((v) => `<span class="vchip" title="${esc([...(v.aliases || []), ...(v.bank_patterns || []), ...(v.email_domains || [])].join(" · "))}">${esc(v.name)}${v.vat_rates && v.vat_rates.length ? ` <small>${fmtRates(v.vat_rates)}</small>` : ""}</span>`).join("") || '<span class="muted">—</span>'}</td>
        <td class="kb-desc">${esc(a.description || "")}${a.vat_note ? `<div class="muted">${esc(a.vat_note)}</div>` : ""}</td></tr>`).join("")}</tbody></table></div></div>`;
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
  if ($("#pop") && !e.target.closest("#pop,[data-why]")) closePop();
  const t = e.target.closest("[data-why],[data-go],[data-act],[data-filter],[data-afilter],[data-approve],[data-doc],[data-client],.doc");
  if (!t) { if (menuOpen) { menuOpen = false; renderTop(); } return; }
  if (t.dataset.act !== "menu" && menuOpen) menuOpen = false;
  if (t.dataset.why) { e.preventDefault(); return showWhy(t); }
  if (t.dataset.go) return go(t.dataset.go);
  if (t.dataset.client) { toast("amber", t.dataset.client, "Demo: only Lovelight Design AB is connected live."); return render(); }
  if (t.dataset.filter) { filter = t.dataset.filter; return render(); }
  if (t.dataset.afilter) { AUD.filter = t.dataset.afilter; return render(); }
  if (t.dataset.approve) { await api.approve(t.dataset.approve); toast("green", "Match approved", "Voucher posted to ledger"); return scheduleRefresh(); }
  if (t.dataset.doc) return openDrawer(t.dataset.doc);
  if (t.classList.contains("doc")) return openDrawer(t.dataset.id);
  switch (t.dataset.act) {
    case "menu": menuOpen = !menuOpen; return renderTop();
    case "replay": toast("green", "Replaying demo batch", "Documents incoming from email + Light", ICON.play); await api.replay(); return scheduleRefresh();
    case "reset": closeDrawer(); await api.reset(); seen.clear(); return scheduleRefresh();
    case "approveAll": await api.approveAll(); toast("green", "Approved all ≥95%", "Deterministic vouchers posted"); return scheduleRefresh();
    case "sieExport": if (!MOCK) window.open("/api/export/sie4", "_blank"); return siePreview();
    case "siePreview": return siePreview();
    case "verify": await loadAudit(); return toast(AUD.verify && AUD.verify.ok ? "green" : "red", AUD.verify && AUD.verify.ok ? "Chain verified" : "Chain check failed", AUD.verify ? `${typeof AUD.verify.events === "number" ? AUD.verify.events : (AUD.verify.events || []).length} events recomputed from genesis` : "Audit log unavailable", ICON.chain);
    case "closeModal": $("#modal").hidden = true; return;
    case "close": return closeDrawer();
  }
});
document.addEventListener("submit", (e) => {
  const r = e.target.closest("form[data-review]");
  if (r) {
    e.preventDefault();
    return submitReview(r, (e.submitter && e.submitter.value) || "approve");
  }
  const f = e.target.closest("form[data-correct]");
  if (!f) return;
  e.preventDefault();
  submitCorrection(f);
});
$("#scrim").addEventListener("click", closeDrawer);
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") e.currentTarget.hidden = true; });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { if ($("#pop")) return closePop(); closeDrawer(); $("#modal").hidden = true; } });
window.addEventListener("resize", closePop);
$("#view").addEventListener("scroll", closePop);

function connect() {
  const liveEl = $(".live");
  if (MOCK) { window.LovelightMock.on(onEvent); return; }
  const es = new EventSource("/api/events");
  es.onopen = () => liveEl.classList.remove("off");
  es.onerror = () => liveEl.classList.add("off");
  es.onmessage = (m) => onEvent(JSON.parse(m.data));
}

connect();
loadKnowledge();
const ready = refresh().then(() => { if (QS.get("doc")) openDrawer(QS.get("doc")); });

window.Lovelight = {
  ready, api, ICON, MOCK, go, refresh, toast, openDrawer, closeDrawer, siePreview, showWhy, closePop, loadAudit,
  state: () => S,
  view: () => view,
};
