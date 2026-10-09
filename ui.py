"""Taspen Sentiment Platform - custom UI component library.

All widgets are hand-built HTML/CSS so the app never looks like stock Streamlit.
Only essential native inputs stay native (restyled via app.py CSS):
  text_input, checkbox, slider, selectbox, multiselect, button,
  download_button, dataframe, chat_input, plotly_chart, progress.
"""
import html as _html

# ── Palette (Taspen) ──────────────────────────────────────────
NAVY = "#004a7c"
NAVY_DARK = "#00304f"
BLUE = "#005d97"
BLUE_LIGHT = "#e8f1f8"
GOLD = "#e8c21d"
GOLD_DARK = "#d1ae24"
INK = "#0b1f33"
TEXT = "#1e3a52"
MUTED = "#5c7a94"
BG = "#eef4f9"
SURFACE = "#ffffff"
BORDER = "#d5e2ec"
POSITIF = "#1e9e6a"
NETRAL = "#8aa5b5"
NEGATIF = "#d64545"
WARNING = "#e8a13a"

LABEL_COLOR = {"Positif": POSITIF, "Netral": NETRAL, "Negatif": NEGATIF}


def esc(s):
    return _html.escape(str(s))


# ── Cards & sections ──────────────────────────────────────────
def card_open(cls=""):
    return f'<div class="tsp-card {cls}">'


def card(title, desc="", body_html="", accent=BLUE, cls="", icon_svg=""):
    """A titled card. body_html is raw HTML (already trusted/safe)."""
    d = f'<div class="tsp-card-desc">{esc(desc)}</div>' if desc else ""
    ic = f'<span class="tsp-card-ic">{icon_svg}</span>' if icon_svg else ""
    return (
        f'<div class="tsp-card {cls}">'
        f'<div class="tsp-card-head" style="--tsp-accent:{accent};">'
        f'{ic}<div><div class="tsp-card-title">{esc(title)}</div>{d}</div></div>'
        f'{body_html}</div>'
    )


def section(title, desc="", num=None):
    """Numbered section header (step marker)."""
    badge = f'<span class="tsp-step">{num}</span>' if num else ""
    d = f'<span class="tsp-section-desc">{esc(desc)}</span>' if desc else ""
    return (
        f'<div class="tsp-section">{badge}'
        f'<span class="tsp-section-title">{esc(title)}</span>{d}</div>'
    )


def stat(label, value, sub="", color=BLUE, icon_svg=""):
    """Big number stat card."""
    s = f'<div class="tsp-stat-sub">{esc(sub)}</div>' if sub else ""
    return (
        f'<div class="tsp-stat" style="--tsp-stat:{color};">'
        f'<div class="tsp-stat-top">{icon_svg}'
        f'<span class="tsp-stat-label">{esc(label)}</span></div>'
        f'<div class="tsp-stat-value">{esc(value)}</div>{s}</div>'
    )


def stats_row(items):
    """items: list of dicts from stat(); one HTML row."""
    return '<div class="tsp-stats">' + "".join(items) + "</div>"


def dot(color, size=9):
    return (f'<span class="tsp-dot" style="width:{size}px;height:{size}px;'
            f'background:{color};"></span>')


def badge(text, bg=POSITIF, fg="#ffffff"):
    return (f'<span class="tsp-badge" style="background:{bg};color:{fg};">'
            f'{esc(text)}</span>')


def chip(text, bg=BLUE_LIGHT, fg=NAVY):
    return (f'<span class="tsp-chip" style="background:{bg};color:{fg};">'
            f'{esc(text)}</span>')


def kv_row(pairs):
    """pairs: [(k, v)] rendered as a definition grid."""
    rows = "".join(
        f'<div class="tsp-kv-k">{esc(k)}</div><div class="tsp-kv-v">{v}</div>'
        for k, v in pairs)
    return f'<div class="tsp-kv">{rows}</div>'


def sentiment_bar(pct):
    """Horizontal stacked distribution bar. pct: dict label->percent."""
    segs = ""
    for lab in ("Positif", "Netral", "Negatif"):
        v = pct.get(lab, 0)
        if v <= 0:
            continue
        segs += (f'<div class="tsp-sbar-seg" style="width:{v}%;'
                 f'background:{LABEL_COLOR[lab]};" title="{lab}: {v}%"></div>')
    legend = " · ".join(
        f'{dot(LABEL_COLOR[l])} <b style="color:{LABEL_COLOR[l]};">{pct.get(l,0)}%</b> {l}'
        for l in ("Positif", "Netral", "Negatif"))
    return (f'<div class="tsp-sbar">{segs}</div>'
            f'<div class="tsp-sbar-legend">{legend}</div>')


def comment_card(source_label, text, meta_line, tone=NETRAL):
    return (
        f'<div class="tsp-quote" style="--tsp-tone:{tone};">'
        f'<div class="tsp-quote-src">{esc(source_label)}</div>'
        f'<div class="tsp-quote-text">{esc(text)}</div>'
        f'<div class="tsp-quote-meta">{esc(meta_line)}</div></div>'
    )


def terminal(lines, title="Log"):
    """Dark terminal-style log panel."""
    body = "\n".join(_html.escape(str(l)) for l in lines[-400:])
    return (
        f'<div class="tsp-term"><div class="tsp-term-bar">'
        f'<span class="tsp-term-dot" style="background:#ff5f57"></span>'
        f'<span class="tsp-term-dot" style="background:#febc2e"></span>'
        f'<span class="tsp-term-dot" style="background:#28c840"></span>'
        f'<span class="tsp-term-title">{esc(title)}</span></div>'
        f'<pre class="tsp-term-body">{body}</pre></div>'
    )


def progress_bar(pct, label=""):
    """Static progress bar (used inside custom HTML panels)."""
    pct = max(0.0, min(100.0, float(pct)))
    return (
        f'<div class="tsp-prog"><div class="tsp-prog-fill" style="width:{pct}%"></div></div>'
        f'<div class="tsp-prog-label">{esc(label)}</div>'
    )


def source_tile(name, label, icon_svg, color, status_ok=True, note=""):
    """Header block for a per-source config tile."""
    pulse = ('<span class="tsp-live" title="aktif"></span>' if status_ok
             else '<span class="tsp-off" title="nonaktif"></span>')
    n = f'<div class="tsp-tile-note">{esc(note)}</div>' if note else ""
    return (
        f'<div class="tsp-tile" style="--tsp-tile:{color};">'
        f'<span class="tsp-tile-ic">{icon_svg}</span>'
        f'<div class="tsp-tile-txt"><div class="tsp-tile-name">{esc(label)}</div>{n}</div>'
        f'{pulse}</div>'
    )


def empty_state(title, desc, icon_svg=""):
    return (
        f'<div class="tsp-empty">{icon_svg}'
        f'<div class="tsp-empty-title">{esc(title)}</div>'
        f'<div class="tsp-empty-desc">{esc(desc)}</div></div>'
    )


def alert_row(items):
    """items: [(text, level)] -> alert pills row. level in danger|warn|ok|info."""
    if not items:
        return ""
    out = ""
    for text, level in items:
        out += f'<span class="tsp-alert tsp-alert-{level}">{text}</span>'
    return f'<div class="tsp-alerts">{out}</div>'
