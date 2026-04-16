/* Kollekten-Automation PWA — Vanilla JS */
"use strict";

// ── Konfiguration ─────────────────────────────────────────────────────────────
const BASE = window.location.origin;

// ── Hilfsfunktionen ───────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const token = localStorage.getItem("api_token") || "";
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(BASE + path, { ...opts, headers });
  if (res.status === 401) {
    showToast("Nicht autorisiert — bitte Token in Einstellungen eintragen.");
    throw new Error("401");
  }
  return res.json();
}

function showToast(msg, ms = 2800) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), ms);
}

function eur(v) {
  return (typeof v === "number")
    ? v.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €"
    : v || "—";
}

// ── Tab-Navigation ─────────────────────────────────────────────────────────────
const pages = document.querySelectorAll(".page");
const navBtns = document.querySelectorAll("nav button[data-page]");

function showPage(id) {
  pages.forEach(p => p.classList.toggle("active", p.id === id));
  navBtns.forEach(b => b.classList.toggle("active", b.dataset.page === id));
  if (id === "page-uebersicht") loadUebersicht();
  if (id === "page-kollekten") loadKollekten();
}

navBtns.forEach(b => b.addEventListener("click", () => showPage(b.dataset.page)));

// ── Übersicht (Dashboard) ─────────────────────────────────────────────────────
const dot = document.getElementById("status-dot");

async function loadUebersicht() {
  try {
    const s = await apiFetch("/api/status");
    document.getElementById("gemeinde-name").textContent = s.gemeinde || "—";
    document.getElementById("last-run").textContent =
      s.last_run ? new Date(s.last_run).toLocaleString("de-DE") : "—";
    document.getElementById("last-processed").textContent = s.last_run_processed ?? "—";
    document.getElementById("last-errors").textContent = s.last_run_errors ?? "—";
    document.getElementById("version-lbl").textContent = s.version ? `v${s.version}` : "";
    setRunning(s.is_running);

    const month = new Date().getMonth() + 1;
    const year  = new Date().getFullYear();
    const sum = await apiFetch(`/api/kollekten/summary?month=${month}&year=${year}`);
    document.getElementById("sum-eigene").textContent    = sum.summe_eigene_fmt    || "—";
    document.getElementById("sum-weiter").textContent    = sum.summe_weiterleitung_fmt || "—";
    document.getElementById("sum-gesamt").textContent    = sum.summe_gesamt_fmt    || "—";
    document.getElementById("sum-count").textContent     = sum.count ?? "—";
  } catch (e) {
    if (e.message !== "401") {
      dot.className = "error";
      document.getElementById("gemeinde-name").textContent = "Verbindungsfehler";
    }
  }
}

function setRunning(running) {
  dot.className = running ? "run" : "ok";
  const btnRun = document.getElementById("btn-run");
  const btnDry = document.getElementById("btn-dry");
  if (btnRun) btnRun.disabled = running;
  if (btnDry) btnDry.disabled = running;
}

// Run-Buttons
document.getElementById("btn-run")?.addEventListener("click", () => startRun(false));
document.getElementById("btn-dry")?.addEventListener("click", () => startRun(true));

let _sse = null;

async function startRun(dry) {
  try {
    const res = await apiFetch(`/api/run?dry_run=${dry}`, { method: "POST" });
    if (!res.started) { showToast("Konnte nicht starten."); return; }
    setRunning(true);
    openLiveLog();
    showToast(dry ? "Vorschau läuft…" : "Verarbeitung gestartet…");
  } catch (e) {
    if (e.message !== "401") showToast("Fehler beim Starten.");
  }
}

function openLiveLog() {
  const box = document.getElementById("progress-box");
  box.innerHTML = "";
  box.classList.add("visible");

  if (_sse) _sse.close();
  const token = localStorage.getItem("api_token") || "";
  const url = BASE + "/api/run/live";
  _sse = new EventSource(url);

  _sse.onmessage = (e) => {
    if (!e.data || e.data === "{}") return;
    try {
      const d = JSON.parse(e.data);
      if (d.type === "progress") {
        const p = document.createElement("p");
        p.textContent = d.message;
        box.appendChild(p);
        box.scrollTop = box.scrollHeight;
      }
      if (d.type === "finished") {
        setRunning(false);
        showToast(`✓ ${d.processed} verarbeitet, ${d.errors} Fehler`);
        _sse.close(); _sse = null;
        loadUebersicht();
      }
      if (d.type === "error") {
        setRunning(false);
        showToast("Fehler: " + d.message, 5000);
        _sse.close(); _sse = null;
      }
    } catch (_) {}
  };

  _sse.onerror = () => { _sse?.close(); _sse = null; setRunning(false); };
}

// ── Kollekten-Liste ───────────────────────────────────────────────────────────
let _allEntries = [];

async function loadKollekten() {
  const month = document.getElementById("filter-month")?.value || "";
  const year  = document.getElementById("filter-year")?.value  || "";
  const warn  = document.getElementById("filter-warn")?.checked ? "true" : "false";
  const params = new URLSearchParams();
  if (month) params.set("month", month);
  if (year)  params.set("year", year);
  if (warn === "true") params.set("only_warnings", "true");

  try {
    const data = await apiFetch(`/api/kollekten?${params}`);
    _allEntries = data.entries || [];
    renderKollekten(_allEntries);
  } catch (e) { /* 401 already shown */ }
}

function renderKollekten(entries) {
  const tbody = document.getElementById("kollekten-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";
  if (!entries.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty">Keine Einträge gefunden.</td></tr>`;
    return;
  }
  for (const e of entries) {
    const isWeiter = e.typ && e.typ.includes("weiter");
    const chipCls = isWeiter ? "chip-weiter" : "chip-eigene";
    const chipTxt = e.typ_label || (isWeiter ? "→ Weiterleit." : "✓ Eigene");
    const warnCls = e.needs_review ? "warn-row" : "";
    const warnTxt = e.needs_review ? ' <span class="chip chip-warn">!</span>' : "";
    tbody.innerHTML += `
      <tr class="${warnCls}">
        <td>${e.datum}</td>
        <td><strong>${e.betrag_fmt}</strong></td>
        <td>${e.zweck || "—"}${warnTxt}</td>
        <td><span class="chip ${chipCls}">${chipTxt}</span></td>
        <td style="color:#999;font-size:11px">${e.aobj || ""}</td>
      </tr>`;
  }
}

// Filter-Events
["filter-month", "filter-year", "filter-warn"].forEach(id => {
  document.getElementById(id)?.addEventListener("change", loadKollekten);
});

// Monats-Dropdown befüllen
(function initMonthFilter() {
  const sel = document.getElementById("filter-month");
  if (!sel) return;
  const monate = ["Jan","Feb","Mär","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"];
  monate.forEach((m, i) => {
    const opt = document.createElement("option");
    opt.value = i + 1;
    opt.textContent = m;
    sel.appendChild(opt);
  });
  sel.value = new Date().getMonth() + 1;

  const ySel = document.getElementById("filter-year");
  if (ySel) {
    const y = new Date().getFullYear();
    for (let i = y; i >= y - 3; i--) {
      const opt = document.createElement("option");
      opt.value = i; opt.textContent = i;
      ySel.appendChild(opt);
    }
    ySel.value = y;
  }
})();

// ── Einstellungen (Token) ─────────────────────────────────────────────────────
document.getElementById("btn-save-token")?.addEventListener("click", () => {
  const token = document.getElementById("inp-token")?.value?.trim() || "";
  localStorage.setItem("api_token", token);
  showToast("Token gespeichert.");
});

(function initSettings() {
  const inp = document.getElementById("inp-token");
  if (inp) inp.value = localStorage.getItem("api_token") || "";
})();

// ── Service Worker registrieren ───────────────────────────────────────────────
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

// ── Init ──────────────────────────────────────────────────────────────────────
showPage("page-uebersicht");
