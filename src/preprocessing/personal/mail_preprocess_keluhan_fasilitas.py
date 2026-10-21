"""
Preprocessing data keluhan kerusakan fasilitas jalan & pejalan kaki (PJU, trotoar, JPO, halte) DKI Jakarta.
Input : CSV hasil scraping X (format tweet-harvest), satu file per kategori: keluhan_<kategori>_jakarta.csv
Output: folder OUTPUT_DIR (lihat CONFIG)

Cara pakai:
    pip install pandas            # wajib
    pip install Sastrawi          # opsional, untuk stopword + stemming
    python preprocess_keluhan_fasilitas.py

Tahapan:
 1. Load + gabung 4 kategori (tweet yang sama di 2+ kategori digabung jadi multi-label)
 2. Buang retweet, bahasa non-Indonesia, dan teks duplikat (template berulang)
 3. Klasifikasi tipe akun: warga vs media/resmi
 4. Cleaning teks + normalisasi slang (+ stopword & stemming bila Sastrawi terpasang)
 5. Pre-label relevansi berbasis aturan + flag konteks (kerusuhan, berita perbaikan, keyword jalan rusak)
 6. Ekstraksi lokasi: kota -> kecamatan -> kelurahan (kelurahan butuh file gazetteer)
 7. Anonimisasi username / user id
 8. Simpan data bersih, file untuk labeling manual, agregat per wilayah-periode, dan ringkasan statistik
"""

import glob
import hashlib
import html
import os
import re
from itertools import groupby

import pandas as pd

# ============================== CONFIG ==============================
INPUT_GLOB = "keluhan_*_jakarta.csv"
OUTPUT_DIR = "output_preprocessing"
# Gazetteer kelurahan: format HDX/BPS (adm4_name, adm4_pcode, adm3_name, adm2_name) atau kota,kecamatan,kelurahan
GAZETTEER_CSV = "jakarta_kelurahan.csv"            # dari data/external/batas-wilayah/
POPULASI_CSV = "jakarta_populasi_kelurahan.csv"    # dari data/external/populasi/ (opsional, join via adm4_pcode)
# File label (kolom id_str,label = relevan/tidak_relevan; boleh sebagian baris). File belakangan menimpa yang di depan.
LABEL_MANUAL_CSV = ["label_manual_diperbaiki.csv", "label_tambahan.csv", "cek_ulang_label.csv"]
JALAN_RUSAK_CSV = None                  # path dataset jalan rusak teman, untuk cek irisan ID (opsional)
TANGGAL_MULAI = None                    # contoh "2020-01-01"; None = pakai semua
PERIODE_AGREGASI = "Y"                  # "M" bulanan, "Q" triwulan, "Y" tahunan
SALT_ANONIM = "ganti-dengan-string-rahasia"

# Akun media/instansi. Tambah sendiri setelah cek top username di ringkasan.
AKUN_RESMI_MEDIA = {
    "tmcpoldametro", "beritajakarta", "binamargajakpus", "detikcom", "dkijakarta", "sonorafm92",
    "kompascom", "binamargadki", "ntmclantaspolri", "radioelshinta", "trafficjakarta",
    "binamargajaktim", "pt_transjakarta", "mediaindonesia", "metro_tv", "disperinergi", "poskodpudki",
}
POLA_AKUN_RESMI = r"binamarga|dinas|pemprov|humas|polda|polres|lantas|tmc|berita|news|detik|kompas|tribun|tempo|radio|fm\d|tv|official|transjakarta|kec_|kel_|suku"

# ============================== KAMUS ==============================
SLANG = {
    "yg": "yang", "gk": "tidak", "ga": "tidak", "gak": "tidak", "nggak": "tidak", "ngga": "tidak", "enggak": "tidak",
    "tdk": "tidak", "g": "tidak", "jl": "jalan", "jln": "jalan", "udh": "sudah", "sdh": "sudah", "udah": "sudah",
    "blm": "belum", "bgt": "banget", "dgn": "dengan", "dg": "dengan", "utk": "untuk", "krn": "karena", "karna": "karena",
    "tp": "tapi", "tpi": "tapi", "jg": "juga", "aja": "saja", "sm": "sama", "dr": "dari", "lg": "lagi", "kalo": "kalau",
    "klo": "kalau", "bs": "bisa", "gelep": "gelap", "nyala": "menyala", "lbh": "lebih", "byk": "banyak", "skrg": "sekarang",
    "trs": "terus", "adlh": "adalah", "ats": "atas", "mgkn": "mungkin", "jd": "jadi", "tsb": "tersebut",
}

KOTA_ALIAS = {
    "Jakarta Pusat": ["jakarta pusat", "jakpus"],
    "Jakarta Utara": ["jakarta utara", "jakut"],
    "Jakarta Barat": ["jakarta barat", "jakbar"],
    "Jakarta Selatan": ["jakarta selatan", "jaksel"],
    "Jakarta Timur": ["jakarta timur", "jaktim"],
}

# 42 kecamatan DKI Jakarta daratan (Kepulauan Seribu dikecualikan)
KECAMATAN = {
    "Jakarta Pusat": ["Gambir", "Sawah Besar", "Kemayoran", "Senen", "Cempaka Putih", "Menteng", "Tanah Abang", "Johar Baru"],
    "Jakarta Utara": ["Penjaringan", "Pademangan", "Tanjung Priok", "Koja", "Kelapa Gading", "Cilincing"],
    "Jakarta Barat": ["Cengkareng", "Grogol Petamburan", "Taman Sari", "Tambora", "Kebon Jeruk", "Kalideres", "Palmerah", "Kembangan"],
    "Jakarta Selatan": ["Tebet", "Setiabudi", "Mampang Prapatan", "Pasar Minggu", "Kebayoran Lama", "Cilandak",
                        "Kebayoran Baru", "Pancoran", "Jagakarsa", "Pesanggrahan"],
    "Jakarta Timur": ["Matraman", "Pulo Gadung", "Jatinegara", "Kramat Jati", "Pasar Rebo", "Cakung", "Duren Sawit",
                      "Makasar", "Ciracas", "Cipayung"],
}

POLA_FASILITAS = {
    "pju": r"\bpju\b|lampu\s+(di\s+)?(sepanjang\s+)?jalan|lampu penerangan|penerangan jalan",
    "trotoar": r"\btrotoar|\btrotoir|\bpedestrian",
    "halte": r"\bhalte\b",
    "jpo": r"\bjpo\b|jembatan penyeberangan|jembatan penyebrangan",
}
POLA_KERUSAKAN = (r"rusak|mati|padam|pecah|menabrak|ditabrak|tertabrak|belum menyala|tidak layak|tak layak|coret|bolong|berlubang|lubang|ambles|amblas|hancur|jebol|bocor|karat|retak|copot|hilang|"
                  r"dicuri|maling|gelap|roboh|ambruk|patah|miring|tidak menyala|keropos|terkelupas")
POLA_BUKAN_PJU = r"lampu merah|lampu tl\b|traffic light|lampu lalu lintas|lampu lalin|mati lampu|pemadaman|\bpln\b|listrik padam"
POLA_KERUSUHAN = r"ricuh|kericuhan|kerusuhan|dibakar|terbakar|unjuk rasa|\bdemo\b|aksi massa|massa aksi|penjarahan"
POLA_PERBAIKAN = r"sudah diperbaiki|telah diperbaiki|selesai diperbaiki|kembali menyala|tindak lanjut|sedang diperbaiki|perbaikan"
POLA_LUAR_JAKARTA = (r"\b(depok|bogor|bekasi|tangerang|tangsel|cibubur|sawangan|bandung|surabaya|medan|semarang|"
                     r"tanjungbalai|sumut|yogyakarta|jogja|makassar|palembang)\b")
POLA_INFO_UMUM = (r"posko pengaduan|untuk pengaduan|pengaduan jalan rusak|hubungi|menghubungi|untuk melaporkan|"
                  r"silahkan kirim|silakan kirim|earth hour|smart city")   # info/imbauan umum, bukan laporan kerusakan
POLA_JALAN_RUSAK = r"jalan rusak|jalan berlubang|jalan bolong|jalan ambles|jalan amblas"


# ============================== FUNGSI ==============================
def load_data(pattern):
    frames = []
    for path in sorted(glob.glob(pattern)):
        kategori = re.search(r"keluhan_(\w+?)_jakarta", os.path.basename(path)).group(1)
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        df["kategori"] = kategori
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"Tidak ada file yang cocok dengan {pattern}")
    return pd.concat(frames, ignore_index=True)


def gabung_multi_kategori(df):
    """Tweet yang muncul di beberapa file kategori digabung jadi satu baris multi-label."""
    kat = df.groupby("id_str")["kategori"].apply(lambda s: "|".join(sorted(set(s))))
    df = df.drop_duplicates("id_str").drop(columns="kategori").merge(kat.rename("kategori"), on="id_str")
    for k in POLA_FASILITAS:
        df[f"kat_{k}"] = df["kategori"].str.contains(k).astype(int)
    return df


def tipe_akun(username):
    u = str(username).lower()
    if u in AKUN_RESMI_MEDIA or re.search(POLA_AKUN_RESMI, u):
        return "media_resmi"
    return "warga"


def bersihkan_teks(teks):
    t = html.unescape(str(teks)).lower()
    t = re.sub(r"https?://\S+|www\.\S+", " ", t)
    t = re.sub(r"@\w+", " ", t)
    t = re.sub(r"#", " ", t)
    t = re.sub(r"(\w+)²", r"\1 \1", t)                    # lampu² -> lampu lampu
    t = re.sub(r"\b(\w+)2\b", r"\1 \1", t)                # berulang2 -> berulang berulang
    t = re.sub(r"[^a-z0-9\s]", " ", t)                    # emoji & tanda baca
    t = " ".join(SLANG.get(w, w) for w in t.split())
    return re.sub(r"\s+", " ", t).strip()


def siapkan_sastrawi():
    try:
        from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
        from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
        stemmer = StemmerFactory().create_stemmer()
        stop = StopWordRemoverFactory().create_stop_word_remover()
        return lambda t: stemmer.stem(stop.remove(t))
    except ImportError:
        print("[info] Sastrawi tidak terpasang: kolom text_model = text_clean (tanpa stopword/stemming)")
        return lambda t: t


def ada(pola, teks):
    return bool(re.search(pola, teks))


def label_relevansi(row):
    t = row["text_clean"]
    if ada(POLA_INFO_UMUM, t):
        return "tidak_relevan"
    fasilitas_cocok = any(ada(POLA_FASILITAS[k], t) for k in POLA_FASILITAS if row[f"kat_{k}"])
    if not fasilitas_cocok or not ada(POLA_KERUSAKAN, t):
        return "tidak_relevan"
    if row["kategori"] == "pju" and ada(POLA_BUKAN_PJU, t):
        return "perlu_cek"   # campur lampu lalu lintas / pemadaman listrik
    if row["flag_kerusuhan"]:
        return "perlu_cek"
    return "kandidat_relevan"


def pola_nama(nama):
    """Regex nama wilayah yang toleran spasi: 'kali deres' cocok dengan 'kalideres' dan sebaliknya."""
    return r"\b" + r"\s?".join(re.escape(w) for w in nama.lower().split()) + r"\b"


def kunci(nama):
    return re.sub(r"\s+", "", str(nama).lower())


def bersihkan_kota(nama):
    return re.sub(r"^(kota|kabupaten)( administrasi)?\s+", "", str(nama).strip(), flags=re.I)


def muat_gazetteer(path):
    """List entri (kunci, pola, kota, kecamatan, kelurahan, pcode, level), urut nama terpanjang dulu.
    kunci = nama huruf kecil tanpa spasi, sehingga 'Kali Deres' dan 'Kalideres' dianggap nama yang sama."""
    entri = []
    if path and os.path.exists(path):
        g = pd.read_csv(path, dtype=str)
        if "adm4_name" in g.columns:   # format HDX/BPS
            g = g.rename(columns={"adm4_name": "kelurahan", "adm3_name": "kecamatan", "adm2_name": "kota",
                                  "adm4_pcode": "pcode"})
        if "pcode" not in g.columns:
            g["pcode"] = None
        g = g.dropna(subset=["kelurahan"])
        g["kota"] = g["kota"].map(bersihkan_kota)
        g = g[~g["kota"].str.contains("seribu", case=False, na=False)]
        for (kota, kec) in g[["kota", "kecamatan"]].drop_duplicates().itertuples(index=False):
            entri.append((kunci(kec), pola_nama(kec), kota, kec.strip(), None, None, "kecamatan"))
        for r in g.itertuples(index=False):
            kel = r.kelurahan.strip()
            entri.append((kunci(kel), pola_nama(kel), r.kota, r.kecamatan.strip(), kel, r.pcode, "kelurahan"))
        print(f"[info] Gazetteer dimuat: {g['kecamatan'].nunique()} kecamatan, {len(g)} kelurahan")
    else:
        for kota, kecs in KECAMATAN.items():
            for kec in kecs:
                entri.append((kunci(kec), pola_nama(kec), kota, kec, None, None, "kecamatan"))
        print(f"[info] {path} tidak ditemukan: lokasi hanya sampai level kecamatan")
    return sorted(entri, key=lambda e: (-len(e[0]), e[0]))


def ekstrak_lokasi(teks, gazetteer):
    hasil = {"kota": None, "kecamatan": None, "kelurahan": None, "adm4_pcode": None,
             "level_lokasi": "tidak_ada", "lokasi_ambigu": False}
    # Cocokkan nama terpanjang dulu, lalu tutup bagian teks yang sudah cocok supaya nama yang lebih pendek
    # di dalamnya tidak ikut cocok (mis. "kramat jati" tidak lagi memicu kelurahan "kramat").
    sisa, cocok = teks, []
    for nama, grup in groupby(gazetteer, key=lambda e: e[0]):
        grup = list(grup)
        if re.search(grup[0][1], sisa):
            cocok.extend(grup)
            sisa = re.sub(grup[0][1], lambda m: " " * len(m.group()), sisa)
    kel = [e for e in cocok if e[6] == "kelurahan"]
    kec = [e for e in cocok if e[6] == "kecamatan"]
    if kel:
        pilihan = kel[0]
        if kec:  # utamakan kelurahan yang konsisten dengan kecamatan yang juga disebut
            sesuai = [e for e in kel if e[3] in {k[3] for k in kec}]
            pilihan = sesuai[0] if sesuai else pilihan
        # Ambigu jika ada beberapa kelurahan, atau nama kelurahan sama dengan nama kecamatan
        # (tweet "di Kramat Jati" bisa berarti kelurahan atau seluruh kecamatan).
        ambigu = len({e[5] or e[4] for e in kel}) > 1 or pilihan[0] in {k[0] for k in kec}
        hasil.update(kota=pilihan[2], kecamatan=pilihan[3], kelurahan=pilihan[4], adm4_pcode=pilihan[5],
                     level_lokasi="kelurahan", lokasi_ambigu=ambigu)
    elif kec:
        hasil.update(kota=kec[0][2], kecamatan=kec[0][3], level_lokasi="kecamatan",
                     lokasi_ambigu=len({e[3] for e in kec}) > 1)
    else:
        for kota, alias in KOTA_ALIAS.items():
            if any(re.search(rf"\b{a}\b", teks) for a in alias):
                hasil.update(kota=kota, level_lokasi="kota")
                break
    return pd.Series(hasil)


def anonim(nilai):
    return hashlib.sha256((SALT_ANONIM + str(nilai)).encode()).hexdigest()[:12]


# ============================== PIPELINE ==============================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    funnel = []

    df = load_data(INPUT_GLOB)
    funnel.append(("Data mentah (gabungan 4 file)", len(df)))

    df = gabung_multi_kategori(df)
    funnel.append(("Setelah gabung tweet multi-kategori", len(df)))

    df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.tz_convert("Asia/Jakarta")
    if TANGGAL_MULAI:
        df = df[df["created_at"] >= pd.Timestamp(TANGGAL_MULAI, tz="Asia/Jakarta")]
        funnel.append((f"Setelah filter tanggal >= {TANGGAL_MULAI}", len(df)))

    df = df[~df["full_text"].str.startswith("RT @")]
    funnel.append(("Setelah buang retweet", len(df)))

    df = df[df["lang"] == "in"]
    funnel.append(("Setelah buang bahasa non-Indonesia", len(df)))

    df["tipe_akun"] = df["username"].map(tipe_akun)
    df["text_clean"] = df["full_text"].map(bersihkan_teks)
    df = df.drop_duplicates("text_clean")
    funnel.append(("Setelah buang teks duplikat", len(df)))

    stem = siapkan_sastrawi()
    df["text_model"] = df["text_clean"].map(stem)

    df["flag_kerusuhan"] = df["text_clean"].map(lambda t: ada(POLA_KERUSUHAN, t))
    df["flag_berita_perbaikan"] = df["text_clean"].map(lambda t: ada(POLA_PERBAIKAN, t))
    df["flag_kw_jalan_rusak"] = df["text_clean"].map(lambda t: ada(POLA_JALAN_RUSAK, t))
    df["relevansi_rule"] = df.apply(label_relevansi, axis=1)

    gazetteer = muat_gazetteer(GAZETTEER_CSV)
    df = pd.concat([df, df["text_clean"].apply(ekstrak_lokasi, gazetteer=gazetteer)], axis=1)

    # Tweet yang menyebut kota di luar Jakarta: buang jika tidak ada lokasi Jakarta, cek manual jika ada
    df["flag_luar_jakarta"] = df["text_clean"].map(lambda t: ada(POLA_LUAR_JAKARTA, t))
    luar_saja = df["flag_luar_jakarta"] & (df["level_lokasi"] == "tidak_ada")
    df.loc[luar_saja, "relevansi_rule"] = "tidak_relevan"
    df.loc[df["flag_luar_jakarta"] & ~luar_saja & (df["relevansi_rule"] == "kandidat_relevan"), "relevansi_rule"] = "perlu_cek"

    # Label manual (jika sudah ada) menimpa label aturan
    files = [LABEL_MANUAL_CSV] if isinstance(LABEL_MANUAL_CSV, str) else LABEL_MANUAL_CSV
    semua = []
    for f in files:
        if not os.path.exists(f):
            print(f"[info] {f} tidak ditemukan, dilewati")
            continue
        lm = pd.read_csv(f, dtype=str, keep_default_na=False)
        lm["id_str"] = lm["id_str"].str.replace(r"^id_", "", regex=True)   # prefix id_ mencegah Excel merusak ID
        lm["label"] = lm["label"].str.strip().str.lower()
        lm = lm[lm["label"].isin(["relevan", "tidak_relevan"])]
        print(f"[info] {f}: {len(lm)} label")
        semua.append(lm[["id_str", "label"]])
    if semua:
        lm = pd.concat(semua).drop_duplicates("id_str", keep="last")
        df = df.merge(lm.rename(columns={"label": "label_manual"}), on="id_str", how="left")
        print(f"[info] Label manual dimuat: {df['label_manual'].notna().sum()} baris")
    else:
        df["label_manual"] = None
    df["relevan_final"] = df["label_manual"].fillna(df["relevansi_rule"])

    # Validasi aturan: bandingkan pre-label aturan dengan label manual pada baris sampel
    validasi = []
    cek = df[df["label_manual"].notna()]
    for rule, benar in [("kandidat_relevan", "relevan"), ("tidak_relevan", "tidak_relevan")]:
        sub = cek[cek["relevansi_rule"] == rule]
        if len(sub):
            akurasi = (sub["label_manual"] == benar).mean()
            validasi.append(f"- Aturan `{rule}`: {akurasi:.0%} sesuai label manual (n={len(sub)})")

    # Engagement & waktu
    for c in ["favorite_count", "retweet_count", "reply_count", "quote_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    df["engagement"] = df[["favorite_count", "retweet_count", "reply_count", "quote_count"]].sum(axis=1)
    df["tahun"] = df["created_at"].dt.year
    df["periode"] = df["created_at"].dt.tz_localize(None).dt.to_period(PERIODE_AGREGASI).astype(str)

    # Anonimisasi: hash akun, buang kolom yang bisa mengidentifikasi orang
    df["user_hash"] = df["user_id_str"].map(anonim)
    df = df.drop(columns=["username", "user_id_str", "tweet_url", "in_reply_to_screen_name", "location"])

    kolom = ["id_str", "created_at", "tahun", "periode", "kategori", "kat_pju", "kat_trotoar", "kat_jpo", "kat_halte",
             "tipe_akun", "user_hash", "full_text", "text_clean", "text_model", "relevansi_rule", "label_manual",
             "relevan_final", "flag_kerusuhan", "flag_berita_perbaikan", "flag_kw_jalan_rusak", "flag_luar_jakarta",
             "kota", "kecamatan", "kelurahan", "adm4_pcode", "level_lokasi", "lokasi_ambigu",
             "favorite_count", "retweet_count", "reply_count", "quote_count", "engagement", "image_url"]
    df = df[kolom].sort_values("created_at")
    df.to_csv(f"{OUTPUT_DIR}/keluhan_fasilitas_bersih.csv", index=False)

    # File labeling manual: semua yang belum dilabeli, kandidat & perlu_cek di atas
    urut = {"perlu_cek": 0, "kandidat_relevan": 1, "tidak_relevan": 2}
    lab = df[df["label_manual"].isna()].copy()
    lab["_u"] = lab["relevansi_rule"].map(urut)
    lab = lab.sort_values(["_u", "created_at"])[["id_str", "kategori", "relevansi_rule", "full_text"]]
    lab["label"] = ""
    lab["id_str"] = "id_" + lab["id_str"]   # prefix agar Excel tidak mengubah ID 19 digit jadi format ilmiah
    lab.to_csv(f"{OUTPUT_DIR}/untuk_dilabeli.csv", index=False, encoding="utf-8-sig")

    # Agregat per wilayah-periode (hanya yang relevan & berlokasi)
    rel = df[df["relevan_final"].isin(["kandidat_relevan", "relevan"]) & ~df["flag_kerusuhan"]]
    for level in ["kota", "kecamatan", "kelurahan"]:
        sub = rel[rel[level].notna()]
        if sub.empty:
            continue
        keys = {"kota": ["kota"], "kecamatan": ["kota", "kecamatan"],
                "kelurahan": ["kota", "kecamatan", "kelurahan", "adm4_pcode"]}[level]
        agg = sub.groupby(keys + ["periode"]).agg(
            jumlah_keluhan=("id_str", "count"), pju=("kat_pju", "sum"), trotoar=("kat_trotoar", "sum"),
            jpo=("kat_jpo", "sum"), halte=("kat_halte", "sum"), total_engagement=("engagement", "sum"),
            porsi_warga=("tipe_akun", lambda s: round((s == "warga").mean(), 2)),
        ).reset_index()
        if level == "kelurahan" and POPULASI_CSV and os.path.exists(POPULASI_CSV):
            pop = pd.read_csv(POPULASI_CSV, dtype={"adm4_pcode": str})
            agg = agg.merge(pop[["adm4_pcode", "penduduk_2025_est", "area_sqkm", "kepadatan_2025_est"]],
                            on="adm4_pcode", how="left")
            agg["keluhan_per_100rb"] = (agg["jumlah_keluhan"] / agg["penduduk_2025_est"] * 1e5).round(2)
            print(f"[info] Data penduduk digabung ke agregat kelurahan ({POPULASI_CSV})")
        agg.to_csv(f"{OUTPUT_DIR}/agregat_{level}_{PERIODE_AGREGASI}.csv", index=False)

    # Cek irisan dengan dataset jalan rusak
    irisan = None
    if JALAN_RUSAK_CSV and os.path.exists(JALAN_RUSAK_CSV):
        jr = pd.read_csv(JALAN_RUSAK_CSV, dtype=str, usecols=["id_str"])
        irisan = int(df["id_str"].isin(jr["id_str"]).sum())

    # Ringkasan untuk bagian Data Understanding
    L = ["# Ringkasan Data Understanding", "", "## Alur pembersihan", "", "| Tahap | Jumlah baris |", "| --- | --- |"]
    L += [f"| {a} | {b} |" for a, b in funnel]
    def tabel(seri, judul):
        out = ["", f"## {judul}", "", "| Nilai | Jumlah |", "| --- | --- |"]
        return out + [f"| {i} | {v} |" for i, v in seri.items()]
    L += tabel(df["kategori"].value_counts(), "Kategori (setelah pembersihan)")
    L += tabel(df["relevansi_rule"].value_counts(), "Pre-label relevansi (aturan)")
    L += tabel(df["tipe_akun"].value_counts(), "Tipe akun")
    L += tabel(df["level_lokasi"].value_counts(), "Level lokasi yang berhasil diekstrak")
    L += tabel(rel["tahun"].value_counts().sort_index(), "Kandidat relevan per tahun (tanpa konteks kerusuhan)")
    L += tabel(rel["kota"].value_counts(dropna=False), "Kandidat relevan per kota")
    L += tabel(df["tipe_akun"].where(df["tipe_akun"] == "warga", "media_resmi").groupby(df["kota"].fillna("tanpa lokasi")).value_counts().unstack(fill_value=0).astype(str).agg(" / ".join, axis=1), "Media-resmi / warga per kota (cek bias sumber)")
    if validasi:
        L += ["", "## Validasi pre-label aturan terhadap label manual", ""] + validasi
    L += ["", "## Flag", "",
          f"- Konteks kerusuhan: {int(df['flag_kerusuhan'].sum())}",
          f"- Berita perbaikan: {int(df['flag_berita_perbaikan'].sum())}",
          f"- Menyebut kota di luar Jakarta: {int(df['flag_luar_jakarta'].sum())}",
          f"- Mengandung keyword jalan rusak: {int(df['flag_kw_jalan_rusak'].sum())}",
          f"- Irisan ID dengan dataset jalan rusak: {irisan if irisan is not None else 'belum dicek (isi JALAN_RUSAK_CSV)'}",
          "", f"Rentang waktu: {df['created_at'].min():%Y-%m-%d} s.d. {df['created_at'].max():%Y-%m-%d}"]
    with open(f"{OUTPUT_DIR}/ringkasan_data_understanding.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    print("\n".join(L))
    print(f"\n[selesai] Output tersimpan di folder {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
