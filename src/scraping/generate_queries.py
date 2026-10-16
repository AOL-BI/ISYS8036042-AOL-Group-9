"""Generator query scraping keluhan jalan rusak per kecamatan (tweet-harvest).

Kenapa per kecamatan: tweet yang ditemukan lewat nama tempat hampir selalu bisa dipetakan ke wilayah.
Lokasi tetap diambil dari ISI tweet saat preprocessing, bukan dari query.

Cara pakai (dari folder mana pun):
    python src/scraping/generate_queries.py                 # tampilkan semua perintah (format Colab/bash)
    python src/scraping/generate_queries.py --jalan         # + query per nama jalan utama
    python src/scraping/generate_queries.py --run           # jalankan langsung (butuh Node.js + token)
    python src/scraping/generate_queries.py --run --hanya Tebet,Cilandak --limit 300

Token: isi TWEET_HARVEST_TOKEN di file .env (root repo) atau pakai --token.
Hasil: data/raw/jalan_rusak_v2/tweets-data/jr_<nama>.csv (otomatis dibaca preprocess_jalan_rusak.py).
File yang sudah berisi data dilewati; file kosong di-scrape ulang. Kalau kena rate limit tinggal jalankan ulang.
"""
import argparse
import datetime as dt
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "raw" / "jalan_rusak_v2"

KEYWORD = ["jalan rusak", "jalanan rusak", "jalan berlubang", "jalan bolong", "jalan ambles", "jalan amblas",
           "aspal rusak", "aspal bolong", "lubang jalan", "jalan bergelombang"]

# nama kecamatan -> (variasi penulisan, perlu kata 'jakarta'?)
# 'jakarta' ditambahkan untuk nama yang juga ada di luar DKI (Pancoran Mas Depok, Cipayung Depok/Bogor,
# Setiabudi Bandung, Taman Sari Yogyakarta, Makassar, dst.)
KECAMATAN = {
    # Jakarta Pusat
    "Gambir": (["Gambir"], False), "Sawah Besar": (["Sawah Besar"], False), "Kemayoran": (["Kemayoran"], False),
    "Senen": (["Senen"], False), "Cempaka Putih": (["Cempaka Putih"], True), "Menteng": (["Menteng"], True),
    "Tanah Abang": (["Tanah Abang"], False), "Johar Baru": (["Johar Baru"], False),
    # Jakarta Utara
    "Penjaringan": (["Penjaringan"], False), "Pademangan": (["Pademangan"], False),
    "Tanjung Priok": (["Tanjung Priok", "Priok"], False), "Koja": (["Koja"], True),
    "Kelapa Gading": (["Kelapa Gading"], False), "Cilincing": (["Cilincing"], False),
    # Jakarta Barat
    "Cengkareng": (["Cengkareng"], False), "Grogol Petamburan": (["Grogol"], False),
    "Taman Sari": (["Taman Sari", "Tamansari"], True), "Tambora": (["Tambora"], True),
    "Kebon Jeruk": (["Kebon Jeruk"], False), "Kalideres": (["Kalideres", "Kali Deres"], False),
    "Palmerah": (["Palmerah"], False), "Kembangan": (["Kembangan"], True),
    # Jakarta Selatan
    "Tebet": (["Tebet"], False), "Setiabudi": (["Setiabudi", "Setia Budi"], True),
    "Mampang Prapatan": (["Mampang"], False), "Pasar Minggu": (["Pasar Minggu"], False),
    "Kebayoran Lama": (["Kebayoran Lama"], False), "Cilandak": (["Cilandak"], False),
    "Kebayoran Baru": (["Kebayoran Baru"], False), "Pancoran": (["Pancoran"], True),
    "Jagakarsa": (["Jagakarsa"], False), "Pesanggrahan": (["Pesanggrahan"], True),
    # Jakarta Timur
    "Matraman": (["Matraman"], False), "Pulo Gadung": (["Pulogadung", "Pulo Gadung"], False),
    "Jatinegara": (["Jatinegara"], False), "Kramat Jati": (["Kramat Jati"], False),
    "Pasar Rebo": (["Pasar Rebo"], False), "Cakung": (["Cakung"], False),
    "Duren Sawit": (["Duren Sawit"], False), "Makasar": (["Makasar"], True),
    "Ciracas": (["Ciracas"], False), "Cipayung": (["Cipayung"], True),
}

# Jalan utama (opsional, --jalan). Semua pakai 'jakarta' karena nama jalan sering ada di kota lain.
JALAN_UTAMA = ["Daan Mogot", "Gatot Subroto", "TB Simatupang", "Rasuna Said", "Kalimalang", "Raya Bogor",
               "Yos Sudarso", "Gunung Sahari", "Lenteng Agung", "Fatmawati", "Antasari", "DI Panjaitan",
               "MT Haryono", "S Parman", "Pramuka", "Otista", "Bekasi Raya", "Cakung Cilincing", "Ciledug Raya",
               "Hayam Wuruk", "Kramat R aya", "Salemba", "Warung Buncit", "Pondok Kopi"]


def frasa(teks):
    return f'"{teks}"' if " " in teks else teks


def bangun_query(nama_list, pakai_jakarta, since, until):
    kw = " OR ".join(f'"{k}"' for k in KEYWORD)
    tempat = " OR ".join(frasa(n) for n in nama_list)
    tempat = f"({tempat})" if len(nama_list) > 1 else tempat
    q = f"({kw}) {tempat}"
    if pakai_jakarta:
        q += " jakarta"
    return f"{q} -filter:retweets since:{since} until:{until}"


def ada_isinya(path):
    """True kalau file CSV sudah ada dan berisi minimal satu baris data selain header."""
    if not path.exists():
        return False
    with open(path, encoding="utf-8", errors="ignore") as f:
        baris = [b for b in f if b.strip()]
    return len(baris) >= 2


def slug(teks):
    return re.sub(r"[^a-z0-9]+", "_", teks.lower()).strip("_")


def daftar_query(args):
    since, until = args.since, args.until
    jendela = [(since, until)]
    if args.per_tahun:
        y0, y1 = int(since[:4]), int(until[:4])
        jendela = [(max(since, f"{y}-01-01"), min(until, f"{y + 1}-01-01")) for y in range(y0, y1 + 1)]
        jendela = [(a, b) for a, b in jendela if a < b]
    item = [(f"kec_{slug(k)}", v[0], v[1]) for k, v in KECAMATAN.items()]
    if args.jalan:
        item += [(f"jln_{slug(j)}", [j], True) for j in JALAN_UTAMA]
    if args.hanya:
        pilih = {slug(x) for x in args.hanya.split(",")}
        item = [it for it in item if it[0].split("_", 1)[1] in pilih]
    out = []
    for nama, varian, jkt in item:
        for a, b in jendela:
            akhir = f"_{a[:4]}" if args.per_tahun else ""
            out.append((f"jr_{nama}{akhir}.csv", bangun_query(varian, jkt, a, b)))
    return out


def main():
    besok = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default="2019-01-01")
    ap.add_argument("--until", default=besok)
    ap.add_argument("--limit", type=int, default=500, help="maksimum tweet per query")
    ap.add_argument("--jalan", action="store_true", help="tambah query per nama jalan utama")
    ap.add_argument("--per-tahun", action="store_true", help="pecah tiap query per tahun (lebih lengkap, lebih lama)")
    ap.add_argument("--hanya", help="hanya nama tertentu, pisah koma (mis. Tebet,Cilandak)")
    ap.add_argument("--run", action="store_true", help="jalankan tweet-harvest langsung")
    ap.add_argument("--token", help="auth token X (default: TWEET_HARVEST_TOKEN di .env)")
    ap.add_argument("--jeda", type=int, default=15, help="detik jeda antar query saat --run")
    args = ap.parse_args()

    queries = daftar_query(args)
    if not args.run:
        print(f"# {len(queries)} query. Jalankan dari folder {OUT_DIR.relative_to(ROOT).as_posix()}/ "
              f"supaya hasil masuk ke tweets-data/ di sana.\n# Di Colab: tambahkan '!' di depan tiap baris.\n")
        for nama, q in queries:
            print(f"npx -y tweet-harvest@latest -t \"$TWEET_HARVEST_TOKEN\" -s {shlex.quote(q)} "
                  f"-o {nama} -e csv -l {args.limit} --tab LATEST")
        return

    token = args.token or os.environ.get("TWEET_HARVEST_TOKEN")
    if not token:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
            token = os.environ.get("TWEET_HARVEST_TOKEN")
        except ImportError:
            pass
    if not token:
        sys.exit("Token belum ada: isi TWEET_HARVEST_TOKEN di .env atau pakai --token")
    npx = shutil.which("npx")
    if not npx:
        sys.exit("npx tidak ditemukan: pasang Node.js dulu (https://nodejs.org)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for i, (nama, q) in enumerate(queries, 1):
        target = OUT_DIR / "tweets-data" / nama
        if ada_isinya(target):
            print(f"[{i}/{len(queries)}] lewati {nama} (sudah ada)")
            continue
        if target.exists():   # file kosong dari run sebelumnya (tanpa hasil / rate limit): scrape ulang
            target.unlink()
        print(f"[{i}/{len(queries)}] {nama}\n    {q}")
        cmd = [npx, "-y", "tweet-harvest@latest", "-t", token, "-s", q, "-o", nama, "-e", "csv",
               "-l", str(args.limit), "--tab", "LATEST"]
        hasil = subprocess.run(cmd, cwd=OUT_DIR)
        if hasil.returncode != 0:
            print(f"    gagal (kode {hasil.returncode}); kemungkinan rate limit. Jalankan ulang nanti, "
                  f"file yang sudah ada akan dilewati.")
            break
        if i < len(queries):
            time.sleep(args.jeda)


if __name__ == "__main__":
    main()
