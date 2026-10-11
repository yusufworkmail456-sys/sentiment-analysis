#!/usr/bin/env python3
"""Modul kategorisasi konten domain.
Classify comments into relevant domain categories via keyword matching + LLM fallback.
Also provides bot detection heuristics and entity mention tagging.
"""
import re

# ==================================================== KEYWORD CATEGORIES
CATEGORIES = {
    "Pelayanan": [
        "pelayanan", "layanan", "cs", "customer service", "antri", "antrian",
        "loket", "kecepatan", "ramah", "kasar", " Responsif", "tidak responsif",
        "pelayan", "petugas", "satpam", "informasi", "call center", "hotline",
        "wa", "whatsapp", "telepon", "telp", "ga dibalas", "gak dibalas",
        "tidak dijawab", "lama jawab", "respons",
    ],
    "Klaim": [
        "klaim", "mengklaim", "pengajuan", "ajukan", "diajukan", "ditolak",
        "tolak", "penolakan", "berkas", "dokumen", "syarat", "lengkap",
        "belum", "lambat", "proses", "pencairan", "cair", "nunggu", "tunggu",
        "menunggu", "belum cair", "belum dibayar", "tunggak", "tunggakan",
        "manfaat", "jht", "pensiun", "uang", "dibayar", "pembayaran",
    ],
    "Sistem Digital": [
        "dapen", "dapen online", "aplikasi", "aplikasinya", "app", "apps",
        "error", "bug", "lag", "hang", "loading", "login", "tidak bisa login",
        "gak bisa login", "gabisa login", "down", "maintenance", "server",
        "web", "website", "situs", "online", "digital", "e-service",
        "registrasi", "daftar", "akun", "password", "lupa password",
        "otp", "verifikasi", "tidak bisa akses", "gak bisa akses",
    ],
    "Produk": [
        "asuransi", "dana pensiun", "dapsen", "jht", "jaminan", "program",
        "premi", "iuran", "potongan", "simpanan", "produk", "manfaat",
        "perlindungan", "polis", "uang pertangguran", "up",
    ],
    "Iuran/Potongan": [
        "iuran", "potongan", "gaji", "slip", "gajian", "potong", "dipotong",
        "transparan", "transparansi", " nominal", "hitung", "perhitungan",
        "susut", "berkurang", "tidak sesuai", "gak sesuai", "selisih",
    ],
    "Kantor Cabang": [
        "kantor", "cabang", "kantor cabang", "lokasi", "alamat", "jauh",
        "dekat", "fasilitas", "parkir", "ac", "toilet", "nyaman", "tidak nyaman",
        "ramai", "sepi", "gedung", "pintu", "loket",
    ],
    "Penipuan/Misinformasi": [
        "penipuan", "tipu", "scam", "fraud", "hoax", "hoaks", "palsu",
        "bohong", "fitnah", "menipu", "nakal", "curang", "modus",
        "nomor rekening", "minta rekening", "transfer dulu", "wa bos",
        "atas nama", "tidak resmi", "fez akun", "fake akun", "akun palsu",
        "bonus palsu", "undian palsu", "whatsapp bos", "wa atas nama",
    ],
}

# Keywords that indicate negative sentiment within a category
NEG_INDICATORS = [
    "lambat", "lama", "ditolak", "tolak", "error", "tidak bisa", "gak bisa",
    "gabisa", "belum", "rusak", "down", "mahal", "kurang", "jelek", "buruk",
    "kecewa", "marah", "komplain", "keluhan", "protes", "demo", "mundur",
    "tidak puas", "gak puas", "gak jelas", "tidak jelas", "sulit", "ribet",
    "birokrasi", "berbelit", "nunggu", "nungguin", "ngantri", "menunggu",
]


def classify_text(text, llm_classify=None):
    """Classify a single text into a domain category.
    
    Args:
        text: comment text
        llm_classify: optional callable(text) -> category string (LLM fallback)
    
    Returns:
        (category, confidence) tuple
    """
    if not text or len(text.strip()) < 3:
        return ("Lainnya", 0.0)
    
    text_lower = text.lower()
    scores = {}
    
    for cat, keywords in CATEGORIES.items():
        score = 0
        for kw in keywords:
            kw_clean = kw.strip().lower()
            if kw_clean in text_lower:
                score += len(kw_clean)  # longer keyword = higher weight
        if score > 0:
            scores[cat] = score
    
    if scores:
        best_cat = max(scores, key=scores.get)
        total = sum(scores.values())
        conf = scores[best_cat] / total if total > 0 else 0
        return (best_cat, round(conf, 2))
    
    # LLM fallback if provided
    if llm_classify:
        try:
            cat = llm_classify(text)
            if cat and cat in CATEGORIES:
                return (cat, 0.5)
        except Exception:
            pass
    
    return ("Lainnya", 0.0)


def classify_df(df, llm_classify=None):
    """Add category column to dataframe."""
    cats = []
    confs = []
    for text in df["text"].astype(str):
        cat, conf = classify_text(text, llm_classify)
        cats.append(cat)
        confs.append(conf)
    df["kategori"] = cats
    df["kategori_conf"] = confs
    return df


def get_category_keywords():
    """Return all category keywords for display."""
    return CATEGORIES

# ==================================================== BOT DETECTION
# Heuristic patterns for suspected bot/spam accounts
BOT_USERNAME_PATTERNS = [
    r"^user\d{6,}$",            # user123456
    r"^\w{2,4}\d{8,}$",         # ab12345678
    r"^[a-z]{3,6}_[a-z]{3,6}\d{3,}$",  # word_word123
    r"^\w+\.\w+\d{4,}$",        # name.name1234
    r"^[0-9]{6,}$",             # pure numeric username
]
BOT_TEXT_PATTERNS = [
    r"(follow|follow back|f4f|lb|like4like|f\s?4\s?f)",
    r"(click here|klik di sini|bit\.ly|tinyurl|t\.co\/\w{5,})",
    r"(dm\s?me|inbox\s?me|hubungi\s?wa)",
    r"(.)\1{6,}",               # aaaaaaa repeated chars
    r"^[\U0001F600-\U0001F9FF\s]{5,}$",  # only emojis
    r"(wa\.me/|t\.me/|s\.id/|cutt\.ly)",  # link spam WA/Telegram/shortener
    r"\b(wd|jp)\b",             # istilah judi singkat: WD, JP
]
BOT_KEYWORDS = ["promo", "diskon gila", "jual followers", "jual like", "endorse",
                "open jastip", "giveaway palsu", "bot", "spam", "fake",
                # judi online / judol
                "judi", "judol", "slot", "togel", "casino", "jackpot",
                "maxwin", "scatter", "bandar", "situs judi", "judi online",
                "slot gacor", "gacor", "deposit 25", "daftar sekarang",
                "link daftar", "bo kecil", "rungkad"]


def detect_bot(text, author="", likes=0, threshold=2):
    """
    Heuristic bot/spam detection.
    Returns (is_bot_suspect: bool, reasons: list[str])
    """
    reasons = []
    score = 0

    # Username pattern check
    if author:
        for pat in BOT_USERNAME_PATTERNS:
            if re.match(pat, str(author).lower()):
                reasons.append(f"username pattern: {author}")
                score += 1
                break

    # Text pattern check
    text_lower = str(text).lower()
    for pat in BOT_TEXT_PATTERNS:
        if re.search(pat, text_lower, re.IGNORECASE):
            reasons.append(f"text pattern match")
            score += 1
            break

    # Bot keyword check — hitung semua keyword yang kena (bukan cuma pertama)
    matched_kw = [kw for kw in BOT_KEYWORDS if kw in text_lower]
    if matched_kw:
        reasons.append("keyword: " + ", ".join(matched_kw))
        score += len(matched_kw)

    # Very short text with high likes is suspicious
    if len(str(text).strip()) < 5 and likes > 100:
        reasons.append("sangat pendek + likes tinggi")
        score += 1

    # Repeated identical content (handled at batch level, flag pure gibberish)
    if re.match(r'^[^a-zA-Z\u00C0-\u024F\u0400-\u04FF]{0,2}$', str(text).strip()):
        reasons.append("konten tidak bermakna")
        score += 1

    return (score >= threshold, reasons)


def detect_bot_df(df):
    """Add is_bot_suspect and bot_reasons columns to dataframe."""
    suspects = []
    reason_list = []
    for _, row in df.iterrows():
        flag, reasons = detect_bot(
            row.get("text", ""),
            row.get("author", ""),
            int(row.get("likes", 0) or 0)
        )
        suspects.append(flag)
        reason_list.append("; ".join(reasons) if reasons else "")
    df["is_bot_suspect"] = suspects
    df["bot_reasons"] = reason_list
    return df


# ==================================================== ENTITY MENTION TAGGING
# Dictionary of notable entities grouped by category
ENTITY_DICT = {
    "Politik": [
        "prabowo", "jokowi", "joko widodo", "megawati", "anies", "ganjar",
        "gibran", "erick thohir", "airlangga", "zulhas", "muhaimin",
        "gerindra", "pdip", "golkar", "pks", "demokrat", "nasdem", "pkb",
        "pan", "hanura", "dpr", "mpr", "dprd", "koalisi",
    ],
    "Pemerintah/Regulasi": [
        "bkn", "kemenpan", "kementerian", "menteri", "presiden", "gubernur",
        "bupati", "walikota", "sekda", "peraturan", "pp", "uu", "undang",
        "permenaker", "peraturan menteri", "putusan mahkamah",
        "mahkamah agung", "ma", "mk", "bpk", "kpk", "ojk", "bi",
        "bank indonesia", "kemenkeu",
    ],
    "BUMN/Korporat": [
        "asabri", "jamsostek", "bpjs", "bpjs ketenagakerjaan",
        "bpjs kesehatan", "jiwasraya", "asuransi jiwa", "prudential",
        "manulife", "allianz", "bank btpn", "bank mandiri", "bri", "bni",
        "bjb", "btn", "cimb", "ocbc",
    ],
    "Media": [
        "kompas", "tempo", "detik", "cnbc", "cnn indonesia", "republika",
        "antara", "tribun", "okezone", "liputan6", "tvone", "metro tv",
        "rcti", "sctv", "trans7", "transtv",
    ],
}


def tag_entities(text):
    """
    Find mentioned entities in text.
    Returns dict: {category: [entity1, entity2, ...]}
    """
    text_lower = str(text).lower()
    found = {}
    for cat, entities in ENTITY_DICT.items():
        matches = [e for e in entities if e in text_lower]
        if matches:
            found[cat] = matches
    return found


def tag_entities_df(df):
    """Add entity_mentions column (JSON string) and entity_categories to dataframe."""
    import json
    mentions = []
    categories = []
    for text in df["text"].astype(str):
        found = tag_entities(text)
        mentions.append(json.dumps(found, ensure_ascii=False) if found else "")
        categories.append(", ".join(found.keys()) if found else "")
    df["entity_mentions"] = mentions
    df["entity_categories"] = categories
    return df


# ==================================================== RULES INSPECT (utk UI)
def get_rules():
    """Return aturan deteksi yang aktif — ditampilkan read-only di UI."""
    return {
        "bot_keywords": list(BOT_KEYWORDS),
        "bot_text_patterns": [
            {"pattern": p, "desc": d}
            for p, d in zip(BOT_TEXT_PATTERNS, [
                "Ajakan follow-for-follow (f4f, like4like, dll)",
                "Ajakan klik link / shortener umum (bit.ly, tinyurl, t.co)",
                "Ajakan DM/inbox/WA",
                "Karakter berulang berlebihan (aaaaaaa…)",
                "Hanya emoji (5+)",
                "Link spam WA/Telegram/shortener (wa.me, t.me, s.id, cutt.ly)",
                "Istilah judi singkat: WD, JP",
            ])
        ],
        "bot_username_patterns": [
            {"pattern": p, "desc": d}
            for p, d in zip(BOT_USERNAME_PATTERNS, [
                "user + 6 digit (user123456)",
                "2-4 huruf + 8 digit (ab12345678)",
                "kata_kata + 3 digit",
                "nama.nama + 4 digit",
                "username numerik murni",
            ])
        ],
        "bot_threshold": 2,   # min skor (1 keyword = 1) utk flag dugaan bot
        "entity_dict": {cat: list(ents) for cat, ents in ENTITY_DICT.items()},
    }
