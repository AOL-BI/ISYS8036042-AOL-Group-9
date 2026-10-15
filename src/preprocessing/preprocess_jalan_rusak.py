"""Preprocessing gabungan keluhan jalan rusak DKI Jakarta (project kelompok AOL Group 9).

Menyatukan tiga preprocessing personal:
  - Fio   : filter "yang rusak memang jalan", pemisahan keluhan vs laporan perbaikan, buang trotoar/JPO/tol,
            ekstraksi nama jalan, pedoman + aturan label urgensi (Tinggi/Sedang/Rendah)
  - Mail  : cleaning + slang, tipe akun (warga vs media/resmi), ekstraksi lokasi sampai kelurahan (gazetteer BPS),
            agregat per wilayah + penduduk, anonimisasi
  - Angel : fitur waktu (jam, hari, akhir pekan)

Cara pakai (dari folder mana pun, lokal atau Colab setelah repo di-clone):
    pip install -r requirements.txt
    python src/preprocessing/preprocess_jalan_rusak.py

Input  (semua relatif ke root repo, atur di CONFIG):
    data/raw/fio/*.csv                  hasil scraping awal Fio
    data/raw/jalan_rusak_v2/**/*.csv    hasil scraping ulang per kecamatan (src/scraping/generate_queries.py)
    data/raw/mail/*.csv, data/raw/angel/*.csv
                                        hanya tweet yang menyebut jalan rusak yang diambil
    data/raw/labels/*.csv               label urgensi manual (kolom id_str, urgensi), opsional
    data/external/...                   gazetteer kelurahan + estimasi penduduk
Output (data/processed/jalan_rusak/):
    keluhan_jalan_rusak.csv     data utama untuk modeling (satu baris = satu keluhan)
    laporan_perbaikan.csv       publikasi perbaikan oleh instansi (layer pembanding)
    semua_kandidat.csv          semua baris setelah pembersihan dasar + alasan dibuang (audit)
    untuk_dilabeli.csv          keluhan yang belum punya label manual, siap diisi
    agregat_kelurahan.csv       261 kelurahan (termasuk yang 0 keluhan) + penduduk
    agregat_kecamatan.csv       42 kecamatan
    ringkasan.md                angka untuk bagian Data Understanding
"""
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DATA_PROCESSED, GAZETTEER_CSV, POPULASI_CSV, ROOT, Gazetteer, ada, anonim,  # noqa: E402
                    bersihkan_teks, ekstrak_nama_jalan, load_tweets, rel, sebut_luar_jakarta, siapkan_stemmer,
                    tipe_akun)

# ============================== CONFIG ==============================
# (pola glob relatif root repo, nama sumber, wajib_keyword_jalan_rusak)
SUMBER_DATA = [
    ("data/raw/fio/*.csv", "fio_awal", False),
    ("data/raw/jalan_rusak_v2/**/*.csv", "scrape_kecamatan", False),
    ("data/raw/mail/*.csv", "mail_fasilitas", True),
    ("data/raw/angel/*.csv", "angel_kemacetan", True),
]
LABEL_GLOB = ["data/raw/labels/*.csv", "data/raw/fio/label*.csv"]
OUTPUT_DIR = DATA_PROCESSED / "jalan_rusak"
TAHUN_MIN = 2019
BAHASA = {"in"}                     # kode lang X yang dipertahankan
BUANG_TROTOAR_JPO = True
BUANG_TOL = True                    # jalan tol dikelola Jasa Marga, bukan Bina Marga
BOBOT_URGENSI = {"Tinggi": 3, "Sedang": 2, "Rendah": 1}

# ============================== POLA (dari notebook Fio) ==============================
KW_JALAN_RUSAK = (r"\b(?:jalan|jalanan|jln|jl|aspal|ruas)\s+(?:\w+\s+){0,2}(?:rusak|berlubang|bolong|ambles|amblas|"
                  r"hancur|bergelombang|retak|menganga)\b|\blubang\s+(?:di\s+)?jalan")
JALAN = r"(?:jalanan|jalan|jln\.?|jl\.?|aspal|ruas|badan jalan|beton|cor)"
RUSAK = r"(?:rusak|berlubang|bolong|lubang|ambles|amblas|retak|bergelombang|menganga|keriting|gronjal|hancur)"
OBJEK_LAIN = (
    r"(?:jpo|jembatan penyeberangan|jembatan penyebrangan|jembatan|cctv|kamera|"
    r"sekolah|gedung|warteg|kios|lapak|gardu|halte|kabel|pagar|atap|plafon|rumah|"
    r"ruko|bus|truk|mobil|motor|kereta|krl|kapal|saluran|got|trotoar|kanstin|"
    r"barrier|lampu|pju|tiang|billboard|baliho|spanduk|taman|pot|median|tanaman|"
    r"ac|mesin|ban|kendaraan|hp|laptop|kamar|kantor|pabrik|rem|kopling|aki)"
)
RE_LOKATIF = re.compile(r"(?:\bdi\b|\bpada\b|\bsepanjang\b|\bkawasan\b|\bdepan\b|\bseberang\b|"
                        r"\bsekitar\b|\bdekat\b|\barah\b)\s*$", re.I)
RE_RUSAK = re.compile(rf"\b{RUSAK}\b", re.I)
RE_JALAN = re.compile(rf"\b{JALAN}\b", re.I)
RE_OBJEK = re.compile(rf"\b{OBJEK_LAIN}\b", re.I)
RE_MAJU = re.compile(rf"^[ ,]*(?:di|pada|pd)?\s*(?:ruas\s+)?{JALAN}\b", re.I)
RE_IDIOM = re.compile(
    r"\b(?:siang bolong|tembok bolong|gali lubang|tutup lubang|lubang berjalan|"
    r"jalan kaki|jalan-jalan|jalan2|turun ke jalan|jalan hidup|jalan cerita|"
    r"jalan keluar|jalan tengah|jalan pintas|jalan buntu|jalan damai|"
    r"jalan panjang|jalan terus|jalan pikiran|setengah jalan|jalan sehat|"
    r"jalan santai|sepanjang jalan|karang bolong)\b", re.I)
RE_PERBAIKAN = re.compile(
    r"\b(?:diperbaiki|perbaikan|memperbaiki|perbaiki|ditambal|penambalan|menambal|"
    r"diaspal|pengaspalan|rampung|selesai dikerjakan|pasukan kuning|satgas|coldmix|"
    r"sudah diperbaiki|dikerjakan|pemeliharaan rutin|sudin bina marga|"
    r"suku dinas bina marga|sdbm|pengaturan dan pengamanan)\b", re.I)
RE_KELUHAN = re.compile(
    r"\b(?:tolong|mohon|keluhan|dikeluhkan|mengeluh|kapan|belum juga|tak kunjung|"
    r"tidak kunjung|dibenerin|segera|minta|rawan|bahaya|membahayakan|hati-?hati|"
    r"hati2|waspada|korban|tewas|meninggal|kecelakaan|please)\b", re.I)
RE_TROTOAR_JPO = re.compile(r"\b(?:trotoar|jpo|jembatan penyeberangan|jembatan penyebrangan|flyover|fly over|"
                            r"jembatan layang)\b", re.I)
RE_TOL = re.compile(r"\b(?:tol|jorr|japek|wiyoto)\b", re.I)
RE_JAKARTA = r"\b(?:jakarta|dki)\b"

SINYAL_URGENSI = {
    "Tinggi": {
        "korban jiwa": r"(?:tewas|newas|meninggal|wafat|korban jiwa|meregang nyawa)",
        "korban luka": r"(?:luka|dilarikan ke rumah sakit|patah tulang|dirawat)",
        "kecelakaan": r"(?:kecelak\W*an|laka|terjatuh|jatuh|terpelanting|tertabrak|menabrak|terperosok|kejeblos|"
                      r"kejebos|oleng)",
        "jalan ambles": r"(?:ambles|amblas|amblus|longsor|runtuh|ambruk|badan jalan hilang)",
        "lubang parah": r"(?:lubang\s+(?:dalam|besar|menganga|raksasa)|menganga|sedalam|kubangan)",
        "jalan ditutup": r"(?:ditutup|penutupan jalan|pengalihan rute|penyesuaian rute|dialihkan|"
                         r"rekayasa lalu lintas)",
    },
    "Sedang": {
        "rawan atau bahaya": r"(?:rawan|bahaya|membahayakan|berbahaya|mengancam|ancaman|celaka)",
        "imbauan hati-hati": r"(?:hati\W*hati|hati\W*2|hati\W*²|waspada|awas|dihimbau|diimbau|pelan\W*pelan)",
        "gangguan lalu lintas": r"(?:macet|tersendat|padat|penyempitan|menyempit|antrean|antrian|kemacetan|"
                                r"menghindari)",
        "permintaan perbaikan": r"(?:tolong|mohon|segera|dibenerin|harap cepat|kapan diperbaiki|tak kunjung|"
                                r"belum juga|jangan tunggu)",
        "kerusakan parah": r"(?:rusak parah|parah|hancur|ancur)",
    },
    "Rendah": {
        "kerusakan ringan": r"(?:retak|bergelombang|lubang kecil|keriting|gronjal)",
        "pemberitaan agregat": r"(?:\d[\d\.\,]*\s*(?:titik|ruas|km|kilometer)|persen)",
    },
}


# ============================== FUNGSI ==============================
def subjek_adalah_jalan(teks):
    """True bila kata kerusakan memang merujuk ke jalan, bukan benda lain di jalan (notebook Fio).
    "CCTV di Jalan Pejompongan rusak" -> subjeknya CCTV, bukan jalan."""
    teks = re.sub(r"https?://\S+", " ", str(teks))
    if RE_IDIOM.search(teks):
        return False
    for m in RE_RUSAK.finditer(teks):
        if RE_MAJU.match(teks[m.end():m.end() + 40]):
            return True
        jendela = re.split(r"[.!?\n]", teks[max(0, m.start() - 90):m.start()])[-1]
        jalan = list(RE_JALAN.finditer(jendela))
        objek = list(RE_OBJEK.finditer(jendela))
        if not jalan:
            continue
        jalan_akhir = jalan[-1]
        objek_akhir = objek[-1] if objek else None
        jalan_lokatif = bool(RE_LOKATIF.search(jendela[:jalan_akhir.start()]))
        if objek_akhir is None:
            if not jalan_lokatif:
                return True
            continue
        objek_lokatif = bool(RE_LOKATIF.search(jendela[:objek_akhir.start()]))
        if objek_lokatif and not jalan_lokatif:
            return True
        if objek_akhir.start() > jalan_akhir.start() or jalan_lokatif:
            continue
        return True
    return False


def label_urgensi_aturan(teks):
    """Urgensi dari kata penanda. Tinggi menang atas Sedang, Sedang atas Rendah. None = tanpa penanda."""
    t = re.sub(r"https?://\S+", " ", str(teks))
    for kelas, kamus in SINYAL_URGENSI.items():
        if any(re.search(p, t, re.I) for p in kamus.values()):
            return kelas
    return None


def muat_label_manual():
    """Gabung semua file label (id_str, urgensi). File belakangan menimpa yang di depan."""
    import glob
    frames = []
    for pola in LABEL_GLOB:
        for p in sorted(glob.glob(str(ROOT / pola))):
            lm = pd.read_csv(p, dtype=str, keep_default_na=False)
            if not {"id_str", "urgensi"} <= set(lm.columns):
                print(f"[lewati] {rel(p)}: tidak ada kolom id_str + urgensi")
                continue
            lm["id_str"] = lm["id_str"].str.replace(r"^id_", "", regex=True).str.strip()
            lm["urgensi"] = lm["urgensi"].str.strip().str.capitalize().replace(
                {"Tidak_relevan": "tidak_relevan", "Tidak relevan": "tidak_relevan"})
            lm = lm[lm["urgensi"].isin(["Tinggi", "Sedang", "Rendah", "tidak_relevan"])]
            print(f"[info] Label manual {rel(p)}: {len(lm)} baris")
            frames.append(lm[["id_str", "urgensi"]])
    if not frames:
        print("[info] Belum ada file label manual (taruh di data/raw/labels/, kolom id_str + urgensi)")
        return pd.DataFrame(columns=["id_str", "urgensi"])
    return pd.concat(frames).drop_duplicates("id_str", keep="last")


def tabel_md(seri, judul, kolom="Jumlah"):
    out = ["", f"## {judul}", "", f"| Nilai | {kolom} |", "| --- | --- |"]
    return out + [f"| {i} | {v} |" for i, v in seri.items()]


# ============================== PIPELINE ==============================
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    funnel = []

    # 1. Load semua sumber
    frames, per_sumber = [], {}
    for pola, sumber, wajib_kw in SUMBER_DATA:
        df = load_tweets(pola, sumber)
        if df.empty:
            print(f"[info] {pola}: tidak ada file")
            continue
        n_awal = len(df)
        if wajib_kw:
            df = df[df["full_text"].str.lower().str.contains(KW_JALAN_RUSAK, regex=True)]
        per_sumber[sumber] = (n_awal, len(df))
        print(f"[info] {sumber}: {n_awal} baris dari {df['sumber_file'].nunique() if len(df) else 0} file"
              + (f", {len(df)} menyebut jalan rusak" if wajib_kw else ""))
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    funnel.append(("Data mentah gabungan", len(df)))

    # 2. Pembersihan dasar
    df = df.drop_duplicates("id_str", keep="first")       # urutan SUMBER_DATA = prioritas sumber
    funnel.append(("Setelah hapus duplikat ID", len(df)))
    df = df[~df["full_text"].str.strip().str.startswith("RT @")]
    funnel.append(("Setelah buang retweet", len(df)))
    df = df[df["lang"].isin(BAHASA)]
    funnel.append(("Setelah buang bahasa non-Indonesia", len(df)))

    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, format="mixed").dt.tz_convert("Asia/Jakarta")
    df = df.sort_values("created_at")
    df["text_clean"] = df["full_text"].map(bersihkan_teks)
    df = df.drop_duplicates("text_clean", keep="first")
    funnel.append(("Setelah buang teks kembar", len(df)))
    df = df[df["created_at"].dt.year >= TAHUN_MIN].copy()
    funnel.append((f"Tahun {TAHUN_MIN} ke atas", len(df)))

    # 3. Atribut: akun, lokasi, flag
    df["tipe_akun"] = df["username"].map(tipe_akun)
    gaz = Gazetteer(GAZETTEER_CSV)
    df = df.join(gaz.ekstrak_df(df["text_clean"]))
    df["nama_jalan"] = df["full_text"].map(ekstrak_nama_jalan)
    # Status wilayah (aturan Fio): tweet yang menyebut daerah luar DKI (bukan sekadar arah, mis. "arah depok")
    # dibuang kecuali ada lokasi DKI yang jelas. Lokasi DKI kalah kalau tweet menyebut kabupaten dan tidak
    # menyebut Jakarta sama sekali (mis. "jalan desa cilangkap kabupaten lebak banten").
    df["flag_luar_jakarta"] = df["text_clean"].map(sebut_luar_jakarta)
    sebut_jakarta = df["text_clean"].map(lambda t: ada(RE_JAKARTA, t))
    ada_lokasi = df["level_lokasi"] != "tidak_ada"
    kabupaten = df["text_clean"].str.contains(r"\bkabupaten\b")
    df["status_wilayah"] = "tanpa_lokasi"
    df.loc[sebut_jakarta, "status_wilayah"] = "jakarta_umum"
    df.loc[ada_lokasi, "status_wilayah"] = "dki"
    luar = df["flag_luar_jakarta"] & (~ada_lokasi | (kabupaten & ~sebut_jakarta))
    df.loc[luar, "status_wilayah"] = "luar_jakarta"
    df.loc[df["flag_luar_jakarta"] & ada_lokasi & ~luar, "lokasi_ambigu"] = True

    df["subjek_jalan"] = df["full_text"].map(subjek_adalah_jalan)
    df["jenis"] = "keluhan"
    perbaikan = df["full_text"].str.contains(RE_PERBAIKAN) & ~df["full_text"].str.contains(RE_KELUHAN)
    df.loc[perbaikan, "jenis"] = "laporan_perbaikan"
    df["flag_trotoar_jpo"] = df["full_text"].str.contains(RE_TROTOAR_JPO)
    df["flag_tol"] = df["full_text"].str.contains(RE_TOL)

    # Alasan dibuang (urutan sama dengan notebook Fio), dicatat bukan langsung dihapus supaya bisa diaudit
    df["alasan_dibuang"] = ""
    aturan = [
        (~df["status_wilayah"].isin(["dki", "jakarta_umum"]), "bukan_wilayah_dki"),
        (~df["subjek_jalan"], "subjek_bukan_jalan"),
        (df["flag_trotoar_jpo"] & BUANG_TROTOAR_JPO, "trotoar_jpo_flyover"),
        (df["flag_tol"] & BUANG_TOL, "jalan_tol"),
    ]
    for mask, alasan in aturan:
        df.loc[mask & (df["alasan_dibuang"] == ""), "alasan_dibuang"] = alasan
    lolos = df["alasan_dibuang"] == ""
    funnel.append(("Wilayah DKI Jakarta", int((df["status_wilayah"].isin(["dki", "jakarta_umum"])).sum())))
    funnel.append(("Subjek kerusakan = jalan", int((df["alasan_dibuang"].isin(["", "trotoar_jpo_flyover",
                                                                                "jalan_tol"])).sum())))
    funnel.append(("Tanpa trotoar/JPO/flyover dan jalan tol", int(lolos.sum())))

    # 4. Teks model, waktu, engagement, label
    stem = siapkan_stemmer()
    df["text_model"] = ""
    df.loc[lolos, "text_model"] = df.loc[lolos, "text_clean"].map(stem)
    df["tahun"] = df["created_at"].dt.year
    df["bulan"] = df["created_at"].dt.month
    df["periode"] = df["created_at"].dt.strftime("%Y-%m")
    df["jam"] = df["created_at"].dt.hour
    df["hari"] = df["created_at"].dt.day_name()
    df["akhir_pekan"] = df["created_at"].dt.dayofweek >= 5
    for c in ["favorite_count", "retweet_count", "reply_count", "quote_count"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    df["engagement"] = df[["favorite_count", "retweet_count", "reply_count", "quote_count"]].sum(axis=1)
    df["ada_gambar"] = df["image_url"].astype(str).str.strip() != ""
    df["panjang_teks"] = df["text_clean"].str.split().str.len()

    df["urgensi_aturan"] = df["full_text"].map(label_urgensi_aturan)
    lm = muat_label_manual()
    df = df.merge(lm.rename(columns={"urgensi": "urgensi_manual"}), on="id_str", how="left")
    df["urgensi"] = df["urgensi_manual"].fillna(df["urgensi_aturan"])
    df["sumber_label"] = None
    df.loc[df["urgensi_aturan"].notna(), "sumber_label"] = "aturan"
    df.loc[df["urgensi_manual"].notna(), "sumber_label"] = "manual"
    tidak_relevan = (df["urgensi_manual"] == "tidak_relevan") & (df["alasan_dibuang"] == "")
    df.loc[tidak_relevan, "alasan_dibuang"] = "label_manual_tidak_relevan"
    lolos = df["alasan_dibuang"] == ""

    # 5. Anonimisasi
    df["user_hash"] = df["user_id_str"].map(anonim)
    df["akun_media"] = df["username"].where(df["tipe_akun"] == "media_resmi", "")
    df["created_at"] = df["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S")

    kolom = ["id_str", "created_at", "tahun", "bulan", "periode", "jam", "hari", "akhir_pekan", "sumber",
             "tipe_akun", "akun_media", "user_hash", "jenis", "full_text", "text_clean", "text_model", "panjang_teks",
             "kota", "kecamatan", "kelurahan", "adm4_pcode", "level_lokasi", "sumber_lokasi", "ambigu_kelurahan", "lokasi_ambigu",
             "nama_jalan", "status_wilayah", "flag_luar_jakarta", "urgensi_manual", "urgensi_aturan", "urgensi",
             "sumber_label", "favorite_count", "retweet_count", "reply_count", "quote_count", "engagement",
             "ada_gambar"]
    audit = ["subjek_jalan", "flag_trotoar_jpo", "flag_tol", "alasan_dibuang", "sumber_file"]
    df[kolom + audit].to_csv(OUTPUT_DIR / "semua_kandidat.csv", index=False)

    keluhan = df[lolos & (df["jenis"] == "keluhan")][kolom]
    perbaikan = df[lolos & (df["jenis"] == "laporan_perbaikan")][kolom]
    funnel.append(("Keluhan (tanpa laporan perbaikan)", len(keluhan)))
    keluhan.to_csv(OUTPUT_DIR / "keluhan_jalan_rusak.csv", index=False)
    perbaikan.to_csv(OUTPUT_DIR / "laporan_perbaikan.csv", index=False)

    # 6. File untuk labeling manual: belum berlabel manual, data baru dulu, yang ada lokasinya di atas
    lab = keluhan[keluhan["urgensi_manual"].isna()].copy()
    lab["_lok"] = (lab["level_lokasi"] == "tidak_ada").astype(int)
    lab = lab.sort_values(["_lok", "created_at"], ascending=[True, False])
    lab = lab[["id_str", "sumber", "kota", "kecamatan", "kelurahan", "urgensi_aturan", "full_text"]]
    lab["urgensi"] = ""
    lab["id_str"] = "id_" + lab["id_str"]     # prefix supaya Excel tidak merusak ID 19 digit
    lab.to_csv(OUTPUT_DIR / "untuk_dilabeli.csv", index=False, encoding="utf-8-sig")

    # 7. Agregat wilayah (semua wilayah ikut, termasuk yang 0 keluhan, supaya peta lengkap)
    def agregat(data, kunci):
        g = data.groupby(kunci)
        out = pd.DataFrame({
            "jumlah_keluhan": g.size(),
            "keluhan_warga": g["tipe_akun"].apply(lambda s: int((s == "warga").sum())),
            "ambigu_kelurahan": g["ambigu_kelurahan"].apply(lambda s: int(s.astype(bool).sum())),
            "lokasi_ambigu": g["lokasi_ambigu"].apply(lambda s: int(s.astype(bool).sum())),
            **{f"urgensi_{k.lower()}": g["urgensi"].apply(lambda s, k=k: int((s == k).sum()))
               for k in BOBOT_URGENSI},
        })
        out["skor_urgensi"] = sum(out[f"urgensi_{k.lower()}"] * b for k, b in BOBOT_URGENSI.items())
        return out

    wil = gaz.tabel
    pop = pd.read_csv(POPULASI_CSV, dtype={"adm4_pcode": str}) if POPULASI_CSV.exists() else None

    kel = wil[["adm4_pcode", "kelurahan", "kecamatan", "kota"]].copy()
    if pop is not None:
        kel = kel.merge(pop[["adm4_pcode", "penduduk_2025_est", "area_sqkm", "kepadatan_2025_est"]],
                        on="adm4_pcode", how="left")
    a = agregat(keluhan[keluhan["adm4_pcode"].notna()], "adm4_pcode")
    p = perbaikan[perbaikan["adm4_pcode"].notna()].groupby("adm4_pcode").size().rename("laporan_perbaikan")
    kel = kel.merge(a, on="adm4_pcode", how="left").merge(p, on="adm4_pcode", how="left")
    angka = [c for c in kel.columns if c in a.columns or c == "laporan_perbaikan"]
    kel[angka] = kel[angka].fillna(0).astype(int)
    if pop is not None:
        kel["keluhan_per_100rb"] = (kel["jumlah_keluhan"] / kel["penduduk_2025_est"] * 1e5).round(2)
        kel["skor_per_100rb"] = (kel["skor_urgensi"] / kel["penduduk_2025_est"] * 1e5).round(2)
    kel.sort_values("skor_urgensi", ascending=False).to_csv(OUTPUT_DIR / "agregat_kelurahan.csv", index=False)

    kec = wil.groupby(["kota", "kecamatan"]).size().rename("jumlah_kelurahan").reset_index()
    if pop is not None:
        pk = pop.groupby("adm3_name")[["penduduk_2025_est", "area_sqkm"]].sum().round(2).reset_index()
        kec = kec.merge(pk.rename(columns={"adm3_name": "kecamatan"}), on="kecamatan", how="left")
    a = agregat(keluhan[keluhan["kecamatan"].notna()], "kecamatan")
    p = perbaikan[perbaikan["kecamatan"].notna()].groupby("kecamatan").size().rename("laporan_perbaikan")
    kec = kec.merge(a, on="kecamatan", how="left").merge(p, on="kecamatan", how="left")
    angka = [c for c in kec.columns if c in a.columns or c == "laporan_perbaikan"]
    kec[angka] = kec[angka].fillna(0).astype(int)
    if pop is not None:
        kec["keluhan_per_100rb"] = (kec["jumlah_keluhan"] / kec["penduduk_2025_est"] * 1e5).round(2)
        kec["skor_per_100rb"] = (kec["skor_urgensi"] / kec["penduduk_2025_est"] * 1e5).round(2)
    kec.sort_values("skor_urgensi", ascending=False).to_csv(OUTPUT_DIR / "agregat_kecamatan.csv", index=False)

    # 8. Ringkasan
    L = ["# Ringkasan Preprocessing Keluhan Jalan Rusak", "",
         f"Rentang waktu: {keluhan['created_at'].min()} s.d. {keluhan['created_at'].max()}", "",
         "## Sumber data", "", "| Sumber | Baris mentah | Dipakai (setelah filter keyword) |", "| --- | --- | --- |"]
    L += [f"| {s} | {a_} | {b_} |" for s, (a_, b_) in per_sumber.items()]
    L += ["", "## Alur pembersihan", "", "| Tahap | Jumlah baris |", "| --- | --- |"]
    L += [f"| {a_} | {b_} |" for a_, b_ in funnel]
    L += tabel_md(df["alasan_dibuang"].replace("", "(lolos)").value_counts(), "Alasan dibuang (setelah pembersihan dasar)")
    L += tabel_md(df[lolos]["jenis"].value_counts(), "Keluhan vs laporan perbaikan")
    L += tabel_md(keluhan["sumber"].value_counts(), "Keluhan per sumber")
    L += tabel_md(keluhan["tipe_akun"].value_counts(), "Keluhan per tipe akun")
    L += tabel_md(keluhan["level_lokasi"].value_counts(), "Level lokasi keluhan")
    L += tabel_md(keluhan["sumber_lokasi"].fillna("tidak_ada").value_counts(), "Sumber lokasi keluhan")
    L += tabel_md(keluhan["kota"].fillna("(tanpa kota)").value_counts(), "Keluhan per kota")
    L += tabel_md(keluhan["tahun"].value_counts().sort_index(), "Keluhan per tahun")
    L += tabel_md(keluhan["urgensi"].fillna("(belum berlabel)").value_counts(), "Urgensi (manual > aturan)")
    L += tabel_md(keluhan["sumber_label"].fillna("(belum berlabel)").value_counts(), "Sumber label")
    n_kel = int((kel["jumlah_keluhan"] > 0).sum())
    n_kec = int((kec["jumlah_keluhan"] > 0).sum())
    L += ["", "## Cakupan wilayah", "",
          f"- Kelurahan dengan >= 1 keluhan: {n_kel} dari {len(kel)}",
          f"- Kecamatan dengan >= 1 keluhan: {n_kec} dari {len(kec)}",
          f"- Keluhan dengan kelurahan tebakan (kecamatan pasti): {int(keluhan['ambigu_kelurahan'].astype(bool).sum())}",
          f"- Keluhan yang menyebut lebih dari satu kecamatan/kota: {int(keluhan['lokasi_ambigu'].astype(bool).sum())}",
          f"- Laporan perbaikan resmi: {len(perbaikan)} (berlokasi kelurahan: "
          f"{int(perbaikan['adm4_pcode'].notna().sum())})"]
    (OUTPUT_DIR / "ringkasan.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\n[selesai] Output di {rel(OUTPUT_DIR)}/")


if __name__ == "__main__":
    main()
