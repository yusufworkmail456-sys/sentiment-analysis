/* ═══════════════════════════════════════════
   Sentix AI – Dashboard page
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

  el.innerHTML = `
<!-- Page header -->
<div class="section-card mb-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
  <div>
    <div class="flex items-center gap-2 mb-2">
      <span class="chip chip-primary"><span class="material-symbols-outlined text-[13px]">insights</span> Overview</span>
      <span class="chip chip-ok"><span class="material-symbols-outlined text-[13px]">verified</span> ${fmt(App.state.rows.length)} data</span>
    </div>
    <h1 class="text-[22px] font-extrabold text-on-surface tracking-tight">Dashboard</h1>
    <p class="text-[13px] text-on-surface-variant mt-1">Visualization overview hasil analisis sentimen gabungan &amp; per sumber</p>
  </div>
  <button class="btn btn-secondary" onclick="exportPDF()">
    <span class="material-symbols-outlined text-[18px]">picture_as_pdf</span> Export PDF
  </button>
</div>

<!-- Sub-tabs -->
<div id="dash-tabs">
  <div class="tabs-bar">
    <button class="tab-btn active" data-tab="overview">Overview Gabungan</button>
    <button class="tab-btn" data-tab="per-source">Per-Source Breakdown</button>
  </div>

  <!-- Overview tab -->
  <div class="tab-panel active" data-panel="overview" id="panel-overview"></div>

  <!-- Per-source tab -->
  <div class="tab-panel" data-panel="per-source" id="panel-per-source"></div>
</div>
`;

  initTabs('dash-tabs');
  renderOverview();

  // Lazy render per-source on tab click
  document.querySelector('[data-tab="per-source"]').addEventListener('click', () => {
    const panel = document.getElementById('panel-per-source');
    if (!panel.dataset.rendered) {
      renderPerSource();
      panel.dataset.rendered = '1';
    }
  });
};

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
  ${kpiCard('Total Dianalisis',    fmt(st.total),               `${[...new Set(rows.map(r=>r.source))].length} sumber`,    'analytics',              '#3525cd')}
  ${kpiCard('Net Sentiment Score', `${st.skor>=0?'+':''}${st.skor.toFixed(1)}`, `GSS ${st.gss.toFixed(1)}/100`,  'sentiment_very_satisfied', st.skor>=0?'#006e4b':'#ba1a1a')}
  ${kpiCard('Rasio Positif',       st.pct.Positif.toFixed(1)+'%',  `${fmt(st.cnt.Positif)} komentar`,      'thumb_up',                '#006e4b')}
  ${kpiCard('Negatif Alert',       st.pct.Negatif.toFixed(1)+'%',  `${fmt(st.cnt.Negatif)} komentar`,      'notification_important',  '#ba1a1a')}
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

<!-- Row 4: Timeline -->
<div class="section-card mb-4" id="timeline-section">
  <div class="section-title"><span class="material-symbols-outlined">timeline</span> Tren Sentimen Harian</div>
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
  dashFilterTable();
}

// ── Gauge ──────────────────────────────────────────
function renderGauge(id, gss, skor) {
  Plotly.newPlot(id, [{
    type: 'indicator', mode: 'gauge+number', value: gss,
    number: { suffix: '/100', font: { size: 22 } },
    gauge: {
      axis: { range: [0, 100] },
      bar:  { color: '#3525cd', thickness: 0.3 },
      steps: [
        { range: [0,  40], color: '#ffdad6' },
        { range: [40, 60], color: '#fff3cd' },
        { range: [60, 80], color: '#d8f2ea' },
        { range: [80,100], color: '#6ffbbe' },
      ],
      threshold: { line: { color: '#131b2e', width: 3 }, thickness: 0.75, value: gss },
    },
  }], {
    height: 200, margin: { t: 10, b: 5, l: 20, r: 20 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    annotations: [{
      text: `NSS ${skor>=0?'+':''}${skor.toFixed(1)}`,
      x: 0.5, y: 0.15, xref: 'paper', yref: 'paper',
      showarrow: false, font: { size: 13, color: skor >= 0 ? '#006e4b' : '#ba1a1a' },
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
    { type:'bar', name:'Positif %', y:cats, x:posPct, orientation:'h', marker:{color:'#006e4b'} },
    { type:'bar', name:'Negatif %', y:cats, x:negPct, orientation:'h', marker:{color:'#ba1a1a'} },
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
  <td style="color:#006e4b;font-weight:600;">${d.pos}%</td>
  <td style="color:#ba1a1a;font-weight:600;">${d.neg}%</td>
  <td><span style="background:${parseFloat(d.gss)>=60?'#6ffbbe':'#ffdad6'};color:${parseFloat(d.gss)>=60?'#002113':'#93000a'};padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700;">${d.gss}</span></td>
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
    marker: { color: '#ba1a1a' },
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
function renderPerSource() {
  const panel = document.getElementById('panel-per-source');
  if (!panel) return;
  const rows = App.state.rows;
  const sources = [...new Set(rows.map(r => r.source))];

  // Build sub-tabs
  panel.innerHTML = `
<div id="src-tabs">
  <div class="tabs-bar flex-wrap">
    ${sources.map((s,i) => `<button class="tab-btn ${i===0?'active':''}" data-tab="src-${s}">${SOURCE_LABEL[s]||s}</button>`).join('')}
  </div>
  ${sources.map((s,i) => `
    <div class="tab-panel ${i===0?'active':''}" data-panel="src-${s}" id="panel-src-${s}"></div>
  `).join('')}
</div>`;

  initTabs('src-tabs');

  // Render first source immediately
  renderSourcePanel(sources[0], rows.filter(r => r.source === sources[0]));

  // Lazy render on tab click
  sources.slice(1).forEach(s => {
    document.querySelector(`[data-tab="src-${s}"]`)?.addEventListener('click', () => {
      const p = document.getElementById(`panel-src-${s}`);
      if (p && !p.dataset.rendered) {
        renderSourcePanel(s, rows.filter(r => r.source === s));
        p.dataset.rendered = '1';
      }
    });
  });
}

function renderSourcePanel(src, rows) {
  const panel = document.getElementById(`panel-src-${src}`);
  if (!panel || !rows.length) return;
  const st = computeStats(rows);
  const id = `src-${src}`;

  panel.innerHTML = `
<!-- KPI row -->
<div class="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-4 mt-2">
  ${kpiCard(SOURCE_LABEL[src]||src, fmt(st.total), '', 'analytics', '#3525cd')}
  ${kpiCard('NSS', `${st.skor>=0?'+':''}${st.skor.toFixed(1)}`, `GSS ${st.gss.toFixed(1)}`, 'sentiment_very_satisfied', st.skor>=0?'#006e4b':'#ba1a1a')}
  ${kpiCard('Positif', st.pct.Positif.toFixed(1)+'%', fmt(st.cnt.Positif), 'thumb_up', '#006e4b')}
  ${kpiCard('Negatif', st.pct.Negatif.toFixed(1)+'%', fmt(st.cnt.Negatif), 'notification_important', '#ba1a1a')}
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">pie_chart</span> Distribusi ${esc(SOURCE_LABEL[src]||src)}</div>
    <div id="${id}-donut" class="plotly-chart"></div>
  </div>
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">manage_search</span> Top Terms</div>
    <div class="grid grid-cols-2 gap-2">
      <div><div class="text-[11px] font-bold text-on-surface-variant mb-1">Positif</div><div id="${id}-terms-pos" class="plotly-chart"></div></div>
      <div><div class="text-[11px] font-bold text-on-surface-variant mb-1">Negatif</div><div id="${id}-terms-neg" class="plotly-chart"></div></div>
    </div>
  </div>
</div>

<!-- Timeline for this source -->
<div class="section-card mb-4" id="${id}-tl-wrap">
  <div class="section-title"><span class="material-symbols-outlined">timeline</span> Tren Harian</div>
  <div id="${id}-timeline" class="plotly-chart"></div>
</div>

<!-- Sample comments -->
<details class="expander">
  <summary><span class="material-symbols-outlined text-[18px] text-on-surface-variant">chat</span> Contoh Komentar</summary>
  <div class="expander-body" id="${id}-comments"></div>
</details>
`;

  renderDonut(`${id}-donut`, st);

  // Top terms pos/neg
  const posT = rows.filter(r=>r.label==='Positif').map(r=>r.text||'');
  const negT = rows.filter(r=>r.label==='Negatif').map(r=>r.text||'');
  if (posT.length >= 3) {
    const t = topTermsJS(posT, 6);
    Plotly.newPlot(`${id}-terms-pos`, [{ type:'bar', orientation:'h', x:t.map(x=>x[1]), y:t.map(x=>x[0]), marker:{color:'#006e4b'} }],
      { height:180, showlegend:false, margin:{t:5,b:5,l:5,r:5}, yaxis:{autorange:'reversed'}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' },
      { displayModeBar:false });
  }
  if (negT.length >= 3) {
    const t = topTermsJS(negT, 6);
    Plotly.newPlot(`${id}-terms-neg`, [{ type:'bar', orientation:'h', x:t.map(x=>x[1]), y:t.map(x=>x[0]), marker:{color:'#ba1a1a'} }],
      { height:180, showlegend:false, margin:{t:5,b:5,l:5,r:5}, yaxis:{autorange:'reversed'}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)' },
      { displayModeBar:false });
  }

  // Timeline for source
  const dated = rows.filter(r => r.date && r.date.length > 8);
  if (dated.length >= 5) {
    const dayMap = {};
    for (const r of dated) {
      const day = r.date.slice(0,10);
      if (!dayMap[day]) dayMap[day] = { Positif:0, Netral:0, Negatif:0 };
      dayMap[day][r.label] = (dayMap[day][r.label]||0)+1;
    }
    const days = Object.keys(dayMap).sort();
    Plotly.newPlot(`${id}-timeline`,
      ['Positif','Netral','Negatif'].map(lab => ({
        type:'scatter', mode:'lines+markers', name:lab,
        x:days, y:days.map(d=>dayMap[d][lab]||0),
        line:{color:LABEL_COLOR[lab],width:2.5}, marker:{size:5},
      })),
      { height:220, margin:{t:5,b:5,l:5,r:5}, hovermode:'x unified', paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
        legend:{orientation:'h',yanchor:'bottom',y:1.02,xanchor:'right',x:1} },
      { displayModeBar:false });
  } else {
    const w = document.getElementById(`${id}-tl-wrap`);
    if (w) w.style.display = 'none';
  }

  // Sample comments
  const commEl = document.getElementById(`${id}-comments`);
  if (commEl) {
    commEl.innerHTML = ['Positif','Negatif','Netral'].map(lab => {
      const subs = rows.filter(r=>r.label===lab).sort((a,b)=>(b.likes||0)-(a.likes||0)).slice(0,2);
      if (!subs.length) return '';
      return `<div class="text-[11px] font-bold uppercase text-on-surface-variant mt-3 mb-1">${lab} · ${st.cnt[lab]} data</div>`
        + subs.map(r=>`
<div class="comment-card ${lab==='Positif'?'pos':lab==='Negatif'?'neg':'neu'}">
  <div class="comment-meta">${esc(r.kategori||'?')} · likes ${r.likes||0} · skor ${(r.score||0).toFixed(3)}</div>
  <div class="comment-text">${esc(String(r.text||'').slice(0,200))}</div>
</div>`).join('');
    }).join('');
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
