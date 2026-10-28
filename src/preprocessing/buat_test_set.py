"""Ambil sampel acak keluhan untuk TEST SET yang dilabeli manual secara buta (blind).

Kenapa perlu: label aturan disusun dari label manual yang sudah ada (kesesuaiannya 100%), jadi
label manual lama tidak bisa dipakai menilai label aturan maupun model. Test set ini diambil dari
keluhan yang BELUM pernah dilabeli manual, lalu dilabeli dua anotator tanpa melihat label aturan.
Pedoman: docs/pedoman-anotasi-urgensi.md

Cara pakai (dari root repo, cukup library bawaan Python):
    python src/preprocessing/buat_test_set.py
    python src/preprocessing/buat_test_set.py --margin 0.05     # sampel lebih besar

Output:
    data/anotasi/test_set_ids.csv                      daftar id test set (DI-COMMIT, tanpa teks). Sekali dibuat,
                                                       sampel dibekukan: jalankan ulang hanya membuat ulang lembar
                                                       dari id yang sama. Pakai --paksa untuk sampling ulang.
    data/processed/anotasi/test_set_anotator_A.csv     lembar anotasi (tidak di-commit, berisi teks tweet)
    data/processed/anotasi/test_set_anotator_B.csv     sama, urutan baris berbeda
Id di test_set_ids.csv WAJIB dikeluarkan dari data latih model.
Hasil anotasi (berisi teks) disimpan di data/raw/labels_test/, BUKAN data/raw/labels/ (dibaca pipeline sebagai label latih).
"""
import argparse
import csv
import math
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data" / "processed" / "jalan_rusak" / "keluhan_jalan_rusak.csv"
OUTPUT = ROOT / "data" / "processed" / "anotasi"
IDS = ROOT / "data" / "anotasi" / "test_set_ids.csv"
SEED = 42


def slovin(n_populasi, margin):
    return math.ceil(n_populasi / (1 + n_populasi * margin ** 2))


def sampel_berstrata(baris, kunci, n, rng):
    """Alokasi proporsional per strata (largest remainder), lalu acak di tiap strata."""
    strata = defaultdict(list)
    for b in baris:
        strata[b[kunci]].append(b)
    total = len(baris)
    kuota = {k: n * len(v) / total for k, v in strata.items()}
    bulat = {k: int(q) for k, q in kuota.items()}
    for k in sorted(kuota, key=lambda k: kuota[k] - bulat[k], reverse=True)[: n - sum(bulat.values())]:
        bulat[k] += 1
    hasil = []
    for k in sorted(strata):
        hasil += rng.sample(strata[k], bulat[k])
    return hasil, bulat


def sudah_diisi(path):
    """True kalau lembar sudah ada isinya (kategori/urgensi terisi), supaya tidak tertimpa."""
    if not path.exists():
        return False
    with open(path, encoding="utf-8-sig") as f:
        return any(r.get("kategori", "").strip() or r.get("urgensi", "").strip() for r in csv.DictReader(f))


def tulis_lembar(path, baris):
    if sudah_diisi(path):
        print(f"[lewati] {path.name} sudah berisi anotasi, tidak ditimpa")
        return
    kolom = ["no", "id_str", "full_text", "kategori", "urgensi", "catatan"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig supaya rapi di Excel
        w = csv.DictWriter(f, fieldnames=kolom)
        w.writeheader()
        for i, b in enumerate(baris, 1):
            # prefix id_ supaya Excel tidak membulatkan ID 19 digit
            w.writerow({"no": i, "id_str": "id_" + b["id_str"], "full_text": b["full_text"],
                        "kategori": "", "urgensi": "", "catatan": ""})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--margin", type=float, default=0.07, help="margin of error Slovin (default 0.07)")
    ap.add_argument("--paksa", action="store_true", help="sampling ulang walau test_set_ids.csv sudah ada")
    args = ap.parse_args()

    with open(INPUT, encoding="utf-8") as f:
        semua = list(csv.DictReader(f))
    # Populasi: keluhan yang belum pernah dilabeli manual (label aturan / belum berlabel)
    populasi = [b for b in semua if not b["urgensi_manual"].strip()]
    rng = random.Random(SEED)
    if IDS.exists() and not args.paksa:
        with open(IDS, encoding="utf-8") as f:
            ids_beku = [r["id_str"] for r in csv.DictReader(f)]
        per_id = {b["id_str"]: b for b in semua}
        hilang = [i for i in ids_beku if i not in per_id]
        if hilang:
            raise SystemExit(f"{len(hilang)} id test set tidak ada di {INPUT.name}. Cek data atau pakai --paksa.")
        sampel = [per_id[i] for i in ids_beku]
        n, alokasi = len(sampel), "dari test_set_ids.csv (beku)"
        print(f"[info] Memakai test set beku: {IDS.relative_to(ROOT)}")
    else:
        n = slovin(len(populasi), args.margin)
        sampel, alokasi = sampel_berstrata(populasi, "tipe_akun", n, rng)
        IDS.parent.mkdir(parents=True, exist_ok=True)
        with open(IDS, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id_str", "tipe_akun", "sumber_label_saat_sampling"])
            for b in sorted(sampel, key=lambda b: b["id_str"]):
                w.writerow([b["id_str"], b["tipe_akun"], b["sumber_label"] or "belum"])

    # Urutan lembar dibuat dari id terurut + seed tetap, jadi selalu sama setiap dijalankan
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sampel = sorted(sampel, key=lambda b: b["id_str"])
    urut_a = sampel[:]
    random.Random(SEED + 1).shuffle(urut_a)
    urut_b = sampel[:]
    random.Random(SEED + 2).shuffle(urut_b)
    tulis_lembar(OUTPUT / "test_set_anotator_A.csv", urut_a)
    tulis_lembar(OUTPUT / "test_set_anotator_B.csv", urut_b)

    print(f"Keluhan total            : {len(semua)}")
    print(f"Populasi (belum manual)  : {len(populasi)}")
    print(f"Ukuran sampel            : {n}")
    print(f"Alokasi per tipe_akun    : {alokasi}")
    print(f"Id test set              : {IDS.relative_to(ROOT)}")
    print(f"Lembar anotasi           : {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
