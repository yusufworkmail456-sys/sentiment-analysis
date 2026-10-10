/* ═══════════════════════════════════════════
   Sentix AI – Scrape & Analisis page
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
            {k:'ig',  ic:'photo_camera', label:'Instagram', max:300, def:60},
            {k:'yt',  ic:'play_circle',  label:'YouTube',   max:300, def:60},
            {k:'web', ic:'language',     label:'Web',       max:30,  def:8},
            {k:'ps',  ic:'shop',         label:'Play Store',max:300, def:60},
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

        <div class="flex gap-6 mb-4">
          <label class="toggle-wrap">
            <label class="toggle"><input type="checkbox" id="do-bot"/><span class="toggle-slider"></span></label>
            <span class="toggle-label">Deteksi bot/spam</span>
          </label>
          <label class="toggle-wrap">
            <label class="toggle"><input type="checkbox" id="do-ent"/><span class="toggle-slider"></span></label>
            <span class="toggle-label">Tag entity mentions</span>
          </label>
        </div>

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
            <option value="playstore">Play Store (App ID)</option>
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

<!-- Progress / log -->
<div id="scrape-progress" style="display:none" class="section-card mb-4">
  <div class="flex items-center gap-3 mb-3">
    <div class="spinner"></div>
    <span class="text-[13px] font-semibold text-on-surface" id="progress-label">Scraping...</span>
  </div>
  <div class="progress-wrap mb-3"><div class="progress-bar" id="progress-bar" style="width:10%"></div></div>
  <div class="terminal">
    <div class="terminal-bar">
      <span style="width:9px;height:9px;border-radius:50%;background:#ff5f56;display:inline-block;"></span>
      <span style="width:9px;height:9px;border-radius:50%;background:#ffbd2e;display:inline-block;"></span>
      <span style="width:9px;height:9px;border-radius:50%;background:#27c93f;display:inline-block;"></span>
      <span class="terminal-title ml-2">scrape log</span>
    </div>
    <pre class="terminal-body" id="log-body">menunggu...</pre>
  </div>
</div>

<!-- Results -->
<div id="scrape-results"></div>
`;

  initTabs('scrape-tabs');
  loadSessionStatus();
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
  if (el) el.textContent = (logs || []).join('\n');
}

// ── Render results ─────────────────────────────────
function renderResults() {
  const rows = App.state.rows;
  const el   = document.getElementById('scrape-results');
  if (!rows.length || !el) return;

  const st  = computeStats(rows);
  const meta= App.state.meta;

  el.innerHTML = `
<!-- KPI row -->
<div class="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-5">
  ${kpiCard('Total Teks Dianalisis', fmt(st.total), `${[...new Set(rows.map(r=>r.source))].length} sumber · ${esc(meta.keyword||'')}`, 'analytics', '#3525cd')}
  ${kpiCard('Net Sentiment Score', (st.skor>=0?'+':'') + st.skor.toFixed(1), `GSS ${st.gss.toFixed(1)}/100`, 'sentiment_very_satisfied', st.skor >= 0 ? '#006e4b' : '#ba1a1a')}
  ${kpiCard('Rasio Positif', st.pct.Positif.toFixed(1)+'%', fmt(st.cnt.Positif)+' komentar', 'thumb_up', '#006e4b')}
  ${kpiCard('Negatif Alert', st.pct.Negatif.toFixed(1)+'%', fmt(st.cnt.Negatif)+' komentar', 'notification_important', '#ba1a1a')}
</div>

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
          <th>Teks</th><th>Author</th><th>Likes</th>
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

  tbody.innerHTML = rows.map(r => `
<tr>
  <td>${sentimentBadge(r.label)}</td>
  <td><span class="mono text-[12px]">${(r.score||0).toFixed(3)}</span></td>
  <td>${esc(SOURCE_LABEL[r.source]||r.source)}</td>
  <td>${esc(r.kategori||'?')}</td>
  <td class="text-cell" title="${esc(r.text||'')}">${esc(String(r.text||'').slice(0,80))}</td>
  <td>${esc(r.author||'')}</td>
  <td>${r.likes||0}</td>
</tr>`).join('');

  const countEl = document.getElementById('table-count');
  if (countEl) countEl.textContent = `${rows.length} dari ${App.state.rows.length} data`;
}

// ── CSV download ───────────────────────────────────
function downloadCSV() {
  const rows = App.state.rows;
  if (!rows.length) return toast('Tidak ada data', 'warn');
  const cols = ['source','label','score','kategori','text','author','likes','url'];
  const csv  = [cols.join(','), ...rows.map(r =>
    cols.map(c => JSON.stringify(String(r[c]??''))).join(',')
  )].join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = `sentiment_${App.state.meta.keyword||'hasil'}.csv`;
  a.click();
}
