"""Custom SVG icon set for Sentimetter - uniform line-icon style.
Matches docs theme: primary #3498db, ink #0b1120, text #1e293b.
"""
import html as _html

# ── Color palette (from docs) ──────────────────────────────
C_PRIMARY = "#3498db"
C_PRIMARY_DARK = "#2980b9"
C_INK = "#0b1120"
C_TEXT = "#1e293b"
C_MUTED = "#64748b"
C_SUCCESS = "#22c55e"
C_WARNING = "#f59e0b"
C_DANGER = "#ef4444"
C_POSITIF = "#2ecc71"
C_NETRAL = "#95a5a6"
C_NEGATIF = "#e74c3c"

# ── Icon definitions (24x24 viewBox, stroke-based line icons) ──
_ICONS = {
    "chart": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 16v-6M12 16v-10M17 16v-3"/>',
    "gauge": '<path d="M12 14a2 2 0 1 0 2-2"/><path d="M13.4 10.6 19 5"/><path d="M2 18a10 10 0 0 1 20 0"/>',
    "ai": '<rect x="4" y="8" width="16" height="12" rx="3"/><circle cx="9" cy="14" r="1.2" fill="currentColor" stroke="none"/><circle cx="15" cy="14" r="1.2" fill="currentColor" stroke="none"/><path d="M12 8V4M9 4h6"/><path d="M2 13v3M22 13v3"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    "dashboard": '<rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="5" rx="1.5"/><rect x="13" y="11" width="8" height="10" rx="1.5"/><rect x="3" y="14" width="8" height="7" rx="1.5"/>',
    "key": '<circle cx="7.5" cy="15.5" r="4.5"/><path d="m10.5 12.5 8-8M16 4l3 3M14 6l3 3"/>',
    "gear": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "rocket": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "cross": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>',
    "warning": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z"/><path d="M12 9v4M12 17h.01"/>',
    "point": '<path d="M18 11V6a2 2 0 0 0-4 0v5"/><path d="M14 10V4a2 2 0 0 0-4 0v6"/><path d="M10 10.5V6a2 2 0 0 0-4 0v8"/><path d="M18 8a2 2 0 1 1 4 0c0 4.5-3.5 8-8 8h-3a4 4 0 0 1-4-4l4-6"/>',
    "trend-up": '<path d="m3 17 6-6 4 4 8-8"/><path d="M17 7h4v4"/>',
    "trend-down": '<path d="m3 7 6 6 4-4 8 8"/><path d="M17 17h4v-4"/>',
    "clipboard": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 14l2 2 4-4"/>',
    "broadcast": '<circle cx="12" cy="13" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 10.49M7.76 7.76a6 6 0 0 0 0 10.49M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2z"/>',
    "folder": '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2a2 2 0 0 0-1.66-.9H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2z"/>',
    "note": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h5"/>',
    "bulb": '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7c.6.4 1 1.1 1 1.8V17h6v-.5c0-.7.4-1.4 1-1.8A7 7 0 0 0 12 2z"/>',
    "thinking": '<path d="M12 5a3 3 0 1 0-5.99.5A4.5 4.5 0 0 0 3 9.5c0 1.5.8 2.8 2 3.6"/><path d="M12 5a3 3 0 1 1 5.99.5A4.5 4.5 0 0 1 21 9.5c0 1.5-.8 2.8-2 3.6"/><path d="M12 5v4M8 12v2a4 4 0 0 0 8 0v-2"/><circle cx="10" cy="13" r=".6" fill="currentColor"/><circle cx="14" cy="13" r=".6" fill="currentColor"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
    "document": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "instagram": '<rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1.2" fill="currentColor" stroke="none"/>',
    "youtube": '<rect x="2" y="5" width="20" height="14" rx="4"/><path d="m10 9 5 3-5 3z" fill="currentColor" stroke="none"/>',
    "web": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 0 20 15.3 15.3 0 0 1 0-20z"/>',
    "playstore": '<path d="M6 3v18l13-9z"/><path d="M6 3l8 8M6 21l8-8"/>',
    "facebook": '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>',
    "tiktok": '<path d="M9 12a4 4 0 1 0 4 4V4c1 2 3 3 5 3"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
    "sparkle": '<path d="M12 3l1.9 5.8a2 2 0 0 0 1.3 1.3L21 12l-5.8 1.9a2 2 0 0 0-1.3 1.3L12 21l-1.9-5.8a2 2 0 0 0-1.3-1.3L3 12l5.8-1.9a2 2 0 0 0 1.3-1.3z"/>',
    "refresh": '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/>',
}


def icon(name, size=18, color=None, cls=""):
    """Return an inline SVG string for a named icon."""
    paths = _ICONS.get(name)
    if not paths:
        return ""
    stroke = color or "currentColor"
    return (
        f'<svg class="ss-icon {cls}" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{stroke}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'style="display:inline-block;vertical-align:-3px;">{paths}</svg>'
    )


def icon_text(name, text, size=18, color=None, text_color=None,
              gap="6px", bold=False, cls=""):
    """Return an SVG icon + text in a flex span."""
    ic = icon(name, size, color)
    tc = text_color or C_TEXT
    fw = "700" if bold else "400"
    return (
        f'<span class="ss-icon-text {cls}" style="display:inline-flex;'
        f'align-items:center;gap:{gap};color:{tc};font-weight:{fw};">{ic}'
        f'<span>{_html.escape(text)}</span></span>'
    )


def dot(color, size=10, label=None):
    """Colored circle dot - replaces emoji dots."""
    lab = f'<span style="margin-left:4px;font-size:0.8rem;color:{C_TEXT};">{_html.escape(label)}</span>' if label else ''
    return (
        f'<span style="display:inline-flex;align-items:center;">'
        f'<span style="width:{size}px;height:{size}px;background:{color};'
        f'border-radius:50%;display:inline-block;"></span>{lab}</span>'
    )


def badge(text, bg=C_SUCCESS, fg="#ffffff"):
    """Status badge pill."""
    return (
        f'<span style="background:{bg};color:{fg};padding:1px 7px;'
        f'border-radius:4px;font-size:0.7rem;font-weight:600;'
        f'display:inline-block;line-height:1.5;">'
        f'{_html.escape(text)}</span>'
    )
