#!/usr/bin/env python3
"""Modul kategorisasi konten domain.
Classify comments into relevant domain categories via keyword matching + LLM fallback.
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
