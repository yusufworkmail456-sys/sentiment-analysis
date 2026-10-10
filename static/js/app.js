/* ═══════════════════════════════════════════════════
   Taspen Sentiment Platform – App state, router, shared utilities
══════════════════════════════════════════════════ */

// ── Global state ──────────────────────────────────
window.App = {
  state: {
    rows:     [],    // sentiment result rows
    meta:     {},    // {keyword, stamp, durasi, mode}
    logs:     [],
    aiSummary: null,
    aiReco:    null,
    chatHistory: [],
  },
  currentPage: 'scrape',
};

// ── API helpers ────────────────────────────────────
async function apiPost(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  // Try to parse JSON even on error responses
  let data;
  try { data = await r.json(); } catch (_) { data = null; }
  if (!r.ok) {
    const msg = data?.error || data?.detail || `HTTP ${r.status}`;
    throw new Error(msg);
  }
  return data;
}

async function apiGet(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── Toast ──────────────────────────────────────────
function toast(msg, type = 'ok', ms = 3500) {
  const icons = { ok: 'check_circle', err: 'error', warn: 'warning' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="material-symbols-outlined text-[16px]">${icons[type] || 'info'}</span>${esc(msg)}`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), ms);
}

// ── String helpers ─────────────────────────────────
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function fmt(n) {
  return Number(n).toLocaleString('id-ID');
}

// ── Set status bar ─────────────────────────────────
function setStatus(text, ok = true) {
  const dot  = document.getElementById('status-dot');
  const span = document.getElementById('status-text');
  if (dot)  dot.className  = `w-2 h-2 rounded-full ${ok ? 'bg-tertiary-container animate-pulse' : 'bg-error'}`;
  if (span) span.textContent = text;
}

// ── Update sidebar meter ───────────────────────────
function updateSidebar() {
  const vol = App.state.rows.length;
  const kw  = App.state.meta.keyword || '—';
  const el  = document.getElementById('sb-volume');
  const kEl = document.getElementById('sb-keyword');
  const bar = document.getElementById('sb-meter');
  if (el)  el.textContent  = `${fmt(vol)} baris`;
  if (kEl) kEl.textContent = kw;
  if (bar) bar.style.width = Math.min(100, (vol / 1000) * 100) + '%';
}

// ── Router ─────────────────────────────────────────
const PAGES = {
  scrape:    { title: 'Scrape & Analisis',         desc: 'Kumpulkan data dari 6 platform lalu analisis sentimennya',            render: () => window.renderScrape?.() },
  dashboard: { title: 'Visualization Overview',    desc: 'Parameter bersama dari semua sumber dalam satu tampilan',             render: () => window.renderDashboard?.() },
  sources:   { title: 'Per-Source Breakdown',      desc: 'Visualisasi adaptif per sumber — menyesuaikan data yang tertangkap',  render: () => window.renderSourcesPage?.() },
  historical:{ title: 'Historical Analytics',      desc: 'Tren antar run scrape dari database — dedup global, data unik saja',  render: () => window.renderHistorical?.() },
  ai:        { title: 'AI Insight',                desc: 'Ringkasan eksekutif, rekomendasi, dan chatbot analisis',              render: () => window.renderAI?.() },
};

function navigate(page) {
  App.currentPage = page;
  // Update nav links
  document.querySelectorAll('.nav-link').forEach(a => {
    a.classList.toggle('active', a.dataset.page === page);
  });
  // Update topbar
  const p = PAGES[page];
  if (p) {
    document.getElementById('topbar-title').innerHTML = esc(p.title);
    document.getElementById('topbar-desc').innerHTML  = esc(p.desc);
  }
  // Render page
  const content = document.getElementById('page-content');
  content.innerHTML = '';
  p?.render?.();
}

// ── Plotly global layout: konsisten untuk semua chart ──
const PLOT_FONT = { family: "'Plus Jakarta Sans', sans-serif", size: 12, color: '#465e71' };
const PLOT_LAYOUT_BASE = {
  font: PLOT_FONT,
  margin: { t: 36, b: 52, l: 62, r: 26 },
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  legend: { orientation: 'h', yanchor: 'bottom', y: 1.04, xanchor: 'right', x: 1, font: { size: 11 } },
  xaxis: { automargin: true, gridcolor: '#e3eef7', zeroline: false, title: { font: { size: 11 } } },
  yaxis: { automargin: true, gridcolor: '#e3eef7', zeroline: false, title: { font: { size: 11 } } },
};

function plotLayout(overrides) {
  return Object.assign({}, PLOT_LAYOUT_BASE, overrides || {});
}

// Semua Plotly.newPlot memakai template di atas; layout spesifik tetap menang.
(function patchPlotly() {
  if (!window.Plotly) return;
  const _newPlot = Plotly.newPlot.bind(Plotly);
  Plotly.newPlot = function (id, data, layout, config) {
    const merged = plotLayout(layout || {});
    // automargin wajib supaya judul axis/label tidak terpotong di kolom sempit
    ['xaxis', 'yaxis', 'xaxis2', 'yaxis2'].forEach(ax => {
      if (merged[ax]) merged[ax].automargin = true;
    });
    return _newPlot(id, data, merged, Object.assign({ responsive: true, displayModeBar: false }, config || {}));
  };
})();

// Reflow chart saat tab berganti (chart yang dirender dalam panel tersembunyi
// bisa berukuran 0 dan tampak gepeng setelah tampil).
function resizePlots(container) {
  if (!window.Plotly) return;
  const scope = container || document;
  scope.querySelectorAll('.plotly-chart, .js-plotly-plot').forEach(el => {
    if (el.offsetParent !== null) {        // hanya elemen yang benar-benar terlihat
      try { Plotly.Plots.resize(el); } catch (_) {}
    }
  });
}
window.addEventListener('resize', () => resizePlots());

// ── Tabs helper ────────────────────────────────────
function initTabs(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      container.querySelector(`[data-panel="${target}"]`)?.classList.add('active');
      // reflow setelah panel tampil
      requestAnimationFrame(() => {
        setTimeout(() => resizePlots(container), 40);
      });
    });
  });
}

// ── Markdown-lite renderer ─────────────────────────
function renderMd(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^#{1,3} (.+)$/gm, '<h3 style="font-size:14px;font-weight:700;margin:10px 0 4px">$1</h3>')
    .replace(/^- (.+)$/gm, '<li style="margin:2px 0 2px 16px;font-size:13px;">$1</li>')
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/`(.+?)`/g, '<code style="background:#eef4f9;padding:1px 5px;border-radius:4px;font-size:12px;font-family:monospace">$1</code>');
}

// ── Sentiment color helpers ────────────────────────
const LABEL_COLOR = { 'Positif': '#1e9e6a', 'Netral': '#6b8299', 'Negatif': '#d64545' };  // Taspen
const LABEL_BG    = { 'Positif': '#a8e6c9', 'Netral': '#d9e7f2', 'Negatif': '#f9dede' };
const LABEL_TEXT  = { 'Positif': '#08351f', 'Netral': '#465e71', 'Negatif': '#8f1d1d' };
const SOURCE_LABEL = {
  instagram: 'Instagram', youtube: 'YouTube', web: 'Web berita',
  facebook: 'Facebook', tiktok: 'TikTok', playstore: 'Play Store',
};

function sentimentBadge(label) {
  const bg   = LABEL_BG[label]   || '#e3eef7';
  const color= LABEL_TEXT[label] || '#465e71';
  return `<span style="background:${bg};color:${color};padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700;">${esc(label)}</span>`;
}

// ── Stats helpers ──────────────────────────────────
function computeStats(rows) {
  const total = rows.length;
  if (!total) return null;
  const cnt = { Positif: 0, Netral: 0, Negatif: 0 };
  for (const r of rows) cnt[r.label] = (cnt[r.label] || 0) + 1;
  const pct = {};
  for (const k of Object.keys(cnt)) pct[k] = total ? (cnt[k] / total * 100) : 0;
  const skor = pct.Positif - pct.Negatif;
  const gss  = (cnt.Positif + 0.5 * cnt.Netral) / total * 100;
  return { total, cnt, pct, skor, gss };
}

// ── Nav helper (usable from inline onclick) ─────────
function navTo(page) { navigate(page); }

// ── Boot ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Nav click handlers
  document.querySelectorAll('.nav-link').forEach(a => {
    a.addEventListener('click', e => { e.preventDefault(); navigate(a.dataset.page); });
  });
  navigate('scrape');
  // Model AI info di sidebar
  apiGet('/api/model/info').then(d => {
    const el = document.getElementById('engine-model');
    if (el && d.ok) el.textContent = d.llm_model;
  }).catch(() => {});
  // Versi aplikasi di brand sidebar
  apiGet('/api/app/info').then(d => {
    const el = document.getElementById('sb-version');
    if (el && d.ok) el.textContent = 'v' + d.version;
  }).catch(() => {});
});
