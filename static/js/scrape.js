/* ═══════════════════════════════════════════
   Taspen Sentiment Platform – Scrape & Analisis page
══════════════════════════════════════════ */

window.renderScrape = function () {
  const el = document.getElementById('page-content');
  el.innerHTML = `
<!-- Page header -->
<div class="section-card mb-5 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
  <div>
    <div class="flex items-center gap-2 mb-2 flex-wrap">
      <span class="chip chip-primary"><span class="material-symbols-outlined text-[13px]">auto_awesome</span> Multi-platform</span>
      <span class="chip chip-gold"><span class="material-symbols-outlined text-[13px]">bolt</span> 6 Sumber Data</span>
      <span class="chip chip-ok"><span class="material-symbols-outlined text-[13px]">link</span> Scrape per URL</span>
    </div>
    <h1 class="text-[22px] font-extrabold text-on-surface tracking-tight">Scrape &amp; Analisis</h1>
    <p class="text-[13px] text-on-surface-variant mt-1 max-w-2xl">
      Kumpulkan komentar dari Instagram, YouTube, Web, Play Store, Facebook, dan TikTok.
      Analisis sentimen otomatis dengan model ID-Sentiment.
    </p>
  </div>
</div>

<!-- Mode tabs -->
<div id="scrape-tabs" class="section-card mb-4">
  <div class="tabs-bar">
    <button class="tab-btn active" data-tab="keyword">Scrape per Keyword</button>
    <button class="tab-btn" data-tab="url">Scrape per URL Postingan</button>
  </div>

  <!-- TAB: Keyword -->
  <div class="tab-panel active" data-panel="keyword">

    <!-- Credentials -->
    <details class="expander mb-4">
      <summary><span class="material-symbols-outlined text-[18px] text-on-surface-variant">key</span> Kredensial Sumber Data</summary>
      <div class="expander-body" id="cred-status-wrap">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
          <!-- Instagram -->
          <div class="source-tile flex-col items-start gap-3">
            <div class="flex items-center gap-3 w-full">
              <span class="material-symbols-outlined text-[20px] text-primary">photo_camera</span>
              <div class="flex-1">
                <div class="text-[13px] font-bold text-on-surface">Instagram</div>
                <div class="text-[11px] text-on-surface-variant">session_id · username+password</div>
              </div>
              <span id="ig-status-dot" class="source-dot-off"></span>
            </div>
            <input class="form-input" id="ig-sid" placeholder="session_id dari browser" type="text"/>
            <input class="form-input" id="ig-user" placeholder="username" type="text"/>
            <input class="form-input" id="ig-pass" placeholder="password" type="password"/>
            <button class="btn btn-secondary btn-sm btn-full" onclick="saveIG()">Simpan IG</button>
          </div>
          <!-- Facebook -->
          <div class="source-tile flex-col items-start gap-3">
            <div class="flex items-center gap-3 w-full">
              <span class="material-symbols-outlined text-[20px] text-primary">thumb_up</span>
              <div class="flex-1">
                <div class="text-[13px] font-bold text-on-surface">Facebook</div>
                <div class="text-[11px] text-on-surface-variant">cookie c_user+xs</div>
              </div>
              <span id="fb-status-dot" class="source-dot-off"></span>
            </div>
            <textarea class="form-textarea" id="fb-cookie" placeholder="Paste cookie (c_user=...; xs=...)"></textarea>
            <button class="btn btn-secondary btn-sm btn-full" onclick="saveFB()">Simpan Facebook</button>
            <div style="height:8px"></div>
            <div class="flex items-center gap-3 w-full">
              <span class="material-symbols-outlined text-[20px] text-primary">music_note</span>
              <div class="flex-1">
                <div class="text-[13px] font-bold text-on-surface">TikTok</div>
                <div class="text-[11px] text-on-surface-variant">ms_token</div>
              </div>
              <span id="tt-status-dot" class="source-dot-off"></span>
            </div>
            <input class="form-input" id="tt-token" placeholder="ms_token" type="password"/>
            <button class="btn btn-secondary btn-sm btn-full" onclick="saveTT()">Simpan TikTok</button>
          </div>
          <!-- Auto sources -->
          <div class="flex flex-col gap-3">
            <div class="source-tile">
              <span class="material-symbols-outlined text-[20px] text-primary">play_circle</span>
              <div><div class="text-[13px] font-bold">YouTube</div><div class="text-[11px] text-on-surface-variant">tanpa login</div></div>
              <span class="source-dot-ok ml-auto"></span>
            </div>
            <div class="source-tile">
              <span class="material-symbols-outlined text-[20px] text-primary">language</span>
              <div><div class="text-[13px] font-bold">Web Berita</div><div class="text-[11px] text-on-surface-variant">tanpa login</div></div>
              <span class="source-dot-ok ml-auto"></span>
            </div>
            <div class="source-tile">
              <span class="material-symbols-outlined text-[20px] text-primary">shop</span>
              <div><div class="text-[13px] font-bold">Play Store</div><div class="text-[11px] text-on-surface-variant">tanpa login</div></div>
              <span class="source-dot-ok ml-auto"></span>
            </div>
          </div>
        </div>
      </div>
    </details>

    <!-- Config -->
    <details class="expander mb-4" open>
      <summary><span class="material-symbols-outlined text-[18px] text-on-surface-variant">settings</span> Konfigurasi Scrape</summary>
      <div class="expander-body">
        <!-- Quick pills -->
        <div class="flex flex-wrap gap-2 mb-3">
          <span class="text-[12px] font-semibold text-on-surface-variant mt-1">Contoh:</span>
          ${['taspen','pensiun','asn','taspen life'].map(k =>
            `<button class="chip chip-primary cursor-pointer hover:opacity-80" onclick="setKw('${k}')">${k}</button>`
          ).join('')}
        </div>
        <input class="form-input mb-4" id="kw-input" placeholder="keyword, nama brand, atau topik" value="taspen"/>

        <div class="text-[11px] font-extrabold uppercase tracking-widest text-outline mb-3">Sumber &amp; jumlah target</div>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4">
          ${[
            {k:'ig',  ic:'photo_camera', label:'Instagram', max:300, def:0},
            {k:'yt',  ic:'play_circle',  label:'YouTube',   max:300, def:30},
            {k:'web', ic:'language',     label:'Web',       max:30,  def:8},
            {k:'ps',  ic:'shop',         label:'Play Store',max:300, def:30},
            {k:'fb',  ic:'thumb_up',     label:'Facebook',  max:300, def:0},
            {k:'tt',  ic:'music_note',   label:'TikTok',    max:300, def:0},
          ].map(s => `
            <div class="source-tile flex-col items-start gap-2 p-3" id="tile-${s.k}">
              <div class="flex items-center gap-2 w-full">
                <span class="material-symbols-outlined text-[18px] text-primary">${s.ic}</span>
                <span class="text-[12px] font-bold flex-1">${s.label}</span>
                <label class="toggle">
                  <input type="checkbox" id="on-${s.k}" ${s.def > 0 ? 'checked' : ''} onchange="toggleSrc('${s.k}')"/>
                  <span class="toggle-slider"></span>
                </label>
              </div>
              <input class="form-input text-[12px]" id="n-${s.k}" type="number" min="0" max="${s.max}" value="${s.def}" ${s.def === 0 ? 'disabled' : ''}
                style="padding:5px 8px;"/>
            </div>
          `).join('')}
        </div>

        <div class="flex gap-6 mb-2">
          <label class="toggle-wrap">
            <label class="toggle"><input type="checkbox" id="do-bot" checked/><span class="toggle-slider"></span></label>
            <span class="toggle-label">Deteksi bot/spam</span>
          </label>
          <label class="toggle-wrap">
            <label class="toggle"><input type="checkbox" id="do-ent" checked/><span class="toggle-slider"></span></label>
            <span class="toggle-label">Tag entity mentions</span>
          </label>
        </div>
        <p class="text-[11px] text-on-surface-variant mb-4">Target jumlah = batas atas. Hasil bisa lebih sedikit (duplikat dibuang, komentar pendek difilter, stok komentar platform habis) — capaian per sumber selalu dilaporkan di log &amp; KPI.</p>

        <button class="btn btn-primary btn-full" id="btn-run-kw" onclick="runScrapeKeyword()">
          <span class="material-symbols-outlined text-[18px]">radar</span> Mulai Scrape + Analisis
        </button>
      </div>
    </details>
  </div><!-- /tab keyword -->

  <!-- TAB: URL -->
  <div class="tab-panel" data-panel="url">
    <div class="section-card mb-4">
      <div class="section-title"><span class="material-symbols-outlined">link</span> Scrape per Postingan</div>
      <p class="section-desc">Input URL postingan → pilih platform → tentukan jumlah komentar</p>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
        <div class="sm:col-span-1">
          <label class="form-label">URL / ID Postingan</label>
          <input class="form-input" id="url-input" placeholder="https://www.instagram.com/p/... atau https://youtu.be/..."/>
        </div>
        <div>
          <label class="form-label">Platform</label>
          <select class="form-select" id="url-src">
            <option value="instagram">Instagram</option>
            <option value="youtube" selected>YouTube</option>
            <option value="web">Web / Artikel</option>
            <option value="facebook">Facebook</option>
            <option value="tiktok">TikTok</option>
            <option value="playstore">Play Store (URL app)</option>
          </select>
        </div>
        <div>
          <label class="form-label">Jumlah komentar</label>
          <input class="form-input" id="url-limit" type="number" min="10" max="500" value="100"/>
        </div>
      </div>
      <div class="flex gap-6 mb-4">
        <label class="toggle-wrap">
          <label class="toggle"><input type="checkbox" id="url-do-bot"/><span class="toggle-slider"></span></label>
          <span class="toggle-label">Deteksi bot/spam</span>
        </label>
        <label class="toggle-wrap">
          <label class="toggle"><input type="checkbox" id="url-do-ent"/><span class="toggle-slider"></span></label>
          <span class="toggle-label">Tag entity mentions</span>
        </label>
      </div>
      <button class="btn btn-primary btn-full" id="btn-run-url" onclick="runScrapeUrl()">
        <span class="material-symbols-outlined text-[18px]">link</span> Scrape URL + Analisis
      </button>
    </div>
  </div><!-- /tab url -->
</div><!-- /scrape-tabs -->

<!-- Log riwayat (persisten, retensi 6 jam) -->
<div id="scrape-progress" class="section-card mb-4" style="display:none">
  <div class="flex items-center gap-3 mb-3">
    <div class="spinner"></div>
    <span class="text-[13px] font-semibold text-on-surface" id="progress-label">Scraping...</span>
  </div>
  <div class="progress-wrap mb-3"><div class="progress-bar" id="progress-bar" style="width:10%"></div></div>
</div>

<!-- Riwayat scrape (dipertahankan 6 jam) -->
<div class="section-card mb-4">
  <div class="flex items-center justify-between mb-3">
    <div class="section-title mb-0"><span class="material-symbols-outlined">history</span> Riwayat Scrape <span class="text-[11px] font-normal text-on-surface-variant ml-1">· retensi 6 jam</span></div>
    <button class="btn btn-secondary btn-sm" onclick="refreshHistory()"><span class="material-symbols-outlined text-[16px]">refresh</span> Muat ulang</button>
  </div>
  <div style="overflow-x:auto;">
    <table class="data-table">
      <thead><tr><th>Waktu (UTC)</th><th>Mode</th><th>Keyword / URL</th><th>Baris</th><th>Aksi</th></tr></thead>
      <tbody id="history-body"><tr><td colspan="5" class="text-on-surface-variant">memuat...</td></tr></tbody>
    </table>
  </div>
</div>

<!-- Log live -->
<div class="section-card mb-4">
  <div class="section-title"><span class="material-symbols-outlined">terminal</span> Log Scrape</div>
  <div class="terminal">
    <div class="terminal-bar">
      <span style="width:9px;height:9px;border-radius:50%;background:#ff5f56;display:inline-block;"></span>
      <span style="width:9px;height:9px;border-radius:50%;background:#ffbd2e;display:inline-block;"></span>
      <span style="width:9px;height:9px;border-radius:50%;background:#27c93f;display:inline-block;"></span>
      <span class="terminal-title ml-2">scrape log</span>
    </div>
    <pre class="terminal-body" id="log-body">Belum ada scrape. Riwayat log tersimpan di tabel Riwayat Scrape di atas.</pre>
  </div>
</div>

<!-- Results -->
<div id="scrape-results"></div>
`;

  initTabs('scrape-tabs');
  loadSessionStatus();
  refreshHistory();
};

// ── Credential status ──────────────────────────────
async function loadSessionStatus() {
  try {
    const d = await apiGet('/api/sessions/status');
    setStatusDot('ig-status-dot', d.instagram === 'ok');
    setStatusDot('fb-status-dot', d.facebook  === 'ok');
    setStatusDot('tt-status-dot', d.tiktok    === 'ok');
  } catch (_) {}
}

function setStatusDot(id, ok) {
  const el = document.getElementById(id);
  if (el) el.className = ok ? 'source-dot-ok' : 'source-dot-off';
}

// ── Session saves ──────────────────────────────────
async function saveIG() {
  const body = {
    session_id: document.getElementById('ig-sid')?.value?.trim() || '',
    username:   document.getElementById('ig-user')?.value?.trim() || '',
    password:   document.getElementById('ig-pass')?.value || '',
  };
  try {
    const d = await apiPost('/api/sessions/instagram', body);
    d.ok ? toast('IG tersimpan', 'ok') : toast(d.error || 'Gagal', 'err');
    if (d.ok) setStatusDot('ig-status-dot', true);
  } catch (e) { toast(String(e), 'err'); }
}

async function saveFB() {
  const cookie = document.getElementById('fb-cookie')?.value?.trim();
  if (!cookie) return toast('Cookie kosong', 'warn');
  try {
    const d = await apiPost('/api/sessions/facebook', { cookie });
    d.ok ? toast('Facebook tersimpan', 'ok') : toast(d.error || 'Gagal', 'err');
    if (d.ok) setStatusDot('fb-status-dot', true);
  } catch (e) { toast(String(e), 'err'); }
}

async function saveTT() {
  const ms_token = document.getElementById('tt-token')?.value?.trim();
  if (!ms_token) return toast('ms_token kosong', 'warn');
  try {
    const d = await apiPost('/api/sessions/tiktok', { ms_token });
    d.ok ? toast('TikTok tersimpan', 'ok') : toast(d.error || 'Gagal', 'err');
    if (d.ok) setStatusDot('tt-status-dot', true);
  } catch (e) { toast(String(e), 'err'); }
}

// ── Keyword pill ───────────────────────────────────
function setKw(kw) {
  const el = document.getElementById('kw-input');
  if (el) el.value = kw;
}

function toggleSrc(k) {
  const checked = document.getElementById(`on-${k}`)?.checked;
  const inp     = document.getElementById(`n-${k}`);
  if (inp) inp.disabled = !checked;
}

// ── Run Keyword scrape ────────────────────────────
async function runScrapeKeyword() {
  const kw = document.getElementById('kw-input')?.value?.trim();
  if (!kw) return toast('Keyword kosong', 'warn');

  const body = {
    keyword:     kw,
    ig:          parseInt(document.getElementById('n-ig')?.value || 0),
    yt:          parseInt(document.getElementById('n-yt')?.value || 0),
    web:         parseInt(document.getElementById('n-web')?.value || 0),
    playstore:   parseInt(document.getElementById('n-ps')?.value || 0),
    facebook:    parseInt(document.getElementById('n-fb')?.value || 0),
    tiktok:      parseInt(document.getElementById('n-tt')?.value || 0),
    detect_bots: document.getElementById('do-bot')?.checked || false,
    tag_entities:document.getElementById('do-ent')?.checked || false,
  };

  const total = body.ig + body.yt + body.web + body.playstore + body.facebook + body.tiktok;
  if (total === 0) return toast('Aktifkan minimal satu sumber', 'warn');

  startProgress('Scraping + Analisis Sentimen...');
  setStatus('Scraping...', true);

  try {
    const d = await apiPost('/api/scrape/keyword', body);
    if (!d.ok) {
      // Show error + any available logs
      if (d.logs?.length) showLogs(d.logs);
      throw new Error(d.error || 'Tidak ada data');
    }
    App.state.rows = d.rows;
    App.state.meta = d.meta;
    App.state.logs = d.logs;
    App.state.aiSummary = null;
    App.state.aiReco    = null;
    App.state.chatHistory = [];
    setStatus(`${fmt(d.rows.length)} data`, true);
    updateSidebar();
    showLogs(d.logs);
    renderResults();
    toast(`Selesai: ${fmt(d.rows.length)} data`, 'ok');
  } catch (e) {
    toast(String(e), 'err');
    setStatus('Error', false);
  } finally {
    stopProgress();
  }
}

// ── Run URL scrape ─────────────────────────────────
async function runScrapeUrl() {
  const url   = document.getElementById('url-input')?.value?.trim();
  const src   = document.getElementById('url-src')?.value;
  const limit = parseInt(document.getElementById('url-limit')?.value || 100);
  if (!url) return toast('URL kosong', 'warn');

  const body = {
    url, source: src, limit,
    detect_bots: document.getElementById('url-do-bot')?.checked || false,
    tag_entities:document.getElementById('url-do-ent')?.checked || false,
  };

  startProgress(`Scraping ${SOURCE_LABEL[src] || src}...`);
  setStatus('Scraping...', true);

  try {
    const d = await apiPost('/api/scrape/url', body);
    if (!d.ok) throw new Error(d.error || 'Gagal');
    App.state.rows = d.rows;
    App.state.meta = d.meta;
    App.state.logs = d.logs;
    App.state.aiSummary = null;
    App.state.aiReco    = null;
    App.state.chatHistory = [];
    setStatus(`${fmt(d.rows.length)} data`, true);
    updateSidebar();
    showLogs(d.logs);
    renderResults();
    toast(`Selesai: ${fmt(d.rows.length)} data`, 'ok');
  } catch (e) {
    toast(String(e), 'err');
    setStatus('Error', false);
  } finally {
    stopProgress();
  }
}

// ── Progress helpers ───────────────────────────────
let _progTimer;
function startProgress(label) {
  document.getElementById('scrape-progress').style.display = '';
  document.getElementById('progress-label').textContent    = label;
  document.getElementById('progress-bar').style.width      = '5%';
  document.getElementById('log-body').textContent          = '';
  let w = 5;
  _progTimer = setInterval(() => {
    w = Math.min(w + 2, 85);
    document.getElementById('progress-bar').style.width = w + '%';
  }, 800);
}

function stopProgress() {
  clearInterval(_progTimer);
  document.getElementById('progress-bar').style.width = '100%';
  setTimeout(() => { document.getElementById('scrape-progress').style.display = 'none'; }, 600);
}

function showLogs(logs) {
  const el = document.getElementById('log-body');
  if (el) el.textContent = (logs && logs.length) ? logs.join('\n') : '(tidak ada log)';
}

// ── Riwayat scrape (retensi 6 jam) ─────────────────
async function refreshHistory() {
  const tbody = document.getElementById('history-body');
  if (!tbody) return;
  try {
    const d = await apiGet('/api/history');
    if (!d.items || !d.items.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-on-surface-variant">Belum ada riwayat. Jalankan scrape — hasil + log tersimpan di sini selama 6 jam.</td></tr>';
      return;
    }
    tbody.innerHTML = d.items.map(h => {
      const t = new Date(h.created).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' });
      const label = esc((h.label || '').slice(0, 60));
      return `<tr>
        <td class="mono text-[12px]">${t}</td>
        <td><span class="chip ${h.kind === 'url' ? 'chip-info' : 'chip-primary'}">${h.kind}</span></td>
        <td class="text-cell" title="${label}">${label}</td>
        <td class="mono">${fmt(h.row_count)}</td>
        <td class="whitespace-nowrap">
          <button class="btn btn-secondary btn-sm" onclick="loadHistory('${h.id}')"><span class="material-symbols-outlined text-[14px]">visibility</span> Buka</button>
          <a class="btn btn-secondary btn-sm" href="/api/history/${h.id}/csv"><span class="material-symbols-outlined text-[14px]">download</span> CSV</a>
        </td>
      </tr>`;
    }).join('');
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-red-600">Gagal memuat riwayat: ${esc(String(e))}</td></tr>`;
  }
}

async function loadHistory(hid) {
  try {
    const d = await apiGet(`/api/history/${hid}`);
    if (!d.ok) throw new Error(d.error || 'Gagal');
    App.state.rows = d.rows;
    App.state.meta = d.meta || {};
    App.state.logs = d.logs || [];
    showLogs(d.logs);
    renderResults();
    toast(`Riwayat ${d.label || hid} dimuat (${fmt(d.rows.length)} baris)`, 'ok');
    document.getElementById('scrape-results')?.scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    toast(String(e), 'err');
  }
}

// ── Render results ─────────────────────────────────
function renderResults() {
  const rows = App.state.rows;
  const el   = document.getElementById('scrape-results');
  if (!rows.length || !el) return;

  const st  = computeStats(rows);
  const meta= App.state.meta;

  // Capaian per sumber (target vs hasil)
  const targets = meta.targets || {};
  const perSrc = {};
  for (const r of rows) perSrc[r.source] = (perSrc[r.source] || 0) + 1;
  const tgtKeys = Object.keys(targets);
  const capaians = tgtKeys.length
    ? tgtKeys.map(k => {
        const key = ({'Instagram':'instagram','YouTube':'youtube','Web':'web','Play Store':'playstore','Facebook':'facebook','TikTok':'tiktok'})[k] || k.toLowerCase();
        const got = perSrc[key] || 0;
        const ok  = got >= (targets[k] * 0.9);
        return `<span class="chip ${ok ? 'chip-ok' : 'chip-warn'}" style="${ok ? '' : 'background:#fef3c7;color:#92400e'}">${esc(k)} ${got}/${targets[k]}</span>`;
      }).join(' ')
    : '';

  // Bot & entity availability
  const botRows  = rows.filter(r => r.is_bot_suspect !== undefined && r.is_bot_suspect !== null);
  const botCount = botRows.filter(r => r.is_bot_suspect === true || r.is_bot_suspect === 'True').length;
  const entRows  = rows.filter(r => r.entity_mentions && String(r.entity_mentions).trim());
  const showTrust = botRows.length > 0 || entRows.length > 0;

  el.innerHTML = `
<!-- KPI row -->
<div class="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-3">
  ${kpiCard('Total Teks Dianalisis', fmt(st.total), `${[...new Set(rows.map(r=>r.source))].length} sumber · ${esc(meta.keyword||'')}`, 'analytics', '#005d97')}
  ${kpiCard('Net Sentiment Score', (st.skor>=0?'+':'') + st.skor.toFixed(1), `P ${st.cnt.Positif} · Neg ${st.cnt.Negatif} dari ${st.total}`, 'sentiment_very_satisfied', st.skor >= 0 ? '#1e9e6a' : '#d64545')}
  ${kpiCard('Rasio Positif', st.pct.Positif.toFixed(1)+'%', fmt(st.cnt.Positif)+' komentar', 'thumb_up', '#1e9e6a')}
  ${kpiCard('Negatif Alert', st.pct.Negatif.toFixed(1)+'%', fmt(st.cnt.Negatif)+' komentar', 'notification_important', '#d64545')}
</div>
${capaians ? `<div class="flex flex-wrap items-center gap-2 mb-4"><span class="text-[11px] font-bold uppercase tracking-wider text-outline">Capaian:</span>${capaians}<span class="text-[11px] text-on-surface-variant ml-1">target = batas atas</span></div>` : ''}
${showTrust ? renderTrustSection(rows, botRows.length, botCount, entRows.length) : ''}

<!-- Distribusi + top comments -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-5">
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined text-[18px]">pie_chart</span> Distribusi Sentimen</div>
    <div id="chart-donut-scrape" class="plotly-chart"></div>
    <div class="flex justify-center gap-6 mt-3">
      ${Object.entries(st.pct).map(([k,v])=>`
        <div class="flex items-center gap-2">
          <span style="width:10px;height:10px;border-radius:50%;background:${LABEL_COLOR[k]};display:inline-block;"></span>
          <span class="text-[12px] font-semibold">${esc(k)}</span>
          <span class="text-[12px] text-on-surface-variant">${v.toFixed(1)}%</span>
        </div>`).join('')}
    </div>
  </div>
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined text-[18px]">chat</span> Contoh Komentar</div>
    ${renderCommentSamples(rows)}
  </div>
</div>

<!-- Data table -->
<details class="expander mb-4">
  <summary><span class="material-symbols-outlined text-[18px] text-on-surface-variant">table_view</span> Data + Filter</summary>
  <div class="expander-body">
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
      <div>
        <label class="form-label">Sentimen</label>
        <select class="form-select" id="flt-label" onchange="filterTable()">
          <option value="">Semua</option>
          <option>Positif</option><option>Netral</option><option>Negatif</option>
        </select>
      </div>
      <div>
        <label class="form-label">Sumber</label>
        <select class="form-select" id="flt-source" onchange="filterTable()">
          <option value="">Semua</option>
          ${[...new Set(rows.map(r=>r.source))].map(s=>`<option value="${s}">${SOURCE_LABEL[s]||s}</option>`).join('')}
        </select>
      </div>
      <div>
        <label class="form-label">Cari teks</label>
        <input class="form-input" id="flt-search" placeholder="keyword..." oninput="filterTable()"/>
      </div>
      <div class="flex items-end">
        <button class="btn btn-secondary btn-sm btn-full" onclick="downloadCSV()">
          <span class="material-symbols-outlined text-[16px]">download</span> Unduh CSV
        </button>
      </div>
    </div>
    <div style="overflow-x:auto;">
      <table class="data-table" id="results-table">
        <thead><tr>
          <th>Sentimen</th><th>Skor</th><th>Sumber</th><th>Kategori</th>
          <th>Teks</th><th>Author</th><th>Likes</th><th>Autentisitas</th><th>Entitas</th>
        </tr></thead>
        <tbody id="results-tbody"></tbody>
      </table>
    </div>
    <div class="text-[12px] text-on-surface-variant mt-2" id="table-count"></div>
  </div>
</details>
`;

  // Render donut chart
  renderDonut('chart-donut-scrape', st);
  filterTable();
}

// ── Trust section: bot detection + entity mentions ─
function renderTrustSection(rows, botTotal, botCount, entCount) {
  // Chart 1: autentisitas per sumber (stacked)
  const srcMap = {};
  for (const r of rows) {
    if (r.is_bot_suspect === undefined || r.is_bot_suspect === null) continue;
    if (!srcMap[r.source]) srcMap[r.source] = { asli: 0, bot: 0 };
    const isBot = r.is_bot_suspect === true || r.is_bot_suspect === 'True';
    srcMap[r.source][isBot ? 'bot' : 'asli']++;
  }
  const srcs = Object.keys(srcMap);
  // Chart 2: entity terbanyak
  const entCnt = {};
  for (const r of rows) {
    if (!r.entity_mentions) continue;
    try {
      const m = typeof r.entity_mentions === 'string' ? JSON.parse(r.entity_mentions) : r.entity_mentions;
      for (const cat of Object.keys(m || {})) {
        (m[cat] || []).forEach(e => { const k = `${e}`; entCnt[k] = (entCnt[k] || 0) + 1; });
      }
    } catch (_) {}
  }
  const entTop = Object.entries(entCnt).sort((a, b) => b[1] - a[1]).slice(0, 10);

  let charts = '';
  if (srcs.length) {
    charts += `<div><div class="text-[11px] font-bold text-on-surface-variant mb-1">Asli vs dugaan bot per sumber</div><div id="chart-trust-bot" class="plotly-chart"></div></div>`;
  }
  if (entTop.length) {
    charts += `<div><div class="text-[11px] font-bold text-on-surface-variant mb-1">Pihak/entitas ikut disebut</div><div id="chart-trust-ent" class="plotly-chart"></div></div>`;
  }

  setTimeout(() => {
    if (srcs.length) {
      Plotly.newPlot('chart-trust-bot', [
        { type: 'bar', name: 'Asli', x: srcs.map(s => SOURCE_LABEL[s] || s), y: srcs.map(s => srcMap[s].asli), marker: { color: '#1e9e6a' } },
        { type: 'bar', name: 'Dugaan bot', x: srcs.map(s => SOURCE_LABEL[s] || s), y: srcs.map(s => srcMap[s].bot), marker: { color: '#d64545' } },
      ], {
        barmode: 'stack', height: 220, margin: { t: 5, b: 30, l: 30, r: 5 },
        legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
        yaxis: { gridcolor: '#e3eef7' },
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      }, { displayModeBar: false });
    }
    if (entTop.length) {
      Plotly.newPlot('chart-trust-ent', [{
        type: 'bar', orientation: 'h', x: entTop.map(e => e[1]), y: entTop.map(e => e[0]), marker: { color: '#004a7c' },
      }], {
        height: Math.max(200, entTop.length * 28), showlegend: false,
        margin: { t: 5, b: 5, l: 5, r: 5 }, yaxis: { autorange: 'reversed' },
        paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      }, { displayModeBar: false });
    }
  }, 50);

  return `
<!-- Trust: bot + entity -->
<div class="section-card mb-5">
  <div class="flex items-center justify-between mb-1">
    <div class="section-title mb-0"><span class="material-symbols-outlined">verified_user</span> Autentisitas &amp; Pihak Terkait</div>
    <div class="flex gap-2">
      ${botTotal ? `<span class="chip ${botCount ? 'chip-neg' : 'chip-ok'}">${botCount}/${botTotal} dugaan bot</span>` : ''}
      ${entCount ? `<span class="chip chip-info">${entCount} baris menyebut pihak lain</span>` : ''}
    </div>
  </div>
  <p class="section-desc">Deteksi bot = heuristic (pola username, teks spam, duplikat). Entity = pihak/organisasi ikut disebut dalam komentar. Keduanya aktif via toggle di Konfigurasi Scrape.</p>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">${charts}</div>
</div>`;
}

// ── Render results (helper position: after renderResults) ──
function renderResults_end() {}

// ── KPI card HTML ──────────────────────────────────
function kpiCard(label, value, sub, icon, color) {
  return `
<div class="kpi-card">
  <div class="flex items-start justify-between">
    <span class="kpi-label">${esc(label)}</span>
    <div class="kpi-icon" style="background:${color}18;">
      <span class="material-symbols-outlined text-[20px]" style="color:${color};">${icon}</span>
    </div>
  </div>
  <div class="kpi-value" style="color:${color};">${value}</div>
  <div class="kpi-sub">${esc(sub)}</div>
</div>`;
}

// ── Donut chart (Plotly) ───────────────────────────
function renderDonut(id, st) {
  const labels = ['Positif','Netral','Negatif'];
  const values = labels.map(l => st.cnt[l] || 0);
  const colors = labels.map(l => LABEL_COLOR[l]);
  Plotly.newPlot(id, [{
    type: 'pie', labels, values,
    marker: { colors },
    hole: 0.55,
    textinfo: 'label+percent',
    sort: false,
    direction: 'clockwise',
  }], {
    margin: { t:5, b:5, l:5, r:5 },
    height: 220,
    showlegend: false,
    paper_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false });
}

// ── Comment samples ────────────────────────────────
function renderCommentSamples(rows) {
  const out = [];
  for (const lab of ['Positif','Negatif','Netral']) {
    const subs = rows.filter(r=>r.label===lab).sort((a,b)=>(b.likes||0)-(a.likes||0)).slice(0,1);
    if (!subs.length) continue;
    const r = subs[0];
    out.push(`
<div class="comment-card ${lab==='Positif'?'pos':lab==='Negatif'?'neg':'neu'}">
  <div class="comment-meta">${esc(SOURCE_LABEL[r.source]||r.source)} · ${esc(r.kategori||'?')} · likes ${r.likes||0}</div>
  <div class="comment-text">${esc(String(r.text||'').slice(0,200))}</div>
  <div class="mt-1">${sentimentBadge(lab)}</div>
</div>`);
  }
  return out.join('') || '<div class="text-[12px] text-on-surface-variant">Tidak ada data.</div>';
}

// ── Table filter ───────────────────────────────────
function filterTable() {
  const labF  = document.getElementById('flt-label')?.value  || '';
  const srcF  = document.getElementById('flt-source')?.value || '';
  const search= (document.getElementById('flt-search')?.value || '').toLowerCase();
  const tbody = document.getElementById('results-tbody');
  if (!tbody) return;

  const rows = App.state.rows.filter(r => {
    if (labF   && r.label  !== labF)  return false;
    if (srcF   && r.source !== srcF)  return false;
    if (search && !String(r.text||'').toLowerCase().includes(search)) return false;
    return true;
  }).slice(0, 200);

  tbody.innerHTML = rows.map(r => {
    const isBot = r.is_bot_suspect === true || r.is_bot_suspect === 'True';
    const botCell = (r.is_bot_suspect === undefined || r.is_bot_suspect === null)
      ? '<td class="text-on-surface-variant">—</td>'
      : `<td><span class="chip ${isBot ? 'chip-neg' : 'chip-ok'}" title="${esc(r.bot_reasons || '')}">${isBot ? 'bot?' : 'asli'}</span></td>`;
    const entCell = r.entity_categories
      ? `<td class="text-cell" title="${esc(r.entity_mentions || '')}">${esc(r.entity_categories)}</td>`
      : '<td class="text-on-surface-variant">—</td>';
    return `
<tr>
  <td>${sentimentBadge(r.label)}</td>
  <td><span class="mono text-[12px]">${(r.score||0).toFixed(3)}</span></td>
  <td>${esc(SOURCE_LABEL[r.source]||r.source)}</td>
  <td>${esc(r.kategori||'?')}</td>
  <td class="text-cell" title="${esc(r.text||'')}">${esc(String(r.text||'').slice(0,80))}</td>
  <td>${esc(r.author||'')}</td>
  <td>${r.likes||0}</td>
  ${botCell}
  ${entCell}
</tr>`;
  }).join('');

  const countEl = document.getElementById('table-count');
  if (countEl) countEl.textContent = `${rows.length} dari ${App.state.rows.length} data`;
}

// ── CSV download ───────────────────────────────────
function downloadCSV() {
  const rows = App.state.rows;
  if (!rows.length) return toast('Tidak ada data', 'warn');
  const cols = ['source','label','score','kategori','text','author','date','likes','rating','is_bot_suspect','bot_reasons','entity_categories','entity_mentions','url'];
  const csv  = [cols.join(','), ...rows.map(r =>
    cols.map(c => JSON.stringify(String(r[c]??''))).join(',')
  )].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = `sentiment_${App.state.meta.keyword||'hasil'}.csv`;
  a.click();
}
