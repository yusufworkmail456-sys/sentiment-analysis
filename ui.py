"""Taspen Sentiment Platform - UI kit (Stitch-adapted, Taspen palette).

Pattern: white sidebar, fixed header chip, mono KPI, dense white cards,
Material Symbols icons, Plus Jakarta Sans + JetBrains Mono.
"""
import html as _html

# ── Taspen palette ────────────────────────────────────────────
NAVY = "#004a7c"        # primary action
NAVY_DARK = "#003a61"
BLUE = "#005d97"        # secondary
BLUE_SOFT = "#e3edf6"   # surface tint
GOLD = "#e8c21d"        # accent (active nav, highlights)
GOLD_DARK = "#d1ae24"
INK = "#10202e"         # headings
TEXT = "#3a4c5c"        # body
MUTED = "#8195a5"       # labels
LINE = "#e4ebf1"        # borders
BG = "#f6f9fb"          # app background
SURFACE = "#ffffff"
TINT = "#f1f5f9"        # inner panels
POS = "#0c7a55"         # positive
POS_SOFT = "#dcf3ea"
NEU = "#8aa5b5"         # neutral
NEG = "#c03535"         # negative
NEG_SOFT = "#fbe3e3"
GOLD_SOFT = "#faf0c8"
WARNING = "#e8a13a"

LABEL_COLOR = {"Positif": POS, "Netral": NEU, "Negatif": NEG}


def esc(s):
    return _html.escape(str(s))


def mt(name, size=18, color=None, fill=0):
    c = f"color:{color};" if color else ""
    return (f'<span class="material-symbols-outlined" '
            f'style="font-size:{size}px;{c}font-variation-settings:'
            f"'FILL' {fill}, 'wght' 500, 'GRAD' 0, 'opsz' 24\">{name}</span>")


# ── Sidebar ──────────────────────────────────────────────────
def sidebar_shell(brand_html, status_html, nav_html, footer_html):
    """Wrap sidebar content; layout handled by app.py CSS (.tsp-sb)."""
    return (f'<div class="tsp-sb">{brand_html}{status_html}'
            f'<div class="tsp-sb-label">Workspace</div>'
            f'<nav class="tsp-sb-nav">{nav_html}</nav>{footer_html}</div>')


def nav_item(label, icon_name, active=False):
    cls = "tsp-nav-item active" if active else "tsp-nav-item"
    return (f'<a class="{cls}" href="#">{mt(icon_name, 19)}'
            f'<span>{esc(label)}</span></a>')


def engine_status(model="ID-Sentiment v1", ms="45ms"):
    return (f'<div class="tsp-status"><div class="tsp-status-l">'
            f'<span class="tsp-dot-ok"></span><b>Engine Online</b></div>'
            f'<span class="tsp-status-r tsp-mono">{esc(model)} · {esc(ms)}</span></div>')


def sidebar_footer(volume=0, total=0):
    pct = min(100, round(100 * volume / total) if total else 0)
    return (f'<div class="tsp-sb-foot"><div class="tsp-sb-foot-row">'
            f'<b>Data teranalisa</b><span class="tsp-mono">{volume:,} / {total:,}</span></div>'
            f'<div class="tsp-meter"><div style="width:{pct}%"></div></div>'
            f'<div class="tsp-sb-foot-sub"><span>Taspen Sentiment Platform</span>'
            f'<span class="tsp-gold-text">by Mitra Digital</span></div></div>')


# ── Page header ──────────────────────────────────────────────
def page_head(title, desc_html, chips="", actions=""):
    return (f'<div class="tsp-phead"><div class="tsp-phead-l">'
            f'<div class="tsp-phead-chips">{chips}</div>'
            f'<h1 class="tsp-h1">{esc(title)}</h1>'
            f'<p class="tsp-phead-desc">{desc_html}</p></div>'
            f'<div class="tsp-phead-actions">{actions}</div></div>')


def chip(icon_name, text, tone="gold"):
    tones = {"gold": (GOLD_SOFT, "#8a6d1a"), "ok": (POS_SOFT, POS),
             "info": (BLUE_SOFT, NAVY), "mut": (TINT, MUTED)}
    bg, fg = tones.get(tone, tones["mut"])
    return (f'<span class="tsp-chip" style="background:{bg};color:{fg};">'
            f'{mt(icon_name, 13)}{esc(text)}</span>')


def btn(label, icon_name, kind="primary"):
    return (f'<span class="tsp-btn tsp-btn-{kind}">{mt(icon_name, 16)}'
            f'<span>{esc(label)}</span></span>')


# ── KPI / stats ──────────────────────────────────────────────
def stat(label, value, sub="", icon_name="analytics", accent=NAVY, spark=None):
    """Spark: svg path string (x 0..100, y 0..24) or None."""
    sp = ""
    if spark:
        sp = (f'<svg class="tsp-spark" viewBox="0 0 100 24" preserveAspectRatio="none">'
              f'<path d="{spark} L100,24 L0,24 Z" fill="{accent}" opacity=".12"/>'
              f'<path d="{spark}" fill="none" stroke="{accent}" stroke-width="2" '
              f'stroke-linecap="round"/></svg>')
    return (f'<div class="tsp-kpi"><div class="tsp-kpi-top">'
            f'<span class="tsp-kpi-label">{esc(label)}</span>'
            f'<span class="tsp-kpi-ic" style="background:{_tint(accent)};color:{accent};">'
            f'{mt(icon_name, 19)}</span></div>'
            f'<div class="tsp-kpi-value tsp-mono" style="color:{accent};">{value}</div>'
            f'<div class="tsp-kpi-sub">{sub}</div>{sp}</div>')


def stats_row(items):
    return f'<div class="tsp-kpis">{"".join(items)}</div>'


# ── Cards & generic ──────────────────────────────────────────
def card(title, desc="", body_html="", icon_name="insights"):
    d = f'<p class="tsp-card-desc">{esc(desc)}</p>' if desc else ""
    return (f'<div class="tsp-card"><div class="tsp-card-top"><div>'
            f'<h3 class="tsp-card-title">{mt(icon_name, 18, NAVY)} {esc(title)}</h3>{d}'
            f'</div></div>{body_html}</div>')


def dot(color, size=8):
    return (f'<span class="tsp-dot" style="width:{size}px;height:{size}px;'
            f'background:{color};"></span>')


def badge(text, tone="ok", icon_name=None):
    tones = {"ok": (POS_SOFT, POS), "neg": (NEG_SOFT, NEG),
             "info": (BLUE_SOFT, NAVY), "gold": (GOLD_SOFT, "#8a6d1a"),
             "mut": (TINT, MUTED)}
    bg, fg = tones.get(tone, tones["mut"])
    ic = mt(icon_name, 13) if icon_name else ""
    return (f'<span class="tsp-badge" style="background:{bg};color:{fg};">{ic}{esc(text)}</span>')


def kv_row(pairs):
    rows = "".join(
        f'<div class="tsp-kv-k">{esc(k)}</div><div class="tsp-kv-v">{v}</div>'
        for k, v in pairs)
    return f'<div class="tsp-kv">{rows}</div>'


def sentiment_bar(pct):
    """Inline stacked bar + legend. pct: dict label->percent."""
    segs = "".join(
        f'<div style="width:{pct.get(l, 0)}%;background:{LABEL_COLOR[l]};" '
        f'title="{l}: {pct.get(l, 0)}%"></div>'
        for l in ("Positif", "Netral", "Negatif"))
    legend = "".join(
        f'<div class="tsp-lg"><span class="tsp-dot" style="background:{LABEL_COLOR[l]};"></span>'
        f'<span class="tsp-mono">{pct.get(l, 0):.1f}%</span> {l}</div>'
        for l in ("Positif", "Netral", "Negatif"))
    return f'<div class="tsp-sbar">{segs}</div><div class="tsp-sbar-lg">{legend}</div>'


def donut(pct, center_value, center_label):
    """Conic-gradient donut + 3-cell legend."""
    p, n, g = pct.get("Positif", 0), pct.get("Netral", 0), pct.get("Negatif", 0)
    seg = f"{POS} 0 {p}%, {NEU} {p}% {p+n}%, {NEG} {p+n}% 100%"
    legend = "".join(
        f'<div class="tsp-lg-leg"><div class="tsp-lg-k" style="color:{LABEL_COLOR[l]};">'
        f'<span class="tsp-dot" style="background:{LABEL_COLOR[l]};"></span>{l}</div>'
        f'<div class="tsp-lg-v tsp-mono">{pct.get(l, 0):.1f}%</div></div>'
        for l in ("Positif", "Netral", "Negatif"))
    return (f'<div class="tsp-donut"><div class="tsp-donut-ring" '
            f'style="background:conic-gradient({seg});">'
            f'<div class="tsp-donut-hole"><span class="tsp-donut-lab">{esc(center_label)}</span>'
            f'<span class="tsp-donut-val tsp-mono">{center_value}</span></div></div>'
            f'<div class="tsp-donut-leg">{legend}</div></div>')


def chip_token(text, tone="ok", score=None):
    tones = {"ok": (POS_SOFT, POS), "neg": (NEG_SOFT, NEG)}
    bg, fg = tones.get(tone, tones["ok"])
    sc = (f'<span class="tsp-tok-sc tsp-mono">{score:+.2f}</span>'
          if score is not None else "")
    return (f'<span class="tsp-tok" style="background:{bg};color:{fg};">'
            f'{esc(text)}{sc}</span>')


def comment_card(source_label, text, meta_line, tone=NEU):
    return (f'<div class="tsp-quote" style="border-left-color:{tone};">'
            f'<div class="tsp-quote-src">{esc(source_label)}</div>'
            f'<div class="tsp-quote-text">{esc(text)}</div>'
            f'<div class="tsp-quote-meta">{esc(meta_line)}</div></div>')


def alert_row(items):
    """items: [(text, level)]; level ok|neg|warn|info."""
    out = "".join(f'<span class="tsp-alert tsp-alert-{level}">{esc(text)}</span>'
                  for text, level in items)
    return f'<div class="tsp-alerts">{out}</div>'


def insights_block(bullets):
    rows = "".join(f'<div class="tsp-ins">{mt("arrow_right", 14, NAVY)}<span>{b}</span></div>'
                   for b in bullets)
    return f'<div class="tsp-ins-wrap">{rows}</div>'


def terminal(lines, title="Log"):
    body = "\n".join(_html.escape(str(l)) for l in lines[-400:])
    return (f'<div class="tsp-term"><div class="tsp-term-bar">'
            f'<span class="tsp-term-dot" style="background:#ff5f57"></span>'
            f'<span class="tsp-term-dot" style="background:#febc2e"></span>'
            f'<span class="tsp-term-dot" style="background:#28c840"></span>'
            f'<span class="tsp-term-title">{esc(title)}</span></div>'
            f'<pre class="tsp-term-body">{body}</pre></div>')


def progress_bar(pct, label=""):
    return (f'<div class="tsp-prog"><div style="width:{max(0, min(100, pct))}%"></div></div>'
            f'<div class="tsp-prog-label">{esc(label)}</div>')


def source_tile(label, icon_name, status_ok=True, note=""):
    dot_html = '<span class="tsp-live"></span>' if status_ok else '<span class="tsp-off"></span>'
    n = f'<div class="tsp-tile-note">{esc(note)}</div>' if note else ""
    return (f'<div class="tsp-tile"><span class="tsp-tile-ic">{mt(icon_name, 17, NAVY)}</span>'
            f'<div class="tsp-tile-txt"><div class="tsp-tile-name">{esc(label)}</div>{n}</div>'
            f'{dot_html}</div>')


def empty_state(title, desc, icon_name="radar"):
    return (f'<div class="tsp-empty">{mt(icon_name, 34, MUTED)}'
            f'<div class="tsp-empty-title">{esc(title)}</div>'
            f'<div class="tsp-empty-desc">{esc(desc)}</div></div>')


def _tint(hex_color):
    mapping = {NAVY: BLUE_SOFT, BLUE: BLUE_SOFT, POS: POS_SOFT, NEG: NEG_SOFT,
               GOLD_DARK: GOLD_SOFT, GOLD: GOLD_SOFT, NEU: TINT}
    return mapping.get(hex_color, TINT)
