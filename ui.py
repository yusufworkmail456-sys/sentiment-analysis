"""Taspen Sentiment Platform - UI Kit.

Design system adapted from desihn.html (Sentix AI reference):
- Color palette: Taspen navy/blue/gold with Material Design 3 surface tokens
- Typography: Plus Jakarta Sans + JetBrains Mono
- Components: cards, KPI tiles, donut, bars, badges, tokens, chat
"""
import html as _html

# ── Taspen Brand Palette (dari desihn.html + Taspen brand) ──────────────
NAVY      = "#004a7c"        # primary (Taspen navy biru)
NAVY_DARK = "#003a61"
BLUE      = "#005d97"        # secondary blue
BLUE_SOFT = "#e3edf6"        # surface tint
GOLD      = "#c8a200"        # Taspen gold/kuning
GOLD_DARK = "#a88a00"
GOLD_SOFT = "#fdf6d8"
INK       = "#0d1f2e"        # headings
TEXT      = "#2d3f50"        # body
MUTED     = "#7a93a8"        # labels / captions
LINE      = "#dde6f0"        # borders
BG        = "#f4f7fb"        # app background
SURFACE   = "#ffffff"        # card surface
TINT      = "#f0f4f9"        # inner panels

POS       = "#0c7a55"        # positive green
POS_SOFT  = "#d8f2ea"
NEU       = "#7a93a8"        # neutral
NEU_SOFT  = "#edf1f5"
NEG       = "#bf2d2d"        # negative red
NEG_SOFT  = "#fae0e0"
WARNING   = "#d97706"        # warning amber

# Label → color mapping
LABEL_COLOR = {"Positif": POS, "Netral": NEU, "Negatif": NEG}


def esc(s: str) -> str:
    return _html.escape(str(s))


def mt(name: str, size: int = 18, color: str = None, fill: int = 0) -> str:
    """Render Material Symbols Outlined icon."""
    c = f"color:{color};" if color else ""
    return (
        f'<span class="material-symbols-outlined" '
        f'style="font-size:{size}px;{c}font-variation-settings:'
        f"'FILL' {fill},'wght' 500,'GRAD' 0,'opsz' 24\">{name}</span>"
    )


# ── Sidebar shell ────────────────────────────────────────────────────────
def sidebar_shell(brand_html: str, status_html: str, nav_html: str, footer_html: str) -> str:
    return (
        f'<div class="tsp-sb">{brand_html}{status_html}'
        f'<div class="tsp-sb-label">Workspace</div>'
        f'<nav class="tsp-sb-nav">{nav_html}</nav>{footer_html}</div>'
    )


def engine_status(model: str = "ID-Sentiment v1", ms: str = "45ms") -> str:
    return (
        f'<div class="tsp-status"><div class="tsp-status-l">'
        f'<span class="tsp-dot-ok"></span><b>Engine Online</b></div>'
        f'<span class="tsp-status-r tsp-mono">{esc(model)} · {esc(ms)}</span></div>'
    )


def sidebar_footer(volume: int = 0, total: int = 0) -> str:
    pct = min(100, round(100 * volume / total) if total else 0)
    return (
        f'<div class="tsp-sb-foot">'
        f'<div class="tsp-sb-foot-row">'
        f'<b>Data teranalisa</b>'
        f'<span class="tsp-mono">{volume:,} / {total:,}</span></div>'
        f'<div class="tsp-meter"><div style="width:{pct}%"></div></div>'
        f'<div class="tsp-sb-foot-sub">'
        f'<span>Taspen Sentiment Platform</span>'
        f'<span class="tsp-gold-text">by Mitra Digital</span></div></div>'
    )


# ── Page header ──────────────────────────────────────────────────────────
def page_head(title: str, desc_html: str, chips: str = "", actions: str = "") -> str:
    return (
        f'<div class="tsp-phead"><div class="tsp-phead-l">'
        f'<div class="tsp-phead-chips">{chips}</div>'
        f'<h1 class="tsp-h1">{esc(title)}</h1>'
        f'<p class="tsp-phead-desc">{desc_html}</p></div>'
        f'<div class="tsp-phead-actions">{actions}</div></div>'
    )


def chip(icon_name: str, text: str, tone: str = "gold") -> str:
    tones = {
        "gold": (GOLD_SOFT, GOLD_DARK),
        "ok":   (POS_SOFT, POS),
        "info": (BLUE_SOFT, NAVY),
        "neg":  (NEG_SOFT, NEG),
        "mut":  (TINT, MUTED),
    }
    bg, fg = tones.get(tone, tones["mut"])
    return (
        f'<span class="tsp-chip" style="background:{bg};color:{fg};">'
        f'{mt(icon_name, 13)}{esc(text)}</span>'
    )


def btn(label: str, icon_name: str, kind: str = "primary") -> str:
    return (
        f'<span class="tsp-btn tsp-btn-{kind}">{mt(icon_name, 16)}'
        f'<span>{esc(label)}</span></span>'
    )


# ── KPI cards ────────────────────────────────────────────────────────────
def stat(label: str, value: str, sub: str = "", icon_name: str = "analytics",
         accent: str = NAVY, spark: str = None) -> str:
    sp = ""
    if spark:
        sp = (
            f'<svg class="tsp-spark" viewBox="0 0 100 24" preserveAspectRatio="none">'
            f'<path d="{spark} L100,24 L0,24 Z" fill="{accent}" opacity=".10"/>'
            f'<path d="{spark}" fill="none" stroke="{accent}" stroke-width="2" '
            f'stroke-linecap="round"/></svg>'
        )
    return (
        f'<div class="tsp-kpi">'
        f'<div class="tsp-kpi-top">'
        f'<span class="tsp-kpi-label">{esc(label)}</span>'
        f'<span class="tsp-kpi-ic" style="background:{_tint(accent)};color:{accent};">'
        f'{mt(icon_name, 19)}</span></div>'
        f'<div class="tsp-kpi-value tsp-mono" style="color:{accent};">{value}</div>'
        f'<div class="tsp-kpi-sub">{sub}</div>{sp}</div>'
    )


def stats_row(items) -> str:
    return f'<div class="tsp-kpis">{"".join(items)}</div>'


# ── Generic card ─────────────────────────────────────────────────────────
def card(title: str, desc: str = "", body_html: str = "", icon_name: str = "insights",
         accent: str = None) -> str:
    ac = accent or NAVY
    d = f'<p class="tsp-card-desc">{esc(desc)}</p>' if desc else ""
    return (
        f'<div class="tsp-card">'
        f'<div class="tsp-card-top"><div>'
        f'<h3 class="tsp-card-title">{mt(icon_name, 18, ac)} {esc(title)}</h3>{d}'
        f'</div></div>{body_html}</div>'
    )


def section_header(title: str, desc: str = "", icon_name: str = "bar_chart") -> str:
    d = f'<span class="tsp-card-desc" style="margin-left:6px;">{esc(desc)}</span>' if desc else ""
    return (
        f'<div class="tsp-section-head">'
        f'{mt(icon_name, 18, NAVY)}'
        f'<span class="tsp-card-title" style="margin-left:7px;">{esc(title)}</span>{d}'
        f'</div>'
    )


# ── Dot / badge / sentiment bar ──────────────────────────────────────────
def dot(color: str, size: int = 8) -> str:
    return (
        f'<span class="tsp-dot" '
        f'style="width:{size}px;height:{size}px;background:{color};"></span>'
    )


def badge(text: str, tone: str = "ok", icon_name: str = None) -> str:
    tones = {
        "ok":   (POS_SOFT, POS),
        "neg":  (NEG_SOFT, NEG),
        "info": (BLUE_SOFT, NAVY),
        "gold": (GOLD_SOFT, GOLD_DARK),
        "mut":  (TINT, MUTED),
        "warn": ("#fef3c7", WARNING),
    }
    bg, fg = tones.get(tone, tones["mut"])
    ic = mt(icon_name, 13) if icon_name else ""
    return (
        f'<span class="tsp-badge" style="background:{bg};color:{fg};">'
        f'{ic}{esc(text)}</span>'
    )


def sentiment_bar(pct: dict) -> str:
    segs = "".join(
        f'<div style="width:{pct.get(l, 0)}%;background:{LABEL_COLOR[l]};" '
        f'title="{l}: {pct.get(l, 0)}%"></div>'
        for l in ("Positif", "Netral", "Negatif")
    )
    legend = "".join(
        f'<div class="tsp-lg">'
        f'<span class="tsp-dot" style="background:{LABEL_COLOR[l]};"></span>'
        f'<span class="tsp-mono">{pct.get(l, 0):.1f}%</span> {l}</div>'
        for l in ("Positif", "Netral", "Negatif")
    )
    return f'<div class="tsp-sbar">{segs}</div><div class="tsp-sbar-lg">{legend}</div>'


def donut(pct: dict, center_value: str, center_label: str) -> str:
    p, n, g = pct.get("Positif", 0), pct.get("Netral", 0), pct.get("Negatif", 0)
    seg = f"{POS} 0 {p}%, {NEU} {p}% {p+n}%, {NEG} {p+n}% 100%"
    legend = "".join(
        f'<div class="tsp-lg-leg">'
        f'<div class="tsp-lg-k" style="color:{LABEL_COLOR[l]};">'
        f'<span class="tsp-dot" style="background:{LABEL_COLOR[l]};"></span>{l}</div>'
        f'<div class="tsp-lg-v tsp-mono">{pct.get(l, 0):.1f}%</div></div>'
        for l in ("Positif", "Netral", "Negatif")
    )
    return (
        f'<div class="tsp-donut">'
        f'<div class="tsp-donut-ring" style="background:conic-gradient({seg});">'
        f'<div class="tsp-donut-hole">'
        f'<span class="tsp-donut-lab">{esc(center_label)}</span>'
        f'<span class="tsp-donut-val tsp-mono">{center_value}</span>'
        f'</div></div>'
        f'<div class="tsp-donut-leg">{legend}</div></div>'
    )


# ── Token / comment / alert ───────────────────────────────────────────────
def chip_token(text: str, tone: str = "ok", score: float = None) -> str:
    tones = {"ok": (POS_SOFT, POS), "neg": (NEG_SOFT, NEG), "mut": (TINT, MUTED)}
    bg, fg = tones.get(tone, tones["ok"])
    sc = (
        f'<span class="tsp-tok-sc tsp-mono">{score:+.2f}</span>'
        if score is not None else ""
    )
    return (
        f'<span class="tsp-tok" style="background:{bg};color:{fg};">'
        f'{esc(text)}{sc}</span>'
    )


def comment_card(source_label: str, text: str, meta_line: str, tone: str = NEU) -> str:
    return (
        f'<div class="tsp-quote" style="border-left-color:{tone};">'
        f'<div class="tsp-quote-src">{esc(source_label)}</div>'
        f'<div class="tsp-quote-text">{esc(text)}</div>'
        f'<div class="tsp-quote-meta">{esc(meta_line)}</div></div>'
    )


def alert_row(items) -> str:
    out = "".join(
        f'<span class="tsp-alert tsp-alert-{level}">{esc(text)}</span>'
        for text, level in items
    )
    return f'<div class="tsp-alerts">{out}</div>'


def insights_block(bullets) -> str:
    rows = "".join(
        f'<div class="tsp-ins">{mt("arrow_right", 14, NAVY)}<span>{b}</span></div>'
        for b in bullets
    )
    return f'<div class="tsp-ins-wrap">{rows}</div>'


# ── Source breakdown card (per-source specific) ──────────────────────────
def source_scorecard(src_name: str, icon_name: str, total: int,
                     pct: dict, gss: float, accent: str = NAVY) -> str:
    """Compact per-source summary card."""
    bar_segs = "".join(
        f'<div style="width:{pct.get(l,0):.1f}%;background:{LABEL_COLOR[l]};" '
        f'title="{l} {pct.get(l,0):.1f}%"></div>'
        for l in ("Positif", "Netral", "Negatif")
    )
    return (
        f'<div class="tsp-src-card">'
        f'<div class="tsp-src-head">'
        f'<span class="tsp-src-ic" style="color:{accent};">{mt(icon_name, 22)}</span>'
        f'<div><div class="tsp-src-name">{esc(src_name)}</div>'
        f'<div class="tsp-src-vol tsp-mono">{total:,} data</div></div>'
        f'<span class="tsp-badge tsp-badge-gss" style="background:{_tint(accent)};color:{accent};">'
        f'GSS {gss:.1f}</span></div>'
        f'<div class="tsp-sbar" style="margin-top:8px;">{bar_segs}</div>'
        f'<div class="tsp-src-legend">'
        + "".join(
            f'<span class="tsp-src-lg">'
            f'<span class="tsp-dot" style="background:{LABEL_COLOR[l]};"></span>'
            f'<span>{l} {pct.get(l,0):.1f}%</span></span>'
            for l in ("Positif", "Netral", "Negatif")
        )
        + f'</div></div>'
    )


# ── Terminal / progress / empty ───────────────────────────────────────────
def terminal(lines, title: str = "Log") -> str:
    body = "\n".join(_html.escape(str(l)) for l in lines[-400:])
    return (
        f'<div class="tsp-term">'
        f'<div class="tsp-term-bar">'
        f'<span class="tsp-term-dot" style="background:#ff5f57"></span>'
        f'<span class="tsp-term-dot" style="background:#febc2e"></span>'
        f'<span class="tsp-term-dot" style="background:#28c840"></span>'
        f'<span class="tsp-term-title">{esc(title)}</span></div>'
        f'<pre class="tsp-term-body">{body}</pre></div>'
    )


def progress_bar(pct: float, label: str = "") -> str:
    return (
        f'<div class="tsp-prog"><div style="width:{max(0, min(100, pct))}%"></div></div>'
        f'<div class="tsp-prog-label">{esc(label)}</div>'
    )


def source_tile(label: str, icon_name: str, status_ok: bool = True, note: str = "") -> str:
    dot_html = (
        '<span class="tsp-live"></span>' if status_ok
        else '<span class="tsp-off"></span>'
    )
    n = f'<div class="tsp-tile-note">{esc(note)}</div>' if note else ""
    return (
        f'<div class="tsp-tile">'
        f'<span class="tsp-tile-ic">{mt(icon_name, 17, NAVY)}</span>'
        f'<div class="tsp-tile-txt">'
        f'<div class="tsp-tile-name">{esc(label)}</div>{n}</div>'
        f'{dot_html}</div>'
    )


def empty_state(title: str, desc: str, icon_name: str = "radar") -> str:
    return (
        f'<div class="tsp-empty">{mt(icon_name, 36, MUTED)}'
        f'<div class="tsp-empty-title">{esc(title)}</div>'
        f'<div class="tsp-empty-desc">{esc(desc)}</div></div>'
    )


def kv_row(pairs) -> str:
    rows = "".join(
        f'<div class="tsp-kv-k">{esc(k)}</div><div class="tsp-kv-v">{v}</div>'
        for k, v in pairs
    )
    return f'<div class="tsp-kv">{rows}</div>'


# ── Chat bubbles ─────────────────────────────────────────────────────────
def chat_user(text: str) -> str:
    return (
        f'<div class="tsp-chat-row">'
        f'<div class="tsp-chat-user">{esc(text)}</div></div>'
    )


def chat_ai(content_html: str) -> str:
    return (
        f'<div class="tsp-chat-row"><div class="tsp-chat-ai">'
        f'<div class="tsp-chat-ai-head">'
        f'{mt("psychology", 13, NAVY)} Analysis Agent</div>'
        f'<div class="tsp-md">{content_html}</div></div></div>'
    )


# ── Internal helpers ──────────────────────────────────────────────────────
def _tint(hex_color: str) -> str:
    mapping = {
        NAVY: BLUE_SOFT, BLUE: BLUE_SOFT,
        POS: POS_SOFT, NEG: NEG_SOFT,
        GOLD_DARK: GOLD_SOFT, GOLD: GOLD_SOFT,
        NEU: TINT,
    }
    return mapping.get(hex_color, TINT)
