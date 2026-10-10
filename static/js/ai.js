/* ═══════════════════════════════════════════
   Taspen Sentiment Platform – AI Insight page
══════════════════════════════════════════ */

window.renderAI = function () {
  const el = document.getElementById('page-content');

  if (!App.state.rows.length) {
    el.innerHTML = `
<div class="empty-state">
  <span class="material-symbols-outlined empty-state-icon">auto_awesome</span>
  <div class="empty-state-title">Belum ada data</div>
  <div class="empty-state-desc">Jalankan analisis di halaman Scrape &amp; Analisis dulu.</div>
</div>`;
    return;
  }

  const rows = App.state.rows;
  const meta = App.state.meta;
  const st   = computeStats(rows);

  el.innerHTML = `
<!-- Page header -->
<div class="section-card mb-5 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
  <div>
    <div class="flex items-center gap-2 mb-2">
      <span class="chip chip-gold"><span class="material-symbols-outlined text-[13px]">auto_awesome</span> AI Analysis Agent</span>
      <span class="chip chip-ok"><span class="material-symbols-outlined text-[13px]">verified</span> Grounded on Data</span>
    </div>
    <h1 class="text-[22px] font-extrabold text-on-surface tracking-tight">AI Insight</h1>
    <p class="text-[13px] text-on-surface-variant mt-1 max-w-2xl">
      Analisis otomatis oleh Taspen Sentiment Analysis Agent: ringkasan eksekutif, rekomendasi tindakan, dan tanya jawab atas data terbaru.
    </p>
  </div>
  <button class="btn btn-primary" id="btn-gen-all" onclick="generateAll()">
    <span class="material-symbols-outlined text-[18px]">bolt</span> Generate AI Insights
  </button>
</div>

<!-- Context summary -->
<div class="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-5">
  ${kpiCard('Keyword',      esc(meta.keyword||'—'),   `mode: ${meta.mode||'?'}`,      'search',                  '#005d97')}
  ${kpiCard('Total Data',   fmt(st.total),              `${[...new Set(rows.map(r=>r.source))].length} sumber`,  'analytics',               '#1e9e6a')}
  ${kpiCard('Net Sentiment Score', `${st.skor>=0?'+':''}${st.skor.toFixed(1)}`, `GSS ${st.gss.toFixed(1)}/100`, 'sentiment_very_satisfied', st.skor>=0?'#1e9e6a':'#d64545')}
  ${kpiCard('Durasi Scrape', `${meta.durasi||'?'}s`,   `${meta.stamp||''}`,            'timer',                   '#005d97')}
</div>

<!-- AI Summary -->
<div class="section-card mb-4" id="card-summary">
  <div class="flex items-center justify-between mb-3">
    <div class="section-title"><span class="material-symbols-outlined">description</span> Executive Summary</div>
    <button class="btn btn-secondary btn-sm" id="btn-summary" onclick="genSummary()">
      <span class="material-symbols-outlined text-[16px]">refresh</span> Generate
    </button>
  </div>
  <div id="ai-summary-body">
    ${App.state.aiSummary
      ? `<div class="chat-md">${renderMd(App.state.aiSummary)}</div>`
      : `<div class="empty-state" style="padding:24px;">
           <span class="material-symbols-outlined empty-state-icon" style="font-size:28px;">description</span>
           <div class="empty-state-desc">Klik Generate untuk membuat ringkasan eksekutif.</div>
         </div>`}
  </div>
</div>

<!-- AI Reco -->
<div class="section-card mb-4" id="card-reco">
  <div class="flex items-center justify-between mb-3">
    <div class="section-title"><span class="material-symbols-outlined">lightbulb</span> Consideration &amp; Rekomendasi</div>
    <button class="btn btn-secondary btn-sm" id="btn-reco" onclick="genReco()">
      <span class="material-symbols-outlined text-[16px]">refresh</span> Generate
    </button>
  </div>
  <div id="ai-reco-body">
    ${App.state.aiReco
      ? `<div class="chat-md">${renderMd(App.state.aiReco)}</div>`
      : `<div class="empty-state" style="padding:24px;">
           <span class="material-symbols-outlined empty-state-icon" style="font-size:28px;">lightbulb</span>
           <div class="empty-state-desc">Klik Generate untuk membuat rekomendasi strategis.</div>
         </div>`}
  </div>
</div>

<!-- Chatbot -->
<div class="section-card">
  <div class="section-title mb-3">
    <span class="material-symbols-outlined">psychology</span> Tanya Jawab · Analysis Agent
    <span class="text-[12px] font-normal text-on-surface-variant ml-2">${fmt(rows.length)} data · keyword: ${esc(meta.keyword||'?')}</span>
  </div>

  <!-- Quick prompts -->
  <div class="flex flex-wrap gap-2 mb-3">
    ${[
      ['Ringkasan sentimen',    'Beri ringkasan singkat hasil sentiment ini.'],
      ['Kenapa banyak negatif?','Analisis kenapa sentimen negatif tinggi. Keluhan utama?'],
      ['Rekomendasi tindakan',  'Beri rekomendasi actionable berdasarkan hasil sentiment ini.'],
      ['Perbandingan sumber',   'Bagaimana perbandingan sentimen antar sumber?'],
    ].map(([label, prompt]) =>
      `<button class="chip chip-primary cursor-pointer hover:opacity-80" onclick="quickPrompt(${JSON.stringify(prompt)})">${esc(label)}</button>`
    ).join('')}
  </div>

  <!-- Chat history -->
  <div id="chat-history" style="max-height:420px;overflow-y:auto;padding:4px 0;margin-bottom:12px;">
    ${renderChatHistory()}
  </div>

  <!-- Input -->
  <div class="flex gap-2">
    <input class="form-input flex-1" id="chat-input" placeholder="Tanya tentang hasil..."
      onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendChat();}"/>
    <button class="btn btn-primary" id="btn-send" onclick="sendChat()">
      <span class="material-symbols-outlined text-[18px]">send</span>
    </button>
  </div>
  <div id="chat-spinner" style="display:none;" class="flex items-center gap-2 mt-2 text-[12px] text-on-surface-variant">
    <div class="spinner"></div> Agent sedang menjawab...
  </div>
</div>
`;
};

// ── Generate all ───────────────────────────────────
async function generateAll() {
  const btn = document.getElementById('btn-gen-all');
  if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner"></div> Generating...'; }
  await Promise.allSettled([genSummary(), genReco()]);
  if (btn) { btn.disabled = false; btn.innerHTML = '<span class="material-symbols-outlined text-[18px]">bolt</span> Generate AI Insights'; }
}

// ── Generate summary ───────────────────────────────
async function genSummary() {
  const body_el = document.getElementById('ai-summary-body');
  const btn     = document.getElementById('btn-summary');
  if (body_el) body_el.innerHTML = '<div class="flex items-center gap-2 p-4"><div class="spinner"></div> <span class="text-[13px] text-on-surface-variant">Generating executive summary...</span></div>';
  if (btn) btn.disabled = true;
  try {
    const d = await apiPost('/api/ai/summary', { rows: App.state.rows, meta: App.state.meta });
    if (!d.ok) throw new Error(d.error || 'Gagal');
    App.state.aiSummary = d.content;
    if (body_el) body_el.innerHTML = `<div class="chat-md">${renderMd(d.content)}</div>`;
    toast('Executive summary selesai', 'ok');
  } catch (e) {
    if (body_el) body_el.innerHTML = `<div class="text-[13px] text-red-600">${esc(String(e))}</div>`;
    toast('Gagal generate summary', 'err');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── Generate recommendations ───────────────────────
async function genReco() {
  const body_el = document.getElementById('ai-reco-body');
  const btn     = document.getElementById('btn-reco');
  if (body_el) body_el.innerHTML = '<div class="flex items-center gap-2 p-4"><div class="spinner"></div> <span class="text-[13px] text-on-surface-variant">Generating recommendations...</span></div>';
  if (btn) btn.disabled = true;
  try {
    const d = await apiPost('/api/ai/recommendations', { rows: App.state.rows, meta: App.state.meta });
    if (!d.ok) throw new Error(d.error || 'Gagal');
    App.state.aiReco = d.content;
    if (body_el) body_el.innerHTML = `<div class="chat-md">${renderMd(d.content)}</div>`;
    toast('Rekomendasi selesai', 'ok');
  } catch (e) {
    if (body_el) body_el.innerHTML = `<div class="text-[13px] text-red-600">${esc(String(e))}</div>`;
    toast('Gagal generate rekomendasi', 'err');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── Quick prompt ───────────────────────────────────
function quickPrompt(text) {
  const inp = document.getElementById('chat-input');
  if (inp) { inp.value = text; inp.focus(); }
}

// ── Send chat ──────────────────────────────────────
async function sendChat() {
  const inp = document.getElementById('chat-input');
  const text = (inp?.value || '').trim();
  if (!text) return;

  inp.value = '';
  App.state.chatHistory.push({ role: 'user', content: text });
  refreshChatHistory();

  const spinner = document.getElementById('chat-spinner');
  const btn     = document.getElementById('btn-send');
  if (spinner) spinner.style.display = '';
  if (btn)     btn.disabled = true;

  try {
    const d = await apiPost('/api/ai/chat', {
      rows:       App.state.rows,
      meta:       App.state.meta,
      messages:   App.state.chatHistory.slice(0, -1),  // history before current
      user_input: text,
    });
    if (!d.ok) throw new Error(d.error || 'Gagal');
    App.state.chatHistory.push({ role: 'assistant', content: d.content });
    refreshChatHistory();
  } catch (e) {
    App.state.chatHistory.push({ role: 'assistant', content: `Gagal: ${e}` });
    refreshChatHistory();
    toast('Chat gagal', 'err');
  } finally {
    if (spinner) spinner.style.display = 'none';
    if (btn)     btn.disabled = false;
  }
}

// ── Render chat history ────────────────────────────
function renderChatHistory() {
  return App.state.chatHistory.map(m => {
    if (m.role === 'user') {
      return `<div class="chat-row"><div class="chat-user">${esc(m.content)}</div></div>`;
    }
    return `
<div class="chat-row">
  <div class="chat-ai">
    <div class="chat-ai-head">
      <span class="material-symbols-outlined text-[14px]">psychology</span> Analysis Agent
    </div>
    <div class="chat-md">${renderMd(m.content)}</div>
  </div>
</div>`;
  }).join('') || `<div class="text-[13px] text-on-surface-variant text-center py-6">
    Tanya apa saja tentang hasil analisis sentiment ini.
  </div>`;
}

function refreshChatHistory() {
  const el = document.getElementById('chat-history');
  if (el) {
    el.innerHTML = renderChatHistory();
    el.scrollTop = el.scrollHeight;
  }
}
