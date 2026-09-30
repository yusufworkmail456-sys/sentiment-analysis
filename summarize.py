#!/usr/bin/env python3
"""Ringkasan sentimen dari CSV berlabel -> teks siap kirim LINE."""
import sys

import pandas as pd

BAR = {"Positive": "🟢", "positive": "🟢", "Neutral": "⚪", "neutral": "⚪", "Negative": "🔴", "negative": "🔴"}


def main() -> int:
    path = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else ""
    df = pd.read_csv(path)
    total = len(df)
    if total == 0:
        print("Tidak ada komentar terbaca.")
        return 1

    vc = df["label"].value_counts()
    pos = int(vc.get("positive", 0))
    neu = int(vc.get("neutral", 0))
    neg = int(vc.get("negative", 0))

    lines = []
    lines.append("📊 HASIL SENTIMENT ANALYSIS")
    if url:
        lines.append(url)
    lines.append(f"Total komentar: {total}")
    lines.append("")
    lines.append("Ringkasan:")
    for label, n in (("positive", pos), ("neutral", neu), ("negative", neg)):
        pct = n / total * 100
        bar = "█" * int(round(pct / 5))
        lines.append(f"{BAR.get(label, '•')} {label.capitalize():9s} {n:4d} ({pct:.0f}%) {bar}")
    lines.append("")

    # kesimpulan sederhana
    if pos > neg and pos > neu:
        kesimpulan = "Kesimpulan: sentimen dominan POSITIF 🙂"
    elif neg > pos and neg > neu:
        kesimpulan = "Kesimpulan: sentimen dominan NEGATIF 😕"
    else:
        kesimpulan = "Kesimpulan: sentimen CAMPURAN / NETRAL"
    lines.append(kesimpulan)

    # contoh komentar paling yakin per label
    def contoh(label, n=2):
        sub = df[(df["label"] == label) & (df["score"] >= 0.75)].sort_values("score", ascending=False)
        out = []
        for _, r in sub.head(n).iterrows():
            t = str(r["text"]).replace("\n", " ").strip()
            if len(t) > 80:
                t = t[:77] + "..."
            out.append(f'  "{t}"')
        return out

    if pos:
        lines.append("")
        lines.append("Contoh positif:")
        lines.extend(contoh("positive"))
    if neg:
        lines.append("")
        lines.append("Contoh negatif:")
        lines.extend(contoh("negative"))

    # komentar paling banyak di-like
    if "likes" in df.columns:
        try:
            lk = df.dropna(subset=["likes"])
            lk = lk[pd.to_numeric(lk["likes"], errors="coerce").fillna(0) > 0]
            if not lk.empty:
                top = lk.sort_values("likes", ascending=False).iloc[0]
                t = str(top["text"]).replace("\n", " ").strip()
                if len(t) > 80:
                    t = t[:77] + "..."
                lines.append("")
                lines.append(f"👍 Komentar terpopuler ({int(top['likes'])} likes):")
                lines.append(f'  "{t}"')
        except Exception:
            pass

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
