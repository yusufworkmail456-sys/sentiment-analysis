/* ═══════════════════════════════════════════
   Taspen Sentiment Platform – Dashboard page
══════════════════════════════════════════ */

window.renderDashboard = function () {
  const el = document.getElementById('page-content');

  if (!App.state.rows.length) {
    el.innerHTML = `
<div class="empty-state">
  <span class="material-symbols-outlined empty-state-icon">insights</span>
  <div class="empty-state-title">Belum ada data</div>
  <div class="empty-state-desc">Jalankan scraping di halaman Scrape &amp; Analisis dulu.</div>
</div>`;
    return;
  }

  const meta = App.state.meta;
  const st   = computeStats(App.state.rows);

  el.innerHTML = `
<!-- Page header -->
<div class="section-card mb-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
  <div>
    <div class="flex items-center gap-2 mb-2">
      <span class="chip chip-primary"><span class="material-symbols-outlined text-[13px]">insights</span> Overview</span>
      <span class="chip chip-ok"><span class="material-symbols-outlined text-[13px]">verified</span> ${fmt(st.total)} data</span>
    </div>
    <h1 class="text-[22px] font-extrabold text-on-surface tracking-tight">Visualization Overview</h1>
    <p class="text-[13px] text-on-surface-variant mt-1">Parameter yang sama dari semua sumber digabung dalam tampilan ini — breakdown per sumber ada di menu Per-Source Breakdown</p>
  </div>
  <div class="flex gap-2">
    <button class="btn btn-secondary" onclick="navTo('sources')">
      <span class="material-symbols-outlined text-[18px]">folder_data</span> Per-Source Breakdown
    </button>
    <button class="btn btn-primary" onclick="exportPDF()">
      <span class="material-symbols-outlined text-[18px]">picture_as_pdf</span> Export PDF
    </button>
  </div>
</div>

<!-- Time range + granularity bar -->
<div class="section-card mb-4 flex flex-col sm:flex-row sm:items-center gap-3" id="tr-section">
  <div class="flex items-center gap-2 flex-1">
    <span class="material-symbols-outlined text-[18px] text-primary">calendar_today</span>
    <span class="text-[12px] font-bold text-on-surface">Rentang waktu</span>
    <select class="form-select" id="tr-select" style="max-width:160px" onchange="renderTimeSection()">
      <option value="7">7 hari terakhir</option>
      <option value="30" selected>30 hari terakhir</option>
      <option value="90">90 hari terakhir</option>
      <option value="0">Semua waktu</option>
    </select>
  </div>
  <div class="flex items-center gap-2" id="tr-meta">
    <span class="text-[12px] text-on-surface-variant" id="tr-info">—</span>
  </div>
</div>

<!-- Sub-tabs -->
<div id="dash-tabs">
  <div class="tabs-bar">
    <button class="tab-btn active" data-tab="overview">Overview Gabungan</button>
    <button class="tab-btn" data-tab="per-source">Per-Source Ringkas</button>
  </div>

  <!-- Overview tab -->
  <div class="tab-panel active" data-panel="overview" id="panel-overview"></div>

  <!-- Per-source summary tab (links to dedicated page) -->
  <div class="tab-panel" data-panel="per-source" id="panel-per-source"></div>
</div>
`;

  initTabs('dash-tabs');
  renderOverview();

  // Per-source ringkas tab: arahkan ke halaman khusus
  document.querySelector('[data-tab="per-source"]').addEventListener('click', () => navTo('sources'));
};

// ── Shared time-range filter (time series + GSS trend) ──
function timeRangeDays() {
  const sel = document.getElementById('tr-select');
  return sel ? parseInt(sel.value || '30') : 30;
}

function filterRowsByRange(rows, days) {
  if (!days) return rows.filter(r => r.date && String(r.date).length > 8);  // all dated rows
  const cutoff = Date.now() - days * 86400000;
  return rows.filter(r => {
    const t = Date.parse(r.date);
    return !isNaN(t) && t >= cutoff;
  });
}

function renderTimeSection() {
  const rows = App.state.rows;
  const days = timeRangeDays();
  const sub  = filterRowsByRange(rows, days);
  const info = document.getElementById('tr-info');
  const dated = rows.filter(r => r.date && !isNaN(Date.parse(r.date)));
  if (info) {
    info.textContent = `${fmt(sub.length)} data dalam rentang · ${fmt(dated.length)}/${fmt(rows.length)} data punya tanggal valid`;
  }
  renderTimeSeries('chart-timeseries', sub, days);
  renderGSSTrend('chart-gss-trend', sub, days);
}

// ── Time series: stacked area volume per day ────────
function renderTimeSeries(id, rows, days) {
  const wrap = document.getElementById('timeseries-card');
  if (!wrap) return;
  if (rows.length < 3) {
    wrap.style.display = '';
    document.getElementById(id).innerHTML =
      `<div class="text-[12px] text-on-surface-variant p-4">Data bertanggal kurang (${rows.length}) — butuh ≥3 untuk time series. Sumber tanpa timestamp tidak bisa ditampilkan di tren.</div>`;
    return;
  }
  wrap.style.display = '';
  const dayMap = {};
  for (const r of rows) {
    const day = String(r.date).slice(0, 10);
    if (!dayMap[day]) dayMap[day] = { Positif: 0, Netral: 0, Negatif: 0 };
    dayMap[day][r.label] = (dayMap[day][r.label] || 0) + 1;
  }
  const days_list = Object.keys(dayMap).sort();
  const traces = ['Positif', 'Netral', 'Negatif'].map(lab => ({
    type: 'scatter', mode: 'lines', name: lab, stackgroup: 'one',
    x: days_list, y: days_list.map(d => dayMap[d][lab] || 0),
    line: { color: LABEL_COLOR[lab], width: 2 },
    hovertemplate: '%{x}: %{y} ' + lab + '<extra></extra>',
  }));
  Plotly.newPlot(id, traces, {
    height: 280, margin: { t: 10, b: 30, l: 40, r: 10 },
    hovermode: 'x unified',
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
    xaxis: { title: 'Tanggal' }, yaxis: { title: 'Volume per hari', gridcolor: '#e3eef7' },
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false });
}

// ── GSS trend per day (0-100 benchmark line at 50) ──
function renderGSSTrend(id, rows, days) {
  const wrap = document.getElementById('gss-trend-card');
  if (!wrap) return;
  if (rows.length < 3) { wrap.style.display = 'none'; return; }
  const dayMap = {};
  for (const r of rows) {
    const day = String(r.date).slice(0, 10);
    if (!dayMap[day]) dayMap[day] = { Positif: 0, Netral: 0, Negatif: 0 };
    dayMap[day][r.label] = (dayMap[day][r.label] || 0) + 1;
  }
  const days_list = Object.keys(dayMap).sort();
  const gss = days_list.map(d => {
    const v = dayMap[d];
    const tot = v.Positif + v.Netral + v.Negatif;
    return tot ? ((v.Positif + 0.5 * v.Netral) / tot * 100) : 50;
  });
  Plotly.newPlot(id, [{
    type: 'scatter', mode: 'lines+markers', name: 'GSS',
    x: days_list, y: gss,
    line: { color: '#005d97', width: 3 }, marker: { size: 6 },
    fill: 'tozeroy', fillcolor: 'rgba(0,93,151,0.08)',
    hovertemplate: '%{x}: GSS %{y:.1f}<extra></extra>',
  }], {
    height: 240, margin: { t: 10, b: 30, l: 40, r: 10 },
    legend: { showlegend: false },
    xaxis: { title: 'Tanggal' }, yaxis: { title: 'GSS (0-100)', range: [0, 100], gridcolor: '#e3eef7' },
    shapes: [{ type: 'line', x0: days_list[0], x1: days_list[days_list.length - 1],
               y0: 50, y1: 50, line: { color: '#6b8299', width: 1.5, dash: 'dot' } }],
    annotations: [{ x: days_list[0], y: 50, text: 'netral 50', showarrow: false,
                    yanchor: 'bottom', font: { size: 10, color: '#6b8299' } }],
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false });
}

// ═══════════════════════════════════════════
// OVERVIEW TAB
// ═══════════════════════════════════════════
function renderOverview() {
  const rows = App.state.rows;
  const meta = App.state.meta;
  const st   = computeStats(rows);
  const panel= document.getElementById('panel-overview');
  if (!panel || !st) return;

  // Alert badges for critical categories
  const catNeg = {};
  const catTot = {};
  for (const r of rows) {
    const cat = r.kategori || 'Lainnya';
    catTot[cat] = (catTot[cat] || 0) + 1;
    if (r.label === 'Negatif') catNeg[cat] = (catNeg[cat] || 0) + 1;
  }
  const critical = Object.entries(catNeg)
    .map(([cat, n]) => [cat, (n / catTot[cat] * 100)])
    .filter(([, pct]) => pct >= 50)
    .sort((a, b) => b[1] - a[1]);

  const alertsHtml = critical.length
    ? `<div class="alert-row mb-4">${critical.map(([cat, pct]) =>
        `<span class="alert-neg"><span class="material-symbols-outlined text-[13px]">warning</span> ${esc(cat)}: ${pct.toFixed(0)}% negatif</span>`
      ).join('')}</div>` : '';

  panel.innerHTML = `
${alertsHtml}
<!-- KPI -->
<div class="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-5">
  ${kpiCard('Total Dianalisis',    fmt(st.total),               `${[...new Set(rows.map(r=>r.source))].length} sumber`,    'analytics',              '#005d97')}
  ${kpiCard('Net Sentiment Score', `${st.skor>=0?'+':''}${st.skor.toFixed(1)}`, `GSS ${st.gss.toFixed(1)}/100`,  'sentiment_very_satisfied', st.skor>=0?'#1e9e6a':'#d64545')}
  ${kpiCard('Rasio Positif',       st.pct.Positif.toFixed(1)+'%',  `${fmt(st.cnt.Positif)} komentar`,      'thumb_up',                '#1e9e6a')}
  ${kpiCard('Negatif Alert',       st.pct.Negatif.toFixed(1)+'%',  `${fmt(st.cnt.Negatif)} komentar`,      'notification_important',  '#d64545')}
</div>

<!-- Row 1: Donut + Insights -->
<div class="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-4">
  <div class="lg:col-span-2 section-card">
    <div class="section-title"><span class="material-symbols-outlined">pie_chart</span> Distribusi Sentimen</div>
    <p class="section-desc">${fmt(st.total)} sample dianalisis</p>
    <div id="chart-donut-dash" class="plotly-chart"></div>
    <div class="flex justify-center gap-5 mt-3">
      ${['Positif','Netral','Negatif'].map(k=>`
        <div class="flex items-center gap-2">
          <span style="width:10px;height:10px;border-radius:50%;background:${LABEL_COLOR[k]};display:inline-block;"></span>
          <span class="text-[12px] font-semibold">${k}</span>
          <span class="text-[12px] text-on-surface-variant font-mono">${st.pct[k].toFixed(1)}%</span>
        </div>`).join('')}
    </div>
  </div>
  <div class="lg:col-span-3 section-card">
    <div class="section-title"><span class="material-symbols-outlined">speed</span> GSS Score &amp; Ringkasan</div>
    <div id="chart-gauge" class="plotly-chart"></div>
    <div id="insight-bullets" class="mt-3"></div>
  </div>
</div>

<!-- Row 2: Per source + ABSA -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">dashboard</span> Sentimen per Sumber</div>
    <div id="chart-per-source" class="plotly-chart"></div>
  </div>
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">category</span> ABSA per Kategori</div>
    <div id="chart-absa" class="plotly-chart"></div>
  </div>
</div>

<!-- Row 3: Channel scorecard -->
<div class="section-card mb-4">
  <div class="section-title"><span class="material-symbols-outlined">leaderboard</span> Channel Scorecard</div>
  <div style="overflow-x:auto;"><table class="data-table" id="scorecard-table">
    <thead><tr><th>#</th><th>Channel</th><th>Volume</th><th>Pos%</th><th>Neg%</th><th>GSS</th></tr></thead>
    <tbody id="scorecard-body"></tbody>
  </table></div>
</div>

<!-- Row 4: Time series + GSS trend (time-range filtered) -->
<div class="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-4">
  <div class="section-card" id="timeseries-card">
    <div class="section-title"><span class="material-symbols-outlined">monitoring</span> Time Series Volume</div>
    <p class="section-desc">Volume komentar per hari (stacked) — mengikuti rentang waktu di atas</p>
    <div id="chart-timeseries" class="plotly-chart"></div>
  </div>
  <div class="section-card" id="gss-trend-card">
    <div class="section-title"><span class="material-symbols-outlined">show_chart</span> Tren GSS Harian</div>
    <p class="section-desc">Generic Sentiment Score per hari, 0-100 · garis putus-putus = netral 50</p>
    <div id="chart-gss-trend" class="plotly-chart"></div>
  </div>
</div>

<!-- Row 4b: Legacy timeline (all dated rows, no filter) -->
<div class="section-card mb-4" id="timeline-section">
  <div class="section-title"><span class="material-symbols-outlined">timeline</span> Timeline Lengkap (semua data bertanggal)</div>
  <div id="chart-timeline" class="plotly-chart"></div>
</div>

<!-- Row 5: Top terms + Scatter -->
<div class="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-4">
  <div class="lg:col-span-2 section-card">
    <div class="section-title"><span class="material-symbols-outlined">report</span> Top Terms Negatif</div>
    <div id="chart-terms" class="plotly-chart"></div>
  </div>
  <div class="lg:col-span-3 section-card">
    <div class="section-title"><span class="material-symbols-outlined">trending_up</span> Viral Detection</div>
    <div id="chart-scatter" class="plotly-chart"></div>
  </div>
</div>

<!-- Row 6: Heatmap -->
<div class="section-card mb-4">
  <div class="section-title"><span class="material-symbols-outlined">grid_on</span> Heatmap: Kategori × Sentimen</div>
  <div id="chart-heatmap" class="plotly-chart"></div>
</div>

<!-- Data table -->
<details class="expander">
  <summary><span class="material-symbols-outlined text-[18px] text-on-surface-variant">table_view</span> Data + Filter</summary>
  <div class="expander-body">
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
      <div>
        <label class="form-label">Sentimen</label>
        <select class="form-select" id="dash-flt-label" onchange="dashFilterTable()">
          <option value="">Semua</option><option>Positif</option><option>Netral</option><option>Negatif</option>
        </select>
      </div>
      <div>
        <label class="form-label">Sumber</label>
        <select class="form-select" id="dash-flt-source" onchange="dashFilterTable()">
          <option value="">Semua</option>
          ${[...new Set(rows.map(r=>r.source))].map(s=>`<option value="${s}">${SOURCE_LABEL[s]||s}</option>`).join('')}
        </select>
      </div>
      <div>
        <label class="form-label">Cari teks</label>
        <input class="form-input" id="dash-flt-search" placeholder="keyword..." oninput="dashFilterTable()"/>
      </div>
      <div class="flex items-end">
        <button class="btn btn-secondary btn-sm btn-full" onclick="downloadCSV()">
          <span class="material-symbols-outlined text-[16px]">download</span> Unduh CSV
        </button>
      </div>
    </div>
    <div style="overflow-x:auto;">
      <table class="data-table">
        <thead><tr><th>Sentimen</th><th>Skor</th><th>Sumber</th><th>Kategori</th><th>Teks</th><th>Author</th><th>Likes</th></tr></thead>
        <tbody id="dash-table-body"></tbody>
      </table>
    </div>
    <div class="text-[12px] text-on-surface-variant mt-2" id="dash-table-count"></div>
  </div>
</details>
`;

  // Render all charts
  renderDonut('chart-donut-dash', st);
  renderGauge('chart-gauge', st.gss, st.skor);
  renderInsightBullets('insight-bullets', rows, meta);
  renderPerSourceBar('chart-per-source', rows);
  renderABSA('chart-absa', rows);
  renderScorecard(rows);
  renderTimeline('chart-timeline', rows);
  renderTopTerms('chart-terms', rows);
  renderScatter('chart-scatter', rows);
  renderHeatmap('chart-heatmap', rows);
  renderTimeSection();   // time series + GSS trend (respect time-range filter)
  dashFilterTable();
}

// ── Gauge ──────────────────────────────────────────
function renderGauge(id, gss, skor) {
  Plotly.newPlot(id, [{
    type: 'indicator', mode: 'gauge+number', value: gss,
    number: { suffix: '/100', font: { size: 22 } },
    gauge: {
      axis: { range: [0, 100] },
      bar:  { color: '#005d97', thickness: 0.3 },
      steps: [
        { range: [0,  40], color: '#f9dede' },
        { range: [40, 60], color: '#fff3cd' },
        { range: [60, 80], color: '#a8e6c9' },
        { range: [80,100], color: '#a8e6c9' },
      ],
      threshold: { line: { color: '#0d2b45', width: 3 }, thickness: 0.75, value: gss },
    },
  }], {
    height: 200, margin: { t: 10, b: 5, l: 20, r: 20 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    annotations: [{
      text: `NSS ${skor>=0?'+':''}${skor.toFixed(1)}`,
      x: 0.5, y: 0.15, xref: 'paper', yref: 'paper',
      showarrow: false, font: { size: 13, color: skor >= 0 ? '#1e9e6a' : '#d64545' },
    }],
  }, { displayModeBar: false });
}

// ── Insight bullets ────────────────────────────────
function renderInsightBullets(id, rows, meta) {
  const el  = document.getElementById(id);
  if (!el) return;
  const st  = computeStats(rows);
  const kw  = (meta.keyword || '').toLowerCase();
  const items = [];

  const dom = Object.entries(st.cnt).sort((a,b)=>b[1]-a[1])[0];
  items.push(`<strong>${dom[0]}</strong> — ${dom[1]}/${st.total} (${st.pct[dom[0]].toFixed(0)}%). Skor <strong>${st.skor>=0?'+':''}${st.skor.toFixed(1)}</strong>`);

  const lowConf = rows.filter(r => (r.score||0) < 0.6).length;
  if (lowConf > 0) {
    items.push(`<span style="color:#92400e">⚠ ${lowConf} data (${(100*lowConf/st.total).toFixed(0)}%) skor &lt;0.6 (mungkin meleset).</span>`);
  }

  // Highest neg source
  const srcStats = {};
  for (const r of rows) {
    if (!srcStats[r.source]) srcStats[r.source] = { n: 0, neg: 0 };
    srcStats[r.source].n++;
    if (r.label === 'Negatif') srcStats[r.source].neg++;
  }
  const topNeg = Object.entries(srcStats)
    .filter(([,v]) => v.n >= 5)
    .map(([src,v]) => [src, v.neg/v.n*100])
    .sort((a,b) => b[1]-a[1])[0];
  if (topNeg && topNeg[1] >= 20) {
    items.push(`Keluhan di <strong>${SOURCE_LABEL[topNeg[0]]||topNeg[0]}</strong>: ${topNeg[1].toFixed(0)}% negatif.`);
  }

  el.innerHTML = `<div class="flex flex-col gap-2">
    ${items.map(t=>`<div class="flex items-start gap-2 text-[13px] text-on-surface-variant py-1 border-b border-outline-variant/20">
      <span class="material-symbols-outlined text-[16px] text-primary mt-0.5 flex-shrink-0">chevron_right</span>
      <span>${t}</span>
    </div>`).join('')}
  </div>`;
}

// ── Per source stacked bar ─────────────────────────
function renderPerSourceBar(id, rows) {
  const srcMap = {};
  for (const r of rows) {
    if (!srcMap[r.source]) srcMap[r.source] = { Positif: 0, Netral: 0, Negatif: 0 };
    srcMap[r.source][r.label] = (srcMap[r.source][r.label] || 0) + 1;
  }
  const sources = Object.keys(srcMap).map(s => SOURCE_LABEL[s] || s);
  const traces  = ['Positif','Netral','Negatif'].map(lab => ({
    type: 'bar', name: lab,
    x: Object.keys(srcMap).map(s => SOURCE_LABEL[s] || s),
    y: Object.values(srcMap).map(v => v[lab] || 0),
    marker: { color: LABEL_COLOR[lab] },
  }));
  Plotly.newPlot(id, traces, {
    barmode: 'stack', height: 240,
    margin: { t: 5, b: 5, l: 5, r: 5 },
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false });
}

// ── ABSA diverging bar ─────────────────────────────
function renderABSA(id, rows) {
  const catMap = {};
  for (const r of rows) {
    const cat = r.kategori || 'Lainnya';
    if (!catMap[cat]) catMap[cat] = { Positif: 0, Netral: 0, Negatif: 0 };
    catMap[cat][r.label] = (catMap[cat][r.label] || 0) + 1;
  }
  const cats = Object.keys(catMap);
  const tots = cats.map(c => Object.values(catMap[c]).reduce((a,b)=>a+b,0));
  const posPct = cats.map((c,i)  => tots[i] ? (catMap[c].Positif||0)/tots[i]*100 : 0);
  const negPct = cats.map((c,i)  => tots[i] ? -(catMap[c].Negatif||0)/tots[i]*100 : 0);

  Plotly.newPlot(id, [
    { type:'bar', name:'Positif %', y:cats, x:posPct, orientation:'h', marker:{color:'#1e9e6a'} },
    { type:'bar', name:'Negatif %', y:cats, x:negPct, orientation:'h', marker:{color:'#d64545'} },
  ], {
    barmode: 'overlay', height: Math.max(200, cats.length * 40),
    margin: { t: 5, b: 5, l: 5, r: 5 },
    xaxis: { title: '% Sentiment', tickformat: ',.0f', range: [-100, 100] },
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false });
}

// ── Channel scorecard table ────────────────────────
function renderScorecard(rows) {
  const tbody = document.getElementById('scorecard-body');
  if (!tbody) return;
  const srcMap = {};
  for (const r of rows) {
    if (!srcMap[r.source]) srcMap[r.source] = { n:0, pos:0, neg:0, neu:0 };
    srcMap[r.source].n++;
    if (r.label==='Positif') srcMap[r.source].pos++;
    else if (r.label==='Negatif') srcMap[r.source].neg++;
    else srcMap[r.source].neu++;
  }
  const data = Object.entries(srcMap).map(([src,v]) => ({
    src, n:v.n,
    pos: (v.pos/v.n*100).toFixed(1),
    neg: (v.neg/v.n*100).toFixed(1),
    gss: ((v.pos + 0.5*v.neu)/v.n*100).toFixed(1),
  })).sort((a,b) => parseFloat(b.gss)-parseFloat(a.gss));

  tbody.innerHTML = data.map((d,i) => `
<tr>
  <td class="font-mono text-[12px] text-on-surface-variant">#${i+1}</td>
  <td class="font-semibold">${esc(SOURCE_LABEL[d.src]||d.src)}</td>
  <td>${fmt(d.n)}</td>
  <td style="color:#1e9e6a;font-weight:600;">${d.pos}%</td>
  <td style="color:#d64545;font-weight:600;">${d.neg}%</td>
  <td><span style="background:${parseFloat(d.gss)>=60?'#a8e6c9':'#f9dede'};color:${parseFloat(d.gss)>=60?'#08351f':'#8f1d1d'};padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700;">${d.gss}</span></td>
</tr>`).join('');
}

// ── Timeline ───────────────────────────────────────
function renderTimeline(id, rows) {
  const dated = rows.filter(r => r.date && r.date.length > 8);
  if (dated.length < 5) {
    const el = document.getElementById('timeline-section');
    if (el) el.style.display = 'none';
    return;
  }
  // Group by day
  const dayMap = {};
  for (const r of dated) {
    const day = r.date.slice(0, 10);
    if (!dayMap[day]) dayMap[day] = { Positif:0, Netral:0, Negatif:0 };
    dayMap[day][r.label] = (dayMap[day][r.label] || 0) + 1;
  }
  const days = Object.keys(dayMap).sort();
  Plotly.newPlot(id,
    ['Positif','Netral','Negatif'].map(lab => ({
      type: 'scatter', mode: 'lines+markers', name: lab,
      x: days, y: days.map(d => dayMap[d][lab] || 0),
      line: { color: LABEL_COLOR[lab], width: 2.5 },
      marker: { size: 5 },
      fill: 'tozeroy',
      fillcolor: `${LABEL_COLOR[lab]}18`,
    })),
    {
      height: 260, margin: { t: 10, b: 5, l: 5, r: 5 },
      hovermode: 'x unified',
      legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
      xaxis: { title: 'Tanggal' }, yaxis: { title: 'Jumlah' },
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    }, { displayModeBar: false });
}

// ── Top terms bar ──────────────────────────────────
function renderTopTerms(id, rows) {
  const negTexts = rows.filter(r => r.label === 'Negatif').map(r => r.text || '');
  if (negTexts.length < 3) {
    const el = document.getElementById(id)?.closest('.section-card');
    if (el) el.innerHTML += '<div class="text-[12px] text-on-surface-variant mt-2">Data negatif &lt; 3.</div>';
    return;
  }
  const terms = topTermsJS(negTexts, 10);
  Plotly.newPlot(id, [{
    type: 'bar', orientation: 'h',
    x: terms.map(t=>t[1]), y: terms.map(t=>t[0]),
    marker: { color: '#d64545' },
  }], {
    height: 280, showlegend: false,
    margin: { t: 5, b: 5, l: 5, r: 5 },
    yaxis: { autorange: 'reversed' },
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false });
}

// Simple JS top-terms (stopword filtered)
const STOP_JS = new Set('yang dan di ke dari ini itu ada akan pada juga saya kami kita kamu dia mereka nya punya untuk dengan tidak sebagai karena agar kalau jika saja masih lebih sangat oleh atau apa sih dong deh kok ya nih tuh gitu aja udah dah kalo gak ga nggak ngga enggak gk tak bukan belum jangan the and of to in is it for on with sudah harus bisa saat semua banyak http https www com id'.split(' '));
function topTermsJS(texts, topn = 8) {
  const cnt = {};
  for (const t of texts) {
    for (const w of t.toLowerCase().match(/[a-zà-ÿ']{3,}/g) || []) {
      if (!STOP_JS.has(w)) cnt[w] = (cnt[w] || 0) + 1;
    }
  }
  return Object.entries(cnt).sort((a,b)=>b[1]-a[1]).slice(0, topn);
}

// ── Scatter ────────────────────────────────────────
function renderScatter(id, rows) {
  const traces = ['Positif','Netral','Negatif'].map(lab => {
    const sub = rows.filter(r => r.label === lab);
    return {
      type: 'scatter', mode: 'markers', name: lab,
      x: sub.map(r => r.score || 0),
      y: sub.map(r => r.likes || 0),
      marker: { color: LABEL_COLOR[lab], size: sub.map(r => Math.min(20, 6 + (r.likes||0)/20)) },
      text: sub.map(r => `${SOURCE_LABEL[r.source]||r.source}: ${String(r.text||'').slice(0,60)}`),
      hoverinfo: 'text+x+y',
    };
  });
  Plotly.newPlot(id, traces, {
    height: 260, margin: { t: 5, b: 5, l: 5, r: 5 },
    xaxis: { title: 'Skor Sentimen' }, yaxis: { title: 'Likes' },
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false });
}

// ── Heatmap ────────────────────────────────────────
function renderHeatmap(id, rows) {
  const cats   = [...new Set(rows.map(r => r.kategori || 'Lainnya'))];
  const labels = ['Positif','Netral','Negatif'];
  const z = cats.map(cat => labels.map(lab =>
    rows.filter(r => (r.kategori||'Lainnya') === cat && r.label === lab).length
  ));
  Plotly.newPlot(id, [{
    type: 'heatmap', z, x: labels, y: cats,
    colorscale: 'RdYlGn', text: z.map(row=>row.map(String)),
    texttemplate: '%{text}', showscale: true,
  }], {
    height: Math.max(200, cats.length * 50),
    margin: { t: 5, b: 5, l: 5, r: 5 },
    paper_bgcolor: 'rgba(0,0,0,0)',
  }, { displayModeBar: false });
}

// ── Dash table filter ──────────────────────────────
function dashFilterTable() {
  const labF   = document.getElementById('dash-flt-label')?.value  || '';
  const srcF   = document.getElementById('dash-flt-source')?.value || '';
  const search = (document.getElementById('dash-flt-search')?.value || '').toLowerCase();
  const tbody  = document.getElementById('dash-table-body');
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

  const countEl = document.getElementById('dash-table-count');
  if (countEl) countEl.textContent = `${rows.length} dari ${App.state.rows.length} data`;
}

// ═══════════════════════════════════════════
// PER-SOURCE TAB
// ═══════════════════════════════════════════
function renderSourcePanel(src, rows, prefix = 'panel-src') {
  const panel = document.getElementById(`${prefix}-${src}`);
  if (!panel || !rows.length) return;
  const st  = computeStats(rows);
  const key = `${prefix}-${src}`;

  // ── Adaptive capability detection: chart hanya muncul jika datanya ada ──
  const hasDate    = rows.filter(r => r.date && !isNaN(Date.parse(r.date)));
  const hasLikes   = rows.filter(r => (r.likes || 0) > 0);
  const hasAuthor  = rows.filter(r => r.author && String(r.author).trim());
  const hasEntity  = rows.filter(r => r.entity_mentions && String(r.entity_mentions).trim());
  const hasBot     = rows.some(r => r.is_bot_suspect !== undefined && r.is_bot_suspect !== null);
  const hasRating  = rows.some(r => r.rating !== undefined && r.rating !== null && r.rating !== '');
  const posT = rows.filter(r=>r.label==='Positif').map(r=>r.text||'');
  const negT = rows.filter(r=>r.label==='Negatif').map(r=>r.text||'');

  panel.innerHTML = `
<!-- KPI row -->
<div class="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-4 mt-2">
  ${kpiCard(SOURCE_LABEL[src]||src, fmt(st.total), 'total data', 'analytics', '#005d97')}
  ${kpiCard('NSS', `${st.skor>=0?'+':''}${st.skor.toFixed(1)}`, `GSS ${st.gss.toFixed(1)}`, 'sentiment_very_satisfied', st.skor>=0?'#1e9e6a':'#d64545')}
  ${kpiCard('Positif', st.pct.Positif.toFixed(1)+'%', fmt(st.cnt.Positif), 'thumb_up', '#1e9e6a')}
  ${kpiCard('Negatif', st.pct.Negatif.toFixed(1)+'%', fmt(st.cnt.Negatif), 'notification_important', '#d64545')}
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">pie_chart</span> Distribusi ${esc(SOURCE_LABEL[src]||src)}</div>
    <div id="${key}-donut" class="plotly-chart"></div>
  </div>
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">category</span> Kategori Keluhan</div>
    <div id="${key}-absa" class="plotly-chart"></div>
  </div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
  <div class="section-card" id="${key}-terms-card">
    <div class="section-title"><span class="material-symbols-outlined">manage_search</span> Top Terms Positif vs Negatif</div>
    <div class="grid grid-cols-2 gap-2">
      <div><div class="text-[11px] font-bold text-on-surface-variant mb-1">Positif</div><div id="${key}-terms-pos" class="plotly-chart"></div></div>
      <div><div class="text-[11px] font-bold text-on-surface-variant mb-1">Negatif</div><div id="${key}-terms-neg" class="plotly-chart"></div></div>
    </div>
  </div>
  <div class="section-card" id="${key}-eng-card">
    <div class="section-title"><span class="material-symbols-outlined">favorite</span> Engagement (Likes)</div>
    <p class="section-desc">Distribusi likes &amp; komentar paling engaged</p>
    <div id="${key}-eng" class="plotly-chart"></div>
  </div>
</div>

<div class="section-card mb-4" id="${key}-tl-card">
  <div class="section-title"><span class="material-symbols-outlined">timeline</span> Tren Harian</div>
  <div id="${key}-timeline" class="plotly-chart"></div>
</div>

<div class="section-card mb-4" id="${key}-extra-card">
  <div class="section-title"><span class="material-symbols-outlined">extension</span> Metrik Khusus Sumber</div>
  <div id="${key}-extra" class="plotly-chart"></div>
</div>

<details class="expander">
  <summary><span class="material-symbols-outlined text-[18px] text-on-surface-variant">chat</span> Contoh Komentar</summary>
  <div class="expander-body" id="${key}-comments"></div>
</details>
`;

  renderDonut(`${key}-donut`, st);
  renderABSA(`${key}-absa`, rows);

  // ── Terms: hanya jika cukup data ──
  if (posT.length >= 3 || negT.length >= 3) {
    if (posT.length >= 3) {
      const t = topTermsJS(posT, 6);
      Plotly.newPlot(`${key}-terms-pos`, [{ type:'bar', orientation:'h', x:t.map(x=>x[1]), y:t.map(x=>x[0]), marker:{color:'#1e9e6a'} }],
        { height:180, showlegend:false, margin:{t:5,b:5,l:5,r:5}, yaxis:{autorange:'reversed'}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' },
        { displayModeBar:false });
    } else { document.getElementById(`${key}-terms-pos`).innerHTML = '<div class="text-[12px] text-on-surface-variant p-3">Data positif &lt; 3</div>'; }
    if (negT.length >= 3) {
      const t = topTermsJS(negT, 6);
      Plotly.newPlot(`${key}-terms-neg`, [{ type:'bar', orientation:'h', x:t.map(x=>x[1]), y:t.map(x=>x[0]), marker:{color:'#d64545'} }],
        { height:180, showlegend:false, margin:{t:5,b:5,l:5,r:5}, yaxis:{autorange:'reversed'}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' },
        { displayModeBar:false });
    } else { document.getElementById(`${key}-terms-neg`).innerHTML = '<div class="text-[12px] text-on-surface-variant p-3">Data negatif &lt; 3</div>'; }
  } else {
    document.getElementById(`${key}-terms-card`).style.display = 'none';
  }

  // ── Engagement: hanya jika ada likes > 0 ──
  if (hasLikes.length >= 3) {
    const buckets = [[0,0,'0'],[1,10,'1-10'],[11,50,'11-50'],[51,200,'51-200'],[201,Infinity,'200+']];
    const bl = buckets.map(b => b[2]);
    const bv = buckets.map(b => rows.filter(r => (r.likes||0) >= b[0] && (r.likes||0) <= b[1]).length);
    Plotly.newPlot(`${key}-eng`, [{ type:'bar', x:bl, y:bv, marker:{color:'#005d97'} }],
      { height:180, showlegend:false, margin:{t:5,b:25,l:30,r:5}, xaxis:{title:'Likes'}, yaxis:{title:'Jumlah', gridcolor:'#e3eef7'}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' },
      { displayModeBar:false });
  } else {
    document.getElementById(`${key}-eng-card`).style.display = 'none';
  }

  // ── Timeline per source: hanya jika cukup tanggal valid ──
  if (hasDate.length >= 5) {
    const dayMap = {};
    for (const r of hasDate) {
      const day = String(r.date).slice(0,10);
      if (!dayMap[day]) dayMap[day] = { Positif:0, Netral:0, Negatif:0 };
      dayMap[day][r.label] = (dayMap[day][r.label]||0)+1;
    }
    const days = Object.keys(dayMap).sort();
    Plotly.newPlot(`${key}-timeline`,
      ['Positif','Netral','Negatif'].map(lab => ({
        type:'scatter', mode:'lines+markers', name:lab,
        x:days, y:days.map(d=>dayMap[d][lab]||0),
        line:{color:LABEL_COLOR[lab],width:2.5}, marker:{size:5},
      })),
      { height:220, margin:{t:10,b:30,l:40,r:10}, hovermode:'x unified',
        xaxis:{title:'Tanggal'}, yaxis:{title:'Jumlah', gridcolor:'#e3eef7'},
        legend:{orientation:'h',yanchor:'bottom',y:1.02,xanchor:'right',x:1},
        paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' },
      { displayModeBar:false });
  } else {
    document.getElementById(`${key}-tl-card`).style.display = 'none';
  }

  // ── Metrik khusus sumber (adaptive) ──
  let extraDrawn = false;
  if (src === 'playstore' && hasRating) {
    // Rating histogram (jika scraper sudah capture rating bintang)
    const rl = ['1★','2★','3★','4★','5★'];
    const rv = rl.map((_,i) => rows.filter(r => parseInt(r.rating) === i+1).length);
    Plotly.newPlot(`${key}-extra`, [{ type:'bar', x:rl, y:rv, marker:{color:'#e8c21d'} }],
      { height:200, showlegend:false, margin:{t:5,b:25,l:30,r:5}, xaxis:{title:'Rating'}, yaxis:{title:'Jumlah review', gridcolor:'#e3eef7'}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' },
      { displayModeBar:false });
    extraDrawn = true;
  } else if (src === 'web' && hasAuthor.length >= 3) {
    // Web: breakdown per media (author = nama media)
    const mediaCnt = {};
    for (const r of hasAuthor) mediaCnt[r.author] = (mediaCnt[r.author]||0)+1;
    const ent = Object.entries(mediaCnt).sort((a,b)=>b[1]-a[1]).slice(0,10);
    Plotly.newPlot(`${key}-extra`, [{ type:'bar', orientation:'h', x:ent.map(e=>e[1]), y:ent.map(e=>e[0]), marker:{color:'#005d97'} }],
      { height:Math.max(200, ent.length*30), showlegend:false, margin:{t:5,b:5,l:5,r:5}, yaxis:{autorange:'reversed'}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' },
      { displayModeBar:false });
    extraDrawn = true;
  } else if (hasEntity.length >= 3) {
    // Entity mentions: pihak terkait yang ikut disebut
    const entCnt = {};
    for (const r of hasEntity) {
      try {
        const m = JSON.parse(r.entity_mentions);
        for (const cat of Object.keys(m)) entCnt[cat] = (entCnt[cat]||0) + m[cat].length;
      } catch(_) {}
    }
    const ent = Object.entries(entCnt).sort((a,b)=>b[1]-a[1]).slice(0,8);
    if (ent.length) {
      Plotly.newPlot(`${key}-extra`, [{ type:'bar', orientation:'h', x:ent.map(e=>e[1]), y:ent.map(e=>e[0]), marker:{color:'#004a7c'} }],
        { height:Math.max(200, ent.length*35), showlegend:false, margin:{t:5,b:5,l:5,r:5}, yaxis:{autorange:'reversed'}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' },
        { displayModeBar:false });
      extraDrawn = true;
    }
  }
  if (!extraDrawn) document.getElementById(`${key}-extra-card`).style.display = 'none';

  // ── Contoh komentar ──
  const commEl = document.getElementById(`${key}-comments`);
  if (commEl) {
    commEl.innerHTML = ['Positif','Negatif','Netral'].map(lab => {
      const subs = rows.filter(r=>r.label===lab).sort((a,b)=>(b.likes||0)-(a.likes||0)).slice(0,2);
      if (!subs.length) return '';
      return `<div class="text-[11px] font-bold uppercase text-on-surface-variant mt-3 mb-1">${lab} · ${st.cnt[lab]} data</div>`
        + subs.map(r=>`
<div class="comment-card ${lab==='Positif'?'pos':lab==='Negatif'?'neg':'neu'}">
  <div class="comment-meta">${esc(r.kategori||'?')} · likes ${r.likes||0} · skor ${(r.score||0).toFixed(3)}${r.date?' · '+esc(String(r.date).slice(0,10)):''}</div>
  <div class="comment-text">${esc(String(r.text||'').slice(0,200))}</div>
</div>`).join('');
    }).join('') || '<div class="text-[13px] text-on-surface-variant">Tidak ada contoh.</div>';
  }
}

// ═══════════════════════════════════════════
// PDF EXPORT
// ═══════════════════════════════════════════
async function exportPDF() {
  if (!App.state.rows.length) return toast('Tidak ada data', 'warn');
  toast('Generating PDF...', 'ok', 8000);
  try {
    const body = {
      rows:       App.state.rows,
      meta:       App.state.meta,
      ai_summary: App.state.aiSummary || null,
      ai_reco:    App.state.aiReco    || null,
    };
    const r = await fetch('/api/export/pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `sentiment_${App.state.meta.keyword||'report'}.pdf`;
    a.click();
    toast('PDF siap didownload', 'ok');
  } catch (e) {
    toast('PDF gagal: ' + String(e), 'err');
  }
}

// ═══════════════════════════════════════════
// PER-SOURCE BREAKDOWN PAGE (dedicated)
// Adaptive per source: hanya chart yang datanya tersedia.
// ═══════════════════════════════════════════
window.renderSourcesPage = function () {
  const el = document.getElementById('page-content');
  if (!App.state.rows.length) {
    el.innerHTML = `
<div class="empty-state">
  <span class="material-symbols-outlined empty-state-icon">folder_data</span>
  <div class="empty-state-title">Belum ada data</div>
  <div class="empty-state-desc">Jalankan scraping di halaman Scrape &amp; Analisis dulu.</div>
</div>`;
    return;
  }

  const rows = App.state.rows;
  const sources = [...new Set(rows.map(r => r.source))];

  el.innerHTML = `
<!-- Page header -->
<div class="section-card mb-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
  <div>
    <div class="flex items-center gap-2 mb-2">
      <span class="chip chip-primary"><span class="material-symbols-outlined text-[13px]">folder_data</span> Breakdown</span>
      <span class="chip chip-ok"><span class="material-symbols-outlined text-[13px]">verified</span> ${sources.length} sumber</span>
    </div>
    <h1 class="text-[22px] font-extrabold text-on-surface tracking-tight">Per-Source Breakdown</h1>
    <p class="text-[13px] text-on-surface-variant mt-1">Visualisasi menyesuaikan data yang berhasil tertangkap dari tiap sumber — chart kosong otomatis disembunyikan</p>
  </div>
  <div class="flex gap-2">
    <button class="btn btn-secondary" onclick="navTo('dashboard')">
      <span class="material-symbols-outlined text-[18px]">insights</span> Visualization Overview
    </button>
    <button class="btn btn-primary" onclick="exportPDF()">
      <span class="material-symbols-outlined text-[18px]">picture_as_pdf</span> Export PDF
    </button>
  </div>
</div>

<div id="src-page-tabs">
  <div class="tabs-bar flex-wrap">
    ${sources.map((s,i) => `<button class="tab-btn ${i===0?'active':''}" data-tab="pg-${s}">${SOURCE_LABEL[s]||s}</button>`).join('')}
  </div>
  ${sources.map((s,i) => `
    <div class="tab-panel ${i===0?'active':''}" data-panel="pg-${s}" id="pg-panel-${s}"></div>
  `).join('')}
</div>`;

  initTabs('src-page-tabs');

  // Render first source, lazy-render the rest
  renderSourcePanel(sources[0], rows.filter(r => r.source === sources[0]), 'pg-panel');
  sources.slice(1).forEach(s => {
    document.querySelector(`[data-tab="pg-${s}"]`)?.addEventListener('click', () => {
      const p = document.getElementById(`pg-panel-${s}`);
      if (p && !p.dataset.rendered) {
        renderSourcePanel(s, rows.filter(r => r.source === s), 'pg-panel');
        p.dataset.rendered = '1';
      }
    });
  });
};
