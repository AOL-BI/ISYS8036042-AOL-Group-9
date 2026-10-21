"""
Pembersihan data tweet keluhan kerusakan jalan di DKI Jakarta.

Pipeline:
  1. Gabung CSV hasil scraping          5. Filter area Jakarta
  2. Deduplikasi (ID + teks)            6. Filter topik (subjek kerusakan = jalan)
  3. Buang retweet                      7. Klasifikasi jenis konten
  4. Ekstraksi lokasi (geoparsing)      8. Sampling Slovin untuk anotasi manual

Pakai:
    python src/clean_tweets.py --input data/raw --output data/processed
"""

import argparse
import glob
import math
import os
import re

import pandas as pd

# ---------------------------------------------------------------- konfigurasi
TAHUN_MIN = 2019
WILAYAH_SEKITAR = False
BUANG_LAPORAN_PERBAIKAN = True
BUANG_TROTOAR = True
BUANG_JPO = True
BUANG_TOL = True
WAJIB_LOKASI_SPESIFIK = False
MARGIN_ERROR = 0.05
RANDOM_STATE = 42

# ------------------------------------------------------------------ gazetteer
WILAYAH_KEYWORDS = {
    "Jakarta Pusat": [
        "jakarta pusat", "jakpus", "menteng", "gambir", "senen", "cempaka putih",
        "johar baru", "kemayoran", "sawah besar", "tanah abang", "medan merdeka",
        "gunung sahari", "thamrin", "monas", "pasar baru", "salemba", "kwitang",
        "kramat raya",
    ],
    "Jakarta Utara": [
        "jakarta utara", "jakut", "tanjung priok", "koja", "cilincing",
        "penjaringan", "pademangan", "kelapa gading", "sunter", "ancol",
        "marunda", "enggano", "yos sudarso", "boulevard raya", "gedong panjang",
        "plumpang",
    ],
    "Jakarta Barat": [
        "jakarta barat", "jakbar", "cengkareng", "kalideres", "grogol", "tambora",
        "taman sari", "kebon jeruk", "palmerah", "kembangan", "tomang", "slipi",
        "glodok", "s parman", "daan mogot", "kedoya", "meruya", "joglo",
        "semanan", "roxy",
    ],
    "Jakarta Selatan": [
        "jakarta selatan", "jaksel", "kebayoran", "tebet", "mampang", "pancoran",
        "jagakarsa", "pasar minggu", "cilandak", "pesanggrahan", "setiabudi",
        "kemang", "manggarai", "lenteng agung", "rawajati", "kuningan", "blok m",
        "fatmawati", "antasari", "gatot subroto", "gatsu", "simatupang",
        "radio dalam", "senopati", "casablanca", "warung buncit", "ragunan",
        "pondok indah", "rasuna said", "sudirman",
    ],
    "Jakarta Timur": [
        "jakarta timur", "jaktim", "matraman", "jatinegara", "cakung",
        "duren sawit", "kramat jati", "makasar", "pulo gadung", "pulogadung",
        "ciracas", "cipayung", "pasar rebo", "otista", "pramuka", "rawamangun",
        "klender", "cawang", "kebon nanas", "pondok bambu", "halim", "cibubur",
        "penggilingan", "buaran", "pulo gebang", "radjiman", "kalimalang",
    ],
    "Kep. Seribu": ["kepulauan seribu", "pulau seribu"],
}

KOTA_SEKITAR = ["bekasi", "tangerang", "depok", "bogor", "tangsel", "cikarang",
                "bintaro", "ciputat"]
KOTA_JAUH = ["bandung", "cirebon", "karawang", "cikampek", "sukabumi", "lampung",
             "surabaya", "semarang", "medan", "jawa tengah", "bitung", "balaraja",
             "antapani", "pantura", "japek", "bocimi", "merak", "sumatra",
             "kaltim", "papua", "aceh", "kalimantan", "jogja", "solo", "bali",
             "ntt", "flores"]

# ---------------------------------------------------------------------- regex
JALAN = r"(?:jalanan|jalan|jln\.?|jl\.?|aspal|ruas|badan jalan|beton|cor)"
RUSAK = (r"(?:rusak|berlubang|bolong|lubang|ambles|amblas|retak|bergelombang|"
         r"menganga|keriting|gronjal|hancur)")
OBJEK_LAIN = (
    r"(?:jpo|jembatan penyeberangan|jembatan penyebrangan|jembatan|cctv|kamera|"
    r"sekolah|gedung|warteg|kios|lapak|gardu|halte|kabel|pagar|atap|plafon|rumah|"
    r"ruko|bus|truk|mobil|motor|kereta|krl|kapal|saluran|got|trotoar|kanstin|"
    r"barrier|lampu|pju|tiang|billboard|baliho|spanduk|taman|pot|median|tanaman|"
    r"ac|mesin|ban|kendaraan|hp|laptop|kamar|kantor|pabrik|rem|kopling|aki)"
)

RE_LOKATIF = re.compile(
    r"(?:\bdi\b|\bpada\b|\bsepanjang\b|\bkawasan\b|\bdepan\b|\bseberang\b|"
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
    r"jalan santai|sepanjang jalan)\b", re.I)

RE_PERBAIKAN = re.compile(
    r"\b(?:diperbaiki|perbaikan|memperbaiki|perbaiki|ditambal|penambalan|menambal|"
    r"diaspal|pengaspalan|rampung|selesai dikerjakan|pasukan kuning|satgas|coldmix|"
    r"sudah diperbaiki|dikerjakan|pemeliharaan rutin|sudin bina marga|"
    r"suku dinas bina marga|sdbm|pengaturan dan pengamanan)\b", re.I)
RE_KELUHAN = re.compile(
    r"\b(?:tolong|mohon|keluhan|dikeluhkan|mengeluh|kapan|belum juga|tak kunjung|"
    r"tidak kunjung|dibenerin|segera|minta|rawan|bahaya|membahayakan|hati-?hati|"
    r"hati2|waspada|korban|tewas|meninggal|kecelakaan|please)\b", re.I)

STOPWORD_JALAN = (
    r"(?:depan|deket|dekat|arah|sebelah|menuju|sampai|tepatnya|tepat|yang|yg|udah|"
    r"sudah|tolong|mohon|banget|bgt|parah|rusak|bolong|berlubang|hancur|ambles|tuh|"
    r"nih|dong|dan|cc|via|kondisi|akibat|dihimbau|himbau|pengguna|tersebut|agar|"
    r"kembali|penghubung|tampak|mulai|akan|bisa|sering|kerap|banyak|hingga|serta|"
    r"selesai|telah|oleh|untuk|pada|dari|masih|juga|hati)\b")
KATA_BUKAN_JALAN = {"raya", "ini", "itu", "di", "ke", "jakarta"}


# ------------------------------------------------------------------- fungsi
def deteksi_wilayah(teks: str) -> str:
    """Petakan teks ke kota administrasi DKI lewat gazetteer kawasan."""
    teks = f" {str(teks).lower()} "
    cocok = [w for w, kws in WILAYAH_KEYWORDS.items() if any(k in teks for k in kws)]
    if len(cocok) == 1:
        return cocok[0]
    if len(cocok) > 1:
        return "AMBIGU: " + " | ".join(cocok)
    return ""


def cari_kota(teks: str, daftar: list) -> str:
    teks = str(teks).lower()
    return ", ".join(sorted({k for k in daftar if k in teks}))


def ekstrak_nama_jalan(teks: str) -> str:
    """Tarik nama jalan setelah penanda 'Jl./Jalan', potong di kata penanda henti."""
    teks = re.sub(r"https?://\S+", "", str(teks))
    hasil = []
    pola = r"(?:jl\.?|jln\.?|jalan)\s+([A-Za-z0-9\.\-\s]{3,45})"
    for kandidat in re.findall(pola, teks, flags=re.I):
        kandidat = re.split(STOPWORD_JALAN, kandidat, flags=re.I)[0]
        kandidat = re.sub(r"\s+", " ", kandidat).strip(" .-,")
        if len(kandidat) >= 3 and kandidat.lower() not in KATA_BUKAN_JALAN:
            hasil.append(kandidat.title())
    return " ; ".join(dict.fromkeys(hasil))


def subjek_adalah_jalan(teks: str) -> bool:
    """
    True bila ada kata kerusakan yang subjeknya memang jalan.

    Tiga aturan:
      1. Kata benda terdekat sebelum kata kerusakan jadi kandidat subjek.
      2. Frasa lokatif ("di Jalan X", "dekat gedung Y") = keterangan tempat.
      3. Pola maju ("lubang di Jalan X") tidak boleh melewati batas kalimat.
    """
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


def slovin(populasi: int, margin: float) -> int:
    return math.ceil(populasi / (1 + populasi * margin ** 2))


# ------------------------------------------------------------------- pipeline
def bersihkan(df: pd.DataFrame) -> tuple:
    log = [("1. Total mentah", len(df))]

    df = df.drop_duplicates(subset="id_str")
    log.append(("2. Dedup ID", len(df)))

    df = df[~df["full_text"].astype(str).str.strip().str.startswith("RT @")]
    log.append(("3. Buang retweet", len(df)))

    norm = df["full_text"].map(
        lambda t: re.sub(r"\s+", " ", re.sub(
            r"[^a-z0-9\s]", " ", re.sub(r"https?://\S+", "", str(t).lower()))).strip())
    df = df[~norm.duplicated()]
    log.append(("4. Buang teks kembar", len(df)))

    df["tahun"] = pd.to_datetime(df["created_at"], format="mixed", utc=True).dt.year
    if TAHUN_MIN:
        df = df[df["tahun"] >= TAHUN_MIN]
        log.append((f"5. Tahun >= {TAHUN_MIN}", len(df)))

    teks = df["full_text"].astype(str)
    df["wilayah"] = teks.map(deteksi_wilayah)
    df["sekitar"] = teks.map(lambda t: cari_kota(t, KOTA_SEKITAR))
    df["luar_jkt"] = teks.map(lambda t: cari_kota(t, KOTA_JAUH))
    df["nama_jalan"] = teks.map(ekstrak_nama_jalan)

    df["status_lokasi"] = "tanpa lokasi"
    punya_jkt = teks.str.lower().str.contains("jakarta|jkt|dki", na=False)
    df.loc[punya_jkt, "status_lokasi"] = "Jakarta (umum)"
    df.loc[df["sekitar"] != "", "status_lokasi"] = "sekitar Jakarta"
    df.loc[df["luar_jkt"] != "", "status_lokasi"] = "luar Jabodetabek"
    df.loc[df["wilayah"].str.startswith("AMBIGU"), "status_lokasi"] = "ambigu"
    df.loc[df["wilayah"].str.startswith(("Jakarta", "Kep")), "status_lokasi"] = "DKI"

    simpan = ["DKI", "Jakarta (umum)", "ambigu"]
    if WILAYAH_SEKITAR:
        simpan.append("sekitar Jakarta")
    df = df[df["status_lokasi"].isin(simpan)]
    log.append(("6. Area Jakarta", len(df)))

    df["subjek_jalan"] = df["full_text"].astype(str).map(subjek_adalah_jalan)
    terbuang = df[~df["subjek_jalan"]].copy()
    df = df[df["subjek_jalan"]]
    log.append(("7. Subjek = jalan", len(df)))

    teks2 = df["full_text"].astype(str)
    df["jenis"] = "keluhan"
    hanya_perbaikan = teks2.str.contains(RE_PERBAIKAN) & ~teks2.str.contains(RE_KELUHAN)
    df.loc[hanya_perbaikan, "jenis"] = "laporan perbaikan"
    df["trotoar"] = teks2.str.contains(r"\btrotoar\b", case=False)
    df["jpo"] = teks2.str.contains(
        r"\b(?:jpo|jembatan penyeberangan|jembatan penyebrangan|flyover|fly over|"
        r"jembatan layang)\b", case=False, regex=True)
    df["tol"] = teks2.str.contains(r"\b(?:tol|jorr|japek|wiyoto)\b",
                                   case=False, regex=True)
    df["lokasi_spesifik"] = (df["wilayah"] != "") | (df["nama_jalan"] != "")

    if BUANG_LAPORAN_PERBAIKAN:
        df = df[df["jenis"] == "keluhan"]
        log.append(("8. Buang laporan perbaikan", len(df)))
    if BUANG_TROTOAR:
        df = df[~df["trotoar"]]
        log.append(("9. Buang trotoar", len(df)))
    if BUANG_JPO:
        df = df[~df["jpo"]]
        log.append(("10. Buang JPO/flyover", len(df)))
    if BUANG_TOL:
        df = df[~df["tol"]]
        log.append(("11. Buang tol", len(df)))
    if WAJIB_LOKASI_SPESIFIK:
        df = df[df["lokasi_spesifik"]]
        log.append(("12. Wajib lokasi spesifik", len(df)))

    return df, terbuang, log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/raw", help="folder CSV hasil scraping")
    parser.add_argument("--output", default="data/processed", help="folder hasil")
    args = parser.parse_args()

    berkas = sorted(glob.glob(os.path.join(args.input, "*.csv")))
    if not berkas:
        raise SystemExit(f"Tidak ada CSV di {args.input}")
    print("File terbaca:", [os.path.basename(f) for f in berkas])

    df = pd.concat([pd.read_csv(f) for f in berkas], ignore_index=True)
    df, terbuang, log = bersihkan(df)

    print("\n=== ALUR PEMBERSIHAN ===")
    for nama, jumlah in log:
        print(f"{nama:<32}: {jumlah}")

    n_populasi = len(df)
    n_sampel = slovin(n_populasi, MARGIN_ERROR)
    print(f"\n=== DATA FINAL: {n_populasi} ===")
    print(f"Slovin (e={MARGIN_ERROR:.0%}) -> sampel anotasi manual: {n_sampel}")
    print("\n--- Wilayah ---")
    print(df["wilayah"].replace("", "(tanpa wilayah)").value_counts().to_string())

    os.makedirs(args.output, exist_ok=True)
    kolom = [c for c in ["id_str", "created_at", "tahun", "username", "lang",
                         "full_text", "wilayah", "nama_jalan", "status_lokasi",
                         "jenis", "tweet_url"] if c in df.columns]

    df[kolom].to_csv(os.path.join(args.output, "data_final.csv"), index=False)
    terbuang.to_csv(os.path.join(args.output, "terbuang_topik.csv"), index=False)

    sampel = df[kolom].sample(n=min(n_sampel, n_populasi),
                              random_state=RANDOM_STATE).copy()
    sampel["relevan"] = ""
    sampel["urgensi"] = ""
    sampel.to_csv(os.path.join(args.output, "sampel_label_manual.csv"), index=False)

    print(f"\nTersimpan di {args.output}/")


if __name__ == "__main__":
    main()
