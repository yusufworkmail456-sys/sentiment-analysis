/* ═══════════════════════════════════════════
   Taspen Sentiment Platform – Historical Analytics
   Data dari SQLite (scrape_runs + comments), dedup global.
═══════════════════════════════════════════ */

window.renderHistorical = function () {
  const el = document.getElementById('page-content');
  el.innerHTML = `
<!-- Page header -->
<div class="section-card mb-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
  <div>
    <div class="flex items-center gap-2 mb-2">
      <span class="chip chip-primary"><span class="material-symbols-outlined text-[13px]">history_eviction</span> Database</span>
      <span class="chip chip-gold"><span class="material-symbols-outlined text-[13px]">schedule</span> auto-scrape tiap 6 jam</span>
    </div>
    <h1 class="text-[22px] font-extrabold text-on-surface tracking-tight">Historical Analytics</h1>
    <p class="text-[13px] text-on-surface-variant mt-1 max-w-2xl">
      Tren antar run scrape dari database. Setiap run terekam waktunya — sumbu X selalu ada.
      Komentar di-dedup global (sumber + author + teks), jadi yang terhitung hanya data unik.
    </p>
  </div>
  <div class="flex flex-wrap items-center gap-2">
    <select class="form-select" id="ha-keyword" style="max-width:170px" onchange="haRefresh()">
      <option value="">memuat keyword…</option>
    </select>
    <select class="form-select" id="ha-bucket" style="max-width:140px" onchange="haRefresh()">
      <option value="day">Per hari</option>
      <option value="month" selected>Per bulan</option>
      <option value="year">Per tahun</option>
    </select>
    <button class="btn btn-secondary" onclick="haBackfill()">
      <span class="material-symbols-outlined text-[18px]">unarchive</span> Backfill CSV lama
    </button>
  </div>
</div>

<!-- KPI -->
<div class="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-4" id="ha-kpis"></div>

<!-- Chart 1+2: GSS per run & distribusi per run -->
<div class="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-4">
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">show_chart</span> GSS antar Run Scrape</div>
    <p class="section-desc">Generic Sentiment Score (0-100) per waktu scrape · garis putus-putus = netral 50</p>
    <div id="ha-gss" class="plotly-chart" style="min-height:260px"></div>
  </div>
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">stacked_line_chart</span> Distribusi Sentimen antar Run</div>
    <p class="section-desc">Volume Positif/Netral/Negatif per run (stacked)</p>
    <div id="ha-dist" class="plotly-chart" style="min-height:260px"></div>
  </div>
</div>

<!-- Chart 3: pertumbuhan DB vs tanggal komentar -->
<div class="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-4">
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">trending_up</span> Komentar Unik Kumulatif</div>
    <p class="section-desc">Pertumbuhan database per <span id="ha-bucket-label">bulan</span> (kapan data pertama masuk)</p>
    <div id="ha-growth" class="plotly-chart" style="min-height:260px"></div>
  </div>
  <div class="section-card">
    <div class="section-title"><span class="material-symbols-outlined">calendar_month</span> Sebaran Tanggal Komentar</div>
    <p class="section-desc">Hanya komentar yang punya tanggal dari platform — <span id="ha-dated-info">…</span></p>
    <div id="ha-dates" class="plotly-chart" style="min-height:260px"></div>
  </div>
</div>

<!-- Tabel riwayat run -->
<div class="section-card mb-4">
  <div class="section-title"><span class="material-symbols-outlined">table_rows</span> Riwayat Run Scrape</div>
  <div style="overflow-x:auto;">
    <table class="data-table">
      <thead><tr>
        <th>Waktu (UTC)</th><th>Keyword</th><th>Total</th><th>Baru</th><th>Dup</th>
        <th>Pos</th><th>Net</th><th>Neg</th><th>GSS</th><th>NSS</th>
      </tr></thead>
      <tbody id="ha-run-table"><tr><td colspan="10" class="text-on-surface-variant">memuat…</td></tr></tbody>
    </table>
  </div>
</div>`;

  haRefresh();
};

// ── State cache ────────────────────────────────────
let _haKeywordsLoaded = false;

async function haRefresh() {
  const kwSel  = document.getElementById('ha-keyword');
  const bucket = document.getElementById('ha-bucket')?.value || 'month';
  const kw     = kwSel?.value || null;

  // Keyword options (sekali)
  if (!_haKeywordsLoaded && kwSel) {
    try {
      const d = await apiGet('/api/analytics/keywords');
      if (d.ok) {
        kwSel.innerHTML = '<option value="">Semua keyword</option>' +
          d.keywords.map(k => `<option value="${esc(k)}">${esc(k)}</option>`).join('');
        _haKeywordsLoaded = true;
      }
    } catch (_) {}
  }
  const lbl = document.getElementById('ha-bucket-label');
  if (lbl) lbl.textContent = bucket === 'day' ? 'hari' : bucket === 'year' ? 'tahun' : 'bulan';

  try {
    const [ov, runsD, growthD, datesD] = await Promise.all([
      apiGet('/api/analytics/overview'),
      apiGet(`/api/analytics/runs${kw ? '?keyword=' + encodeURIComponent(kw) : ''}`),
      apiGet(`/api/analytics/growth?bucket=${bucket}${kw ? '&keyword=' + encodeURIComponent(kw) : ''}`),
      apiGet(`/api/analytics/comment-dates?bucket=${bucket}${kw ? '&keyword=' + encodeURIComponent(kw) : ''}`),
    ]);

    if (!ov.ok) throw new Error('DB tidak tersedia');
    haRenderKpis(ov, runsD.runs || []);
    haRenderRunTable(runsD.runs || []);
    haRenderGss(runsD.runs || []);
    haRenderDist(runsD.runs || []);
    haRenderGrowth(growthD.series || []);
    haRenderDates(datesD.series || [], datesD.total_dated || 0);
  } catch (e) {
    toast('Historical: ' + String(e), 'err');
  }
}

function haRenderKpis(ov, runs) {
  const el = document.getElementById('ha-kpis');
  if (!el) return;
  const last = runs[runs.length - 1];
  const prev = runs[runs.length - 2];
  const dGss = (last && prev) ? (last.gss - prev.gss) : null;
  el.innerHTML =
    kpiCard('Komentar Unik di DB', fmt(ov.unique_comments || 0),
      `${fmt(ov.dated_comments || 0)} punya tanggal platform`, 'database', '#005d97') +
    kpiCard('Jumlah Run Tercatat', fmt(ov.runs || 0),
      ov.last_run ? 'terakhir: ' + new Date(ov.last_run).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' }) : '-',
      'history', '#004a7c') +
    kpiCard('GSS Run Terakhir', last ? last.gss.toFixed(1) : '-',
      dGss !== null ? `Δ ${dGss >= 0 ? '+' : ''}${dGss.toFixed(1)} vs run sblm` : 'perlu ≥2 run',
      'sentiment_very_satisfied', (last ? last.gss : 50) >= 50 ? '#1e9e6a' : '#d64545') +
    kpiCard('Baru di Run Terakhir', last ? fmt(last.new_count) : '-',
      last ? `${fmt(last.dup_count)} duplikat (dedup global)` : '-',
      'fiber_new', '#a88a00');
}

function haRenderRunTable(runs) {
  const tb = document.getElementById('ha-run-table');
  if (!tb) return;
  if (!runs.length) {
    tb.innerHTML = '<tr><td colspan="10" class="text-on-surface-variant">Belum ada run. Scrape manual & auto-scheduler akan terekam di sini.</td></tr>';
    return;
  }
  const rows = [...runs].reverse().slice(0, 100).map(r => `
<tr>
  <td class="mono text-[12px]">${new Date(r.ts).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' })}</td>
  <td class="font-semibold">${esc(r.keyword)}</td>
  <td class="mono">${fmt(r.total_rows)}</td>
  <td class="mono" style="color:#1e9e6a">+${fmt(r.new_count)}</td>
  <td class="mono text-on-surface-variant">${fmt(r.dup_count)}</td>
  <td class="mono">${r.pos}</td><td class="mono">${r.neu}</td><td class="mono">${r.neg}</td>
  <td><span style="background:${r.gss >= 60 ? '#a8e6c9' : r.gss >= 40 ? '#fdf6d8' : '#f9dede'};color:${r.gss >= 60 ? '#08351f' : r.gss >= 40 ? '#a88a00' : '#8f1d1d'};padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700;">${r.gss.toFixed(1)}</span></td>
  <td class="mono">${r.nss >= 0 ? '+' : ''}${r.nss.toFixed(1)}</td>
</tr>`).join('');
  tb.innerHTML = rows;
}

function haRenderGss(runs) {
  const el = document.getElementById('ha-gss');
  if (!el) return;
  if (runs.length < 1) { el.innerHTML = '<div class="text-[12px] text-on-surface-variant p-4">Belum ada run.</div>'; return; }
  const x  = runs.map(r => r.ts);
  const y  = runs.map(r => r.gss);
  const traces = [{
    type: 'scatter', mode: 'lines+markers', name: 'GSS',
    x, y, line: { color: '#005d97', width: 3, shape: 'spline' }, marker: { size: 7 },
    fill: 'tozeroy', fillcolor: 'rgba(0,93,151,0.08)',
    hovertemplate: '%{x}<br>GSS %{y:.1f}<extra></extra>',
  }];
  if (runs.length === 1) traces[0].mode = 'markers';
  const layout = {
    height: 260,
    xaxis: { title: 'Waktu scrape' }, yaxis: { title: 'GSS (0-100)', range: [0, 100] },
    shapes: [], showlegend: false,
  };
  if (x.length > 1) {
    layout.shapes.push({ type: 'line', xref: 'x', yref: 'y', x0: x[0], x1: x[x.length - 1],
      y0: 50, y1: 50, line: { color: '#6b8299', width: 1.5, dash: 'dot' } });
  } else {
    layout.shapes.push({ type: 'line', xref: 'paper', yref: 'y', x0: 0, x1: 1,
      y0: 50, y1: 50, line: { color: '#6b8299', width: 1.5, dash: 'dot' } });
  }
  Plotly.newPlot('ha-gss', traces, layout);
}

function haRenderDist(runs) {
  const el = document.getElementById('ha-dist');
  if (!el) return;
  if (!runs.length) { el.innerHTML = '<div class="text-[12px] text-on-surface-variant p-4">Belum ada run.</div>'; return; }
  const x = runs.map(r => r.ts);
  Plotly.newPlot('ha-dist', ['Positif', 'Netral', 'Negatif'].map(lab => ({
    type: 'scatter', mode: 'lines', name: lab, stackgroup: 'one',
    x, y: runs.map(r => r[lab === 'Positif' ? 'pos' : lab === 'Netral' ? 'neu' : 'neg']),
    line: { color: LABEL_COLOR[lab], width: 2 },
    hovertemplate: '%{x}<br>' + lab + ': %{y}<extra></extra>',
  })), {
    height: 260, hovermode: 'x unified',
    xaxis: { title: 'Waktu scrape' }, yaxis: { title: 'Volume komentar' },
  });
}

function haRenderGrowth(series) {
  const el = document.getElementById('ha-growth');
  if (!el) return;
  if (!series.length) { el.innerHTML = '<div class="text-[12px] text-on-surface-variant p-4">Database masih kosong.</div>'; return; }
  const x = series.map(d => d.bucket);
  Plotly.newPlot('ha-growth', [
    { type: 'bar', name: 'Baru', x, y: series.map(d => d.n), marker: { color: '#0077c8' } },
    { type: 'scatter', mode: 'lines+markers', name: 'Kumulatif', x, y: series.map(d => d.cum),
      yaxis: 'y2', line: { color: '#004a7c', width: 3 }, marker: { size: 6 } },
  ], {
    height: 260,
    xaxis: { title: 'Periode masuk DB' },
    yaxis: { title: 'Baru' },
    yaxis2: { title: 'Kumulatif', overlaying: 'y', side: 'right', showgrid: false },
  });
}

function haRenderDates(series, totalDated) {
  const el = document.getElementById('ha-dates');
  const info = document.getElementById('ha-dated-info');
  if (info) info.textContent = `${fmt(totalDated)} komentar punya tanggal platform`;
  if (!el) return;
  if (!series.length) {
    el.innerHTML = '<div class="text-[12px] text-on-surface-variant p-4">Belum ada komentar bertanggal di DB.</div>';
    return;
  }
  const x = series.map(d => d.bucket);
  Plotly.newPlot('ha-dates', ['Positif', 'Netral', 'Negatif'].map(lab => ({
    type: 'scatter', mode: 'lines', name: lab, stackgroup: 'one',
    x, y: series.map(d => d[lab === 'Positif' ? 'pos' : lab === 'Netral' ? 'neu' : 'neg'] || 0),
    line: { color: LABEL_COLOR[lab], width: 2 },
    hovertemplate: '%{x}<br>' + lab + ': %{y}<extra></extra>',
  })), {
    height: 260, hovermode: 'x unified',
    xaxis: { title: 'Tanggal komentar' }, yaxis: { title: 'Volume' },
  });
}

// ── Backfill CSV lama ──────────────────────────────
async function haBackfill() {
  const kw = document.getElementById('ha-keyword')?.value?.trim() || 'taspen';
  if (!confirm(`Backfill semua CSV lama untuk keyword "${kw}" ke database?\nDedup global tetap berlaku — data yang sudah ada tidak akan dobel.`)) return;
  toast('Backfill berjalan…', 'ok', 10000);
  try {
    const d = await apiPost('/api/analytics/backfill', { keyword: kw });
    if (!d.ok) throw new Error(d.error || 'Gagal');
    toast(`Backfill selesai: ${d.files_matched} file, +${fmt(d.total_new)} baris diproses`, 'ok', 6000);
    haRefresh();
  } catch (e) {
    toast('Backfill gagal: ' + String(e), 'err');
  }
}
