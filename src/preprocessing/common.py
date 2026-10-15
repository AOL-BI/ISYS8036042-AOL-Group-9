"""Fungsi bersama untuk semua preprocessing data tweet AOL Group 9.

Dipakai oleh preprocess_jalan_rusak.py, dan bisa di-import script lain:
    from common import bersihkan_teks, Gazetteer, ...

Isi:
  - PATH      : semua path dihitung dari root repo, jadi script bisa dijalankan dari folder mana pun
                (lokal maupun Colab setelah repo di-clone).
  - load_tweets : baca CSV hasil tweet-harvest + catat asal file.
  - bersihkan_teks / siapkan_stemmer : cleaning, normalisasi slang, stopword + stemming (Sastrawi, opsional).
  - tipe_akun : warga vs media_resmi (berita, instansi, radio, polisi lalu lintas).
  - Gazetteer : ekstraksi lokasi dari teks -> kelurahan / kecamatan / kota (gazetteer BPS-HDX 261 kelurahan),
                ditambah nama kawasan/jalan terkenal yang bukan nama wilayah resmi.
  - ekstrak_nama_jalan, anonim.
"""
import glob
import hashlib
import html
import os
import re
from itertools import groupby
from pathlib import Path

import pandas as pd

# ============================== PATH ==============================
ROOT = Path(__file__).resolve().parents[2]          # src/preprocessing/common.py -> root repo
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_EXTERNAL = ROOT / "data" / "external"
GAZETTEER_CSV = DATA_EXTERNAL / "batas-wilayah" / "jakarta_kelurahan.csv"
POPULASI_CSV = DATA_EXTERNAL / "populasi" / "jakarta_populasi_kelurahan.csv"

try:  # baca .env kalau ada (ANONIM_SALT, TWEET_HARVEST_TOKEN)
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def rel(path):
    """Path relatif terhadap root repo, untuk dicatat di data & log."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


# ============================== LOAD ==============================
def load_tweets(pola_glob, sumber):
    """Baca semua CSV tweet-harvest yang cocok dengan pola (relatif ke root repo, boleh pakai **).
    Semua kolom dibaca sebagai teks supaya id_str 19 digit tidak rusak."""
    paths = sorted(glob.glob(str(ROOT / pola_glob), recursive=True))
    frames = []
    for p in paths:
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
        if not {"full_text", "id_str", "created_at", "username"} <= set(df.columns) or "urgensi" in df.columns:
            print(f"[lewati] {rel(p)}: bukan file mentah tweet-harvest")
            continue
        df["sumber"] = sumber
        df["sumber_file"] = rel(p)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["id_str"] = out["id_str"].str.replace(r"^id_", "", regex=True).str.strip()
    return out


# ============================== TEKS ==============================
SLANG = {
    "yg": "yang", "gk": "tidak", "ga": "tidak", "gak": "tidak", "nggak": "tidak", "ngga": "tidak", "enggak": "tidak",
    "tdk": "tidak", "g": "tidak", "jl": "jalan", "jln": "jalan", "udh": "sudah", "sdh": "sudah", "udah": "sudah",
    "blm": "belum", "bgt": "banget", "dgn": "dengan", "dg": "dengan", "utk": "untuk", "krn": "karena", "karna": "karena",
    "tp": "tapi", "tpi": "tapi", "jg": "juga", "aja": "saja", "sm": "sama", "dr": "dari", "lg": "lagi", "kalo": "kalau",
    "klo": "kalau", "bs": "bisa", "gelep": "gelap", "nyala": "menyala", "lbh": "lebih", "byk": "banyak", "skrg": "sekarang",
    "trs": "terus", "adlh": "adalah", "ats": "atas", "mgkn": "mungkin", "jd": "jadi", "tsb": "tersebut",
    "jkt": "jakarta", "jaksel": "jakarta selatan", "jakbar": "jakarta barat", "jaktim": "jakarta timur",
    "jakut": "jakarta utara", "jakpus": "jakarta pusat", "bolong2": "bolong bolong", "ancur": "hancur",
    "lobang": "lubang", "berlobang": "berlubang", "amblas": "ambles", "kel": "kelurahan", "kec": "kecamatan",
}


def bersihkan_teks(teks):
    """Huruf kecil, buang URL/mention/emoji/tanda baca, normalisasi slang. Kata tetap utuh (tanpa stemming)."""
    t = html.unescape(str(teks)).lower()
    t = re.sub(r"https?://\S+|www\.\S+", " ", t)
    t = re.sub(r"@\w+", " ", t)
    t = t.replace("#", " ").replace("_", " ")
    t = re.sub(r"(\w+)²", r"\1 \1", t)                    # lampu² -> lampu lampu
    t = re.sub(r"\b([a-z]+)2\b", r"\1 \1", t)             # berulang2 -> berulang berulang
    t = re.sub(r"[^a-z0-9\s]", " ", t)                    # emoji & tanda baca
    t = " ".join(SLANG.get(w, w) for w in t.split())
    return re.sub(r"\s+", " ", t).strip()


def siapkan_stemmer():
    """Fungsi stopword removal + stemming Sastrawi. Kalau Sastrawi belum terpasang, teks dikembalikan apa adanya."""
    try:
        from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
        from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
        stemmer = StemmerFactory().create_stemmer()
        stop = StopWordRemoverFactory().create_stop_word_remover()
        return lambda t: stemmer.stem(stop.remove(t))
    except ImportError:
        print("[info] Sastrawi belum terpasang (pip install Sastrawi): text_model = text_clean")
        return lambda t: t


def ada(pola, teks):
    return bool(re.search(pola, str(teks)))


# ============================== AKUN ==============================
AKUN_RESMI_MEDIA = {
    "tmcpoldametro", "beritajakarta", "binamargajakpus", "detikcom", "dkijakarta", "sonorafm92",
    "kompascom", "binamargadki", "ntmclantaspolri", "radioelshinta", "trafficjakarta",
    "binamargajaktim", "pt_transjakarta", "mediaindonesia", "metro_tv", "disperinergi", "poskodpudki",
    "ptjasamarga", "senkomcmnp", "lewatmana", "detikoto", "hariankompas", "liputan6dotcom", "antaranews",
    "kemenpu", "tempodotco", "cnnindonesia", "kumparan", "okezonenews", "republikaonline", "jawapos",
    "grok",
}
POLA_AKUN_RESMI = (r"binamarga|dinas|pemprov|pemkot|humas|polda|polres|lantas|tmc|berita|news|detik|kompas|tribun|"
                   r"tempo|radio|fm\d|tv|official|transjakarta|jasamarga|kec_|kel_|suku|sudin|info|media")


def tipe_akun(username):
    u = str(username).lower().strip()
    if u in AKUN_RESMI_MEDIA or re.search(POLA_AKUN_RESMI, u):
        return "media_resmi"
    return "warga"


# ============================== LOKASI ==============================
KOTA_ALIAS = {
    "Jakarta Pusat": ["jakarta pusat"],
    "Jakarta Utara": ["jakarta utara"],
    "Jakarta Barat": ["jakarta barat"],
    "Jakarta Selatan": ["jakarta selatan"],
    "Jakarta Timur": ["jakarta timur"],
}

# Nama kelurahan yang juga kata umum / nama tempat lain. Hanya dihitung kalau ditulis "kelurahan <nama>"
# (teks sudah dinormalisasi: "kel." -> "kelurahan"). Contoh salah tangkap: "jalan baru diaspal" -> Kel. Baru,
# "Dukuh Atas" -> Kel. Dukuh (Kramat Jati), "truk tangki" -> Kel. Tangki, "Bintaro" -> bisa Tangerang Selatan.
KELURAHAN_WAJIB_KONTEKS = {
    "baru", "gunung", "jati", "pulo", "dukuh", "gedong", "kartini", "tangki", "bangka", "guntur", "kenari",
    "serdang", "setu", "kamal", "selong", "galur", "bintaro", "cibubur", "kelapa dua", "pekayon", "gelora",
    "karet", "kramat", "senayan",
}
# Ejaan lain yang sering dipakai orang -> nama di gazetteer
ALIAS_WILAYAH = {
    "halim": "Halim Perdana Kusumah",
    "papanggo": "Papango",
    "tanjung priok": "Tanjung Priuk",   # kelurahan; kecamatan tetap Tanjung Priok
    "palmeriam": "Pal Meriem",
    "wijayakusuma": "Wijaya Kesuma",
}

# Kawasan / jalan terkenal yang bukan nama wilayah resmi -> (kota, kecamatan atau None).
# Sebagian dari daftar kawasan di notebook Fio; nama yang melintasi beberapa kota (mis. Sudirman) tidak dimasukkan.
KAWASAN = {
    "thamrin": ("Jakarta Pusat", None), "monas": ("Jakarta Pusat", "Gambir"),
    "medan merdeka": ("Jakarta Pusat", "Gambir"), "salemba": ("Jakarta Pusat", "Senen"),
    "gunung sahari": ("Jakarta Pusat", None), "kramat raya": ("Jakarta Pusat", "Senen"),
    "gbk": ("Jakarta Pusat", "Tanah Abang"), "gelora bung karno": ("Jakarta Pusat", "Tanah Abang"),
    "sunter": ("Jakarta Utara", "Tanjung Priok"), "priok": ("Jakarta Utara", "Tanjung Priok"),
    "yos sudarso": ("Jakarta Utara", None), "boulevard raya": ("Jakarta Utara", "Kelapa Gading"),
    "gedong panjang": ("Jakarta Utara", "Penjaringan"), "plumpang": ("Jakarta Utara", None),
    "enggano": ("Jakarta Utara", "Tanjung Priok"),
    "s parman": ("Jakarta Barat", None), "daan mogot": ("Jakarta Barat", None), "roxy": ("Jakarta Barat", None),
    "kedoya": ("Jakarta Barat", "Kebon Jeruk"), "meruya": ("Jakarta Barat", "Kembangan"),
    "tanjung duren": ("Jakarta Barat", "Grogol Petamburan"), "kota tua": ("Jakarta Barat", None),
    "kemang": ("Jakarta Selatan", "Mampang Prapatan"), "mampang": ("Jakarta Selatan", "Mampang Prapatan"),
    "blok m": ("Jakarta Selatan", "Kebayoran Baru"), "senopati": ("Jakarta Selatan", "Kebayoran Baru"),
    "radio dalam": ("Jakarta Selatan", "Kebayoran Baru"), "warung buncit": ("Jakarta Selatan", "Mampang Prapatan"),
    "pondok indah": ("Jakarta Selatan", "Kebayoran Lama"), "rasuna said": ("Jakarta Selatan", "Setia Budi"),
    "kuningan": ("Jakarta Selatan", None), "semanggi": ("Jakarta Selatan", "Setia Budi"),
    "pejaten": ("Jakarta Selatan", "Pasar Minggu"), "cipete": ("Jakarta Selatan", None),
    "fatmawati": ("Jakarta Selatan", None), "antasari": ("Jakarta Selatan", None),
    "gatot subroto": ("Jakarta Selatan", None), "gatsu": ("Jakarta Selatan", None),
    "simatupang": ("Jakarta Selatan", None), "casablanca": ("Jakarta Selatan", None),
    "kebayoran": ("Jakarta Selatan", None),
    "otista": ("Jakarta Timur", "Jatinegara"), "kebon nanas": ("Jakarta Timur", "Jatinegara"),
    "pramuka": ("Jakarta Timur", None), "buaran": ("Jakarta Timur", "Duren Sawit"),
    "radjiman": ("Jakarta Timur", None), "kalimalang": ("Jakarta Timur", None),
    "pulomas": ("Jakarta Timur", "Pulo Gadung"), "kampung rambutan": ("Jakarta Timur", "Ciracas"),
}

POLA_LUAR_JAKARTA = (
    r"\b(depok|bogor|bekasi|tangerang|tangsel|cikarang|ciputat|sawangan|pondok gede|karawang|cikampek|bandung|"
    r"cirebon|sukabumi kota|surabaya|medan(?! merdeka)|semarang|yogyakarta|jogja|makassar|palembang|lampung|"
    r"cimahi|banten|purwakarta|subang|pantura|japek|bocimi|merak|sumatra|sumatera|kalimantan|papua|aceh|"
    r"jawa barat|jabar|jawa tengah|jateng|jawa timur|jatim)\b"
)


_ARAH = {"arah", "menuju", "ke", "dari", "perbatasan", "sampai", "hingga", "tujuan", "jurusan", "via", "dan", "atau"}


def sebut_luar_jakarta(teks):
    """True bila teks menyebut daerah di luar DKI sebagai lokasi, bukan sekadar arah
    ("jalan raya lenteng agung arah depok" -> False, "kabupaten lebak banten" -> True)."""
    teks = str(teks)
    for m in re.finditer(POLA_LUAR_JAKARTA, teks):
        sebelum = teks[:m.start()].split()[-2:]
        if not (set(sebelum) & _ARAH):
            return True
    return bool(re.search(r"\bkabupaten\b", teks))


def _pola_nama(nama):
    """Regex toleran spasi: 'kali deres' cocok dengan 'kalideres' dan sebaliknya."""
    return r"\b" + r"\s?".join(re.escape(w) for w in nama.lower().split()) + r"\b"


def _kunci(nama):
    return re.sub(r"\s+", "", str(nama).lower())


def _bersihkan_kota(nama):
    return re.sub(r"^(kota|kabupaten)( administrasi)?\s+", "", str(nama).strip(), flags=re.I)


class Gazetteer:
    """Ekstraksi lokasi dari teks yang sudah dibersihkan (huruf kecil, tanpa tanda baca).

    Urutan prioritas: kelurahan > kecamatan > kawasan terkenal > nama kota.
    Nama terpanjang dicocokkan lebih dulu dan bagian teksnya ditutup, supaya 'kramat jati' tidak lagi
    memicu kelurahan 'kramat'. Lokasi selalu diambil dari isi tweet, bukan dari query scraping.
    """

    def __init__(self, path=GAZETTEER_CSV):
        g = pd.read_csv(path, dtype=str)
        g = g.rename(columns={"adm4_name": "kelurahan", "adm3_name": "kecamatan", "adm2_name": "kota",
                              "adm4_pcode": "adm4_pcode", "adm3_pcode": "adm3_pcode"})
        g["kota"] = g["kota"].map(_bersihkan_kota)
        g = g[~g["kota"].str.contains("seribu", case=False, na=False)]
        self.tabel = g
        entri = []   # (kunci, pola, kota, kecamatan, kelurahan, adm4_pcode, level)
        for kota, kec in g[["kota", "kecamatan"]].drop_duplicates().itertuples(index=False):
            entri.append((_kunci(kec), _pola_nama(kec), kota, kec, None, None, "kecamatan"))
        for r in g.itertuples(index=False):
            nama = r.kelurahan.lower()
            pola = _pola_nama(r.kelurahan)
            if nama in KELURAHAN_WAJIB_KONTEKS:
                pola = r"\bkelurahan\s+" + pola[2:]
            entri.append((_kunci(r.kelurahan), pola, r.kota, r.kecamatan, r.kelurahan, r.adm4_pcode, "kelurahan"))
        for alias, resmi in ALIAS_WILAYAH.items():
            for r in g[g["kelurahan"] == resmi].itertuples(index=False):
                entri.append((_kunci(alias), _pola_nama(alias), r.kota, r.kecamatan, r.kelurahan, r.adm4_pcode,
                              "kelurahan"))
        self.entri = sorted(entri, key=lambda e: (-len(e[0]), e[0]))
        self.kawasan = sorted(KAWASAN.items(), key=lambda kv: -len(kv[0]))
        print(f"[info] Gazetteer: {g['kecamatan'].nunique()} kecamatan, {len(g)} kelurahan, "
              f"{len(KAWASAN)} kawasan")

    def ekstrak(self, teks):
        """Kembalikan dict lokasi. Dua jenis ketidakpastian dicatat terpisah:
        - ambigu_kelurahan : kecamatan pasti, kelurahan tebakan (nama kelurahan = nama kecamatannya,
                             mis. 'Pancoran', atau beberapa kelurahan dalam satu kecamatan disebut)
        - lokasi_ambigu    : tweet menyebut lebih dari satu kecamatan/kota, lokasi yang dipilih belum tentu benar
        """
        hasil = {"kota": None, "kecamatan": None, "kelurahan": None, "adm4_pcode": None,
                 "level_lokasi": "tidak_ada", "sumber_lokasi": None, "ambigu_kelurahan": False,
                 "lokasi_ambigu": False}
        teks = str(teks)
        sisa, cocok = teks, []
        for _, grup in groupby(self.entri, key=lambda e: e[0]):
            grup = list(grup)
            if re.search(grup[0][1], sisa):
                cocok.extend(grup)
                sisa = re.sub(grup[0][1], lambda m: " " * len(m.group()), sisa)
        kel = [e for e in cocok if e[6] == "kelurahan"]
        kec = [e for e in cocok if e[6] == "kecamatan"]
        kec_by_kunci = {e[0]: e for e in kec}
        # Nama yang sekaligus nama kecamatan LAIN (mis. 'Jatinegara': kelurahan di Kec. Cakung, tapi orang yang
        # menulis 'Jatinegara' hampir selalu maksudnya Kec. Jatinegara) -> baca sebagai kecamatan,
        # kecuali ditulis 'kelurahan <nama>'.
        kel = [e for e in kel
               if not (e[0] in kec_by_kunci and kec_by_kunci[e[0]][3] != e[3]
                       and not re.search(r"\bkelurahan\s+" + _pola_nama(e[4])[2:], teks))]
        semua_kec = {e[3] for e in kel} | {e[3] for e in kec}
        # Kelurahan yang namanya sama dengan kecamatan yang disebut (mis. 'jagakarsa' di "lenteng agung jagakarsa")
        # hanya dipakai kalau tidak ada kelurahan lain yang lebih spesifik.
        spesifik = [e for e in kel if e[0] not in kec_by_kunci]
        if spesifik:
            kel = spesifik
        if kel:
            pilihan = kel[0]
            if kec:  # utamakan kelurahan yang konsisten dengan kecamatan yang juga disebut
                sesuai = [e for e in kel if e[3] in {k[3] for k in kec}]
                pilihan = sesuai[0] if sesuai else pilihan
            satu_kec = {e[5] for e in kel if e[3] == pilihan[3]}
            ambigu_kel = len(satu_kec) > 1 or pilihan[0] in kec_by_kunci
            hasil.update(kota=pilihan[2], kecamatan=pilihan[3], kelurahan=pilihan[4], adm4_pcode=pilihan[5],
                         level_lokasi="kelurahan", sumber_lokasi="gazetteer", ambigu_kelurahan=ambigu_kel,
                         lokasi_ambigu=len(semua_kec) > 1)
            return hasil
        if kec:
            hasil.update(kota=kec[0][2], kecamatan=kec[0][3], level_lokasi="kecamatan", sumber_lokasi="gazetteer",
                         lokasi_ambigu=len(semua_kec) > 1)
            return hasil
        kws = [(k, v) for k, v in self.kawasan if re.search(_pola_nama(k), sisa)]
        if kws:
            kota_set = {v[0] for _, v in kws}
            kota, kecamatan = kws[0][1]
            hasil.update(kota=kota, kecamatan=kecamatan, level_lokasi="kecamatan" if kecamatan else "kota",
                         sumber_lokasi="kawasan", lokasi_ambigu=len(kota_set) > 1)
            return hasil
        for kota, alias in KOTA_ALIAS.items():
            if any(re.search(rf"\b{a}\b", teks) for a in alias):
                hasil.update(kota=kota, level_lokasi="kota", sumber_lokasi="nama_kota")
                break
        return hasil

    def ekstrak_df(self, seri_teks):
        return pd.DataFrame([self.ekstrak(t) for t in seri_teks], index=seri_teks.index)


# ============================== NAMA JALAN ==============================
_STOPWORD_JALAN = (
    r"(?:depan|deket|dekat|arah|sebelah|menuju|sampai|tepatnya|tepat|yang|yg|udah|"
    r"sudah|tolong|mohon|banget|bgt|parah|rusak|bolong|berlubang|hancur|ambles|tuh|"
    r"nih|dong|dan|cc|via|kondisi|akibat|dihimbau|himbau|pengguna|tersebut|agar|"
    r"kembali|penghubung|tampak|mulai|akan|bisa|sering|kerap|banyak|hingga|serta|"
    r"selesai|telah|oleh|untuk|pada|dari|masih|juga|hati)\b")
_KATA_BUKAN_JALAN = {"raya", "ini", "itu", "di", "ke", "jakarta"}


def ekstrak_nama_jalan(teks):
    """Ambil nama jalan setelah penanda 'Jl./Jln./Jalan' dari teks asli (dari notebook Fio)."""
    teks = re.sub(r"https?://\S+", "", str(teks))
    hasil = []
    for kandidat in re.findall(r"(?:jl\.?|jln\.?|jalan)\s+([A-Za-z0-9\.\-\s]{3,45})", teks, flags=re.I):
        kandidat = re.split(_STOPWORD_JALAN, kandidat, flags=re.I)[0]
        kandidat = re.sub(r"\s+", " ", kandidat).strip(" .-,")
        if len(kandidat) >= 3 and kandidat.lower() not in _KATA_BUKAN_JALAN:
            hasil.append(kandidat.title())
    return " ; ".join(dict.fromkeys(hasil))


# ============================== ANONIMISASI ==============================
SALT_ANONIM = os.environ.get("ANONIM_SALT", "aol-group-9")


def anonim(nilai):
    return hashlib.sha256((SALT_ANONIM + str(nilai)).encode()).hexdigest()[:12]
