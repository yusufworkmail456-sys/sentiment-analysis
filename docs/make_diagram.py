#!/usr/bin/env python3
"""Diagram arsitektur sistem sentiment multi-source -> PNG."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

W, H = 20.0, 13.5
fig, ax = plt.subplots(figsize=(W, H), dpi=150)
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

C_USER = "#eaf2fb"; C_LINE = "#e8f8ee"; C_TUN = "#fdf3e3"
C_NGX = "#f0eafa"; C_HERM = "#e3f0fa"; C_SCR = "#fdeaea"
C_MODEL = "#e6f4f1"; C_OUT = "#f5f0e6"
EDGE = "#4a5568"

def box(x, y, w, h, title, lines, fc, fs_t=13, fs_b=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.12,rounding_size=0.25",
                 fc=fc, ec=EDGE, lw=1.6))
    ax.text(x + w/2, y + h - 0.42, title, ha="center", va="top",
            fontsize=fs_t, fontweight="bold", color="#1a202c")
    if lines:
        ax.text(x + w/2, y + h - 1.05, "\n".join(lines), ha="center",
                va="top", fontsize=fs_b, color="#2d3748", linespacing=1.45)

def arrow(x1, y1, x2, y2, label="", style="-|>", ls="-", lx=None, ly=None, color="#4a5568"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                 mutation_scale=18, lw=1.6, color=color, linestyle=ls,
                 shrinkA=2, shrinkB=2))
    if label:
        ax.text(lx if lx is not None else (x1+x2)/2,
                ly if ly is not None else (y1+y2)/2 + 0.18,
                label, ha="center", va="bottom", fontsize=9.5,
                color="#2d3748",
                bbox=dict(fc="white", ec="none", pad=1.2))

# ---- Level 1: user
box(7.5, 11.6, 5.0, 1.5, "HP / Browser Pengguna",
    ["kirim keyword/URL via LINE", "atau buka app /sentiment/"], C_USER)

# ---- Level 2: LINE server + ngrok
box(1.2, 8.9, 4.6, 1.6, "LINE Server", ["Messaging API", "webhook"], C_LINE)
box(14.2, 8.9, 4.6, 1.6, "ngrok (domain statis)",
    ["grumble-matchbook-", "dispersed.ngrok-free.dev"], C_TUN)

arrow(8.6, 11.6, 4.2, 10.5, "chat keyword / URL", lx=5.4, ly=11.15)
arrow(11.4, 11.6, 15.8, 10.5, "buka /sentiment/", lx=14.6, ly=11.15)

# ---- Level 3: nginx
box(6.6, 6.6, 6.8, 2.5, "nginx :80 (VPS)",
    ["/line/      -> 127.0.0.1:8646  (gateway Hermes)",
     "/sentiment/ -> 127.0.0.1:9120  (Streamlit)",
     "/files/     -> CSV hasil (gate ?key=)"], C_NGX, fs_b=10)

arrow(3.5, 8.9, 8.2, 9.1, "webhook POST", lx=5.0, ly=9.25)
arrow(15.5, 8.9, 12.2, 9.1, "tunnel HTTPS", lx=14.2, ly=9.25)

# ---- Level 4: Hermes
box(6.6, 4.1, 6.8, 1.7, "Hermes Agent (VPS)",
    ["gateway LINE + agent: jalankan pipeline,", "push hasil, perawatan sistem"], C_HERM, fs_b=10)

arrow(10.0, 6.6, 10.0, 5.8)

# ---- Level 5: scrapers
box(0.9, 1.6, 5.2, 1.9, "Instagram scraper",
    ["via WARP SOCKS5 :40000", "login ig_session.json"], C_SCR, fs_b=10)
box(7.4, 1.6, 5.2, 1.9, "YouTube scraper",
    ["yt-dlp + comment-", "downloader (tanpa login)"], C_SCR, fs_b=10)
box(13.9, 1.6, 5.2, 1.9, "Web scraper",
    ["Bing News RSS +", "trafilatura (artikel)"], C_SCR, fs_b=10)

arrow(8.4, 4.1, 3.5, 3.5)
arrow(10.0, 4.1, 10.0, 3.5)
arrow(11.6, 4.1, 16.5, 3.5)

# ---- Level 6: model + output
box(7.4, -0.9, 5.2, 1.7, "Sentiment IndoBERT",
    ["3 label + skor, CPU", "w11wo/indonesian-roberta"], C_MODEL, fs_b=10)
box(14.6, -0.9, 4.9, 1.7, "Output",
    ["grafik + CSV (Streamlit),", "ringkasan + link CSV (LINE)"], C_OUT, fs_b=10)

arrow(10.0, 1.6, 10.0, 0.8)
arrow(12.6, 0.0, 14.6, 0.0)

# WARP note
ax.text(3.5, 0.55, "egress IG = IP Cloudflare (WARP),\nbukan IP VPS — anti blokir datacenter",
        ha="center", va="center", fontsize=9.5, style="italic",
        color="#7a3b3b",
        bbox=dict(fc="#fdf6f6", ec="#c9a5a5", boxstyle="round,pad=0.4"))
arrow(3.5, 1.35, 3.5, 1.05, color="#c9a5a5")

ax.set_ylim(-1.3, 13.4)
plt.tight_layout(pad=0.4)
fig.savefig("/root/ig-sentiment/docs/diagram_arsitektur.png",
            bbox_inches="tight", facecolor="white")
print("saved")
