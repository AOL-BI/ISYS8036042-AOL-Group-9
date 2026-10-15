"""Bangun tabel estimasi penduduk per kelurahan DKI Jakarta (daratan).

Metode:
  1. Ambil jumlah penduduk WNI per kelurahan tahun 2017 (Satu Data Jakarta),
     jumlahkan laki-laki + perempuan.
  2. Cocokkan ke daftar kelurahan batas wilayah (jakarta_kelurahan.csv) lewat
     nama kota + nama kelurahan yang dinormalisasi. Beda ejaan ditangani lewat
     ALIAS di bawah (eksplisit, tanpa fuzzy matching).
  3. Skalakan ke total penduduk per kota dari BPS tahun terbaru:
        penduduk_est = penduduk_2017 x (total_BPS_kota / total_2017_kota)
     Asumsi: proporsi penduduk antar-kelurahan dalam satu kota tidak berubah
     sejak 2017.

Input :
  data/external/batas-wilayah/jakarta_kelurahan.csv
  data/external/populasi/satudata_penduduk_wni_2017.csv
  data/external/populasi/bps_penduduk_kota_2025.csv   <- ganti file ini kalau ada angka BPS lebih baru
Output:
  data/external/populasi/jakarta_populasi_kelurahan.csv

Cara pakai (dari root repo): python src/preprocessing/build_populasi_kelurahan.py
Hanya pakai library bawaan Python.
"""
import collections
import csv
import re
import sys

BATAS = "data/external/batas-wilayah/jakarta_kelurahan.csv"
SUMBER = "data/external/populasi/satudata_penduduk_wni_2017.csv"
BPS = "data/external/populasi/bps_penduduk_kota_2025.csv"
OUT = "data/external/populasi/jakarta_populasi_kelurahan.csv"
TAHUN_SUMBER = 2017

# Ejaan di data Pemprov -> ejaan di batas wilayah (HDX/BPS), sesudah dinormalisasi.
ALIAS = {
    "WIJAYAKUSUMA": "WIJAYAKESUMA",
    "KERENDANG": "KRENDANG",
    "HARAPANMULIA": "HARAPANMULYA",
    "PALMERIAM": "PALMERIEM",
    "PAPANGGO": "PAPANGO",
    "TANJUNGPRIOK": "TANJUNGPRIUK",
}


def norm(s):
    """Huruf besar, buang spasi & tanda baca: 'Rawa Sari' == 'RAWASARI'."""
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def norm_kota(s):
    return norm(s).replace("KOTA", "").replace("KABADM", "")


def bagi_proporsional(nilai, total):
    """Skalakan list nilai supaya jumlahnya persis `total` (largest remainder)."""
    faktor = total / sum(nilai)
    mentah = [v * faktor for v in nilai]
    hasil = [int(m) for m in mentah]
    sisa = total - sum(hasil)
    urut = sorted(range(len(nilai)), key=lambda i: mentah[i] - hasil[i], reverse=True)
    for i in urut[:sisa]:
        hasil[i] += 1
    return hasil


def main():
    # 1. Penduduk 2017 per (kota, kelurahan)
    pop = collections.defaultdict(int)
    with open(SUMBER, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            kel = norm(r["nama_kelurahan"])
            pop[(norm_kota(r["nama_kota"]), ALIAS.get(kel, kel))] += int(r["jumlah"])

    # 2. Cocokkan ke batas wilayah
    with open(BATAS, encoding="utf-8") as f:
        batas = list(csv.DictReader(f))
    kunci = [(norm_kota(b["adm2_name"]), norm(b["adm4_name"])) for b in batas]
    dobel = [k for k, v in collections.Counter(kunci).items() if v > 1]
    tak_ketemu = [b["adm4_name"] for b, k in zip(batas, kunci) if k not in pop]
    if dobel or tak_ketemu:
        sys.exit(f"GAGAL matching. Kunci dobel: {dobel}. Tidak ada data penduduk: {tak_ketemu}")

    # 3. Skala ke total BPS per kota
    with open(BPS, encoding="utf-8") as f:
        bps = {r["adm2_pcode"]: r for r in csv.DictReader(f)}
    tahun = {r["tahun"] for r in bps.values()}
    assert len(tahun) == 1, "bps_penduduk_kota: tahun harus sama semua"
    tahun = tahun.pop()

    per_kota = collections.defaultdict(list)
    for b, k in zip(batas, kunci):
        per_kota[b["adm2_pcode"]].append((b, pop[k]))

    baris = []
    print(f"{'Kota':24}{'2017':>11}{'BPS ' + tahun:>11}{'faktor':>8}{'kel':>5}")
    for kode in sorted(per_kota):
        isi = per_kota[kode]
        lama = [p for _, p in isi]
        target = int(bps[kode]["penduduk"])
        baru = bagi_proporsional(lama, target)
        faktor = target / sum(lama)
        print(f"{isi[0][0]['adm2_name']:24}{sum(lama):>11,}{target:>11,}{faktor:>8.4f}{len(isi):>5}")
        for (b, p_lama), p_baru in zip(isi, baru):
            luas = float(b["area_sqkm"])
            baris.append({
                "adm4_pcode": b["adm4_pcode"], "adm4_name": b["adm4_name"],
                "adm3_pcode": b["adm3_pcode"], "adm3_name": b["adm3_name"],
                "adm2_pcode": b["adm2_pcode"], "adm2_name": b["adm2_name"],
                f"penduduk_{TAHUN_SUMBER}": p_lama,
                "faktor_skala": round(faktor, 4),
                f"penduduk_{tahun}_est": p_baru,
                "area_sqkm": round(luas, 4),
                f"kepadatan_{tahun}_est": round(p_baru / luas),
            })

    baris.sort(key=lambda r: r["adm4_pcode"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(baris[0]))
        w.writeheader()
        w.writerows(baris)
    kol = f"penduduk_{tahun}_est"
    print(f"\n{len(baris)} kelurahan -> {OUT}")
    print(f"Total {kol}: {sum(r[kol] for r in baris):,}")

    terpakai = set(kunci)
    sisa = sorted(k for k in pop if k not in terpakai and "SERIBU" not in k[0])
    if sisa:
        print("PERINGATAN, ada di data penduduk tapi tidak ada di batas wilayah:", sisa)


if __name__ == "__main__":
    main()
