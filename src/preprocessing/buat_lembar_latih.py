"""Lembar anotasi DATA LATIH (pedoman baru) dibagi ke 3 anotator.

Kenapa: model yang dilatih dari label aturan hanya meniru aturan (macro-F1 ~0,36 di test set, tidak lebih
baik dari aturannya). Label latih baru dibuat dengan pedoman yang sama seperti test set
(docs/pedoman-anotasi-urgensi.md) supaya model belajar konsep yang sama dengan yang dievaluasi.

Populasi : keluhan_jalan_rusak.csv, TANPA id test set, tanpa label manual lama,
           tanpa baris yang sudah direview (review_pola_petugas.csv sudah punya kategori).
Sampel   : 210 baris acak berstrata tipe_akun (seed tetap), dibekukan di data/anotasi/latih_ids.csv.
           15 baris "bersama" dilabeli SEMUA anotator (untuk cek kesepakatan setelah kalibrasi),
           195 sisanya dibagi rata (65 per orang). Total per orang: 80 baris.

Cara pakai (dari root repo, library bawaan Python):
    python src/preprocessing/buat_lembar_latih.py
Output:
    data/anotasi/latih_ids.csv                       id + pembagian anotator (di-commit, tanpa teks)
    data/processed/anotasi/latih_<nama>.csv          lembar anotasi per orang (tidak di-commit)
Hasil isian disimpan di data/raw/labels_latih/latih_<nama>.csv
"""
import csv
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KELUHAN = ROOT / "data" / "processed" / "jalan_rusak" / "keluhan_jalan_rusak.csv"
TEST_IDS = ROOT / "data" / "anotasi" / "test_set_ids.csv"
REVIEW = ROOT / "data" / "raw" / "labels_test" / "review_pola_petugas.csv"
IDS = ROOT / "data" / "anotasi" / "latih_ids.csv"
OUTPUT = ROOT / "data" / "processed" / "anotasi"
ANOTATOR = ["mail", "fio", "angel"]
N_TOTAL, N_BERSAMA, SEED = 210, 15, 2026


def sampel_berstrata(baris, kunci, n, rng):
    strata = defaultdict(list)
    for b in baris:
        strata[b[kunci]].append(b)
    kuota = {k: n * len(v) / len(baris) for k, v in strata.items()}
    bulat = {k: int(q) for k, q in kuota.items()}
    for k in sorted(kuota, key=lambda k: kuota[k] - bulat[k], reverse=True)[: n - sum(bulat.values())]:
        bulat[k] += 1
    hasil = []
    for k in sorted(strata):
        hasil += rng.sample(sorted(strata[k], key=lambda b: b["id_str"]), bulat[k])
    return hasil


def sudah_diisi(path):
    if not path.exists():
        return False
    with open(path, encoding="utf-8-sig") as f:
        return any(r.get("kategori", "").strip() for r in csv.DictReader(f))


def main():
    with open(KELUHAN, encoding="utf-8") as f:
        semua = {r["id_str"]: r for r in csv.DictReader(f)}

    if IDS.exists():
        with open(IDS, encoding="utf-8") as f:
            bagi = [(r["id_str"], r["anotator"]) for r in csv.DictReader(f)]
        print(f"[info] Memakai pembagian beku: {IDS.relative_to(ROOT)}")
    else:
        with open(TEST_IDS, encoding="utf-8") as f:
            test = {r["id_str"] for r in csv.DictReader(f)}
        with open(REVIEW, encoding="utf-8-sig") as f:
            review = {r["id_str"].removeprefix("id_") for r in csv.DictReader(f)}
        pool = [r for r in semua.values()
                if r["id_str"] not in test and r["id_str"] not in review and not r["urgensi_manual"].strip()]
        rng = random.Random(SEED)
        sampel = sampel_berstrata(pool, "tipe_akun", N_TOTAL, rng)
        rng.shuffle(sampel)
        bagi = [(b["id_str"], "bersama") for b in sampel[:N_BERSAMA]]
        sisa = sampel[N_BERSAMA:]
        for i, b in enumerate(sisa):
            bagi.append((b["id_str"], ANOTATOR[i % len(ANOTATOR)]))
        IDS.parent.mkdir(parents=True, exist_ok=True)
        with open(IDS, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id_str", "anotator", "tipe_akun"])
            for i, a in sorted(bagi):
                w.writerow([i, a, semua[i]["tipe_akun"]])
        print(f"Populasi: {len(pool)} | sampel: {len(sampel)} ({N_BERSAMA} bersama)")

    hilang = [i for i, _ in bagi if i not in semua]
    if hilang:
        raise SystemExit(f"{len(hilang)} id tidak ada di keluhan_jalan_rusak.csv")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for nama in ANOTATOR:
        ids = sorted(i for i, a in bagi if a in (nama, "bersama"))
        random.Random(f"{SEED}-{nama}").shuffle(ids)          # urutan beda per orang, tetap tiap run
        path = OUTPUT / f"latih_{nama}.csv"
        if sudah_diisi(path):
            print(f"[lewati] {path.name} sudah berisi anotasi, tidak ditimpa")
            continue
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["no", "id_str", "full_text", "kategori", "urgensi", "catatan"])
            for n, i in enumerate(ids, 1):
                w.writerow([n, "id_" + i, semua[i]["full_text"], "", "", ""])
        print(f"{path.relative_to(ROOT)}: {len(ids)} baris")


if __name__ == "__main__":
    main()
