"""Evaluasi test set anotasi buta (CRISP-DM: Evaluation).

Langkah:
  1. Baca lembar anotator A & B (data/raw/labels_test/), samakan format penulisan
     (mis. "Keluhan" -> "keluhan", "tinggi" -> "Tinggi").
  2. Hitung kesepakatan antar-anotator: persentase sepakat, Cohen's kappa (kategori, urgensi),
     dan weighted kappa linear untuk urgensi (kelasnya ordinal).
  3. Baris yang beda -> data/processed/anotasi/perlu_diskusi.csv. Isi kolom final_kategori &
     final_urgensi hasil diskusi, simpan sebagai data/raw/labels_test/hasil_diskusi.csv.
  4. Label final (gold) = label yang sama + hasil diskusi -> data/anotasi/test_set_gold.csv (di-commit, tanpa teks).
  5. Evaluasi pipeline & label aturan terhadap gold:
       - presisi filter "keluhan" pipeline (berapa % baris yang memang keluhan)
       - label aturan vs gold urgensi: akurasi, macro-F1, precision/recall/F1 per kelas, confusion matrix
     Selama diskusi belum selesai, evaluasi memakai baris yang sudah sepakat saja (ditandai SEMENTARA).

Cara pakai (dari root repo, cukup library bawaan Python):
    python src/evaluation/evaluasi_test_set.py
Output ringkasan: reports/tables/eval_test_set.md + beberapa CSV eval_*.csv
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LABELS = ROOT / "data" / "raw" / "labels_test"
FILE_A = LABELS / "test_set_anotator_A.csv"
FILE_B = LABELS / "test_set_anotator_B.csv"
FILE_DISKUSI = LABELS / "hasil_diskusi.csv"
KELUHAN = ROOT / "data" / "processed" / "jalan_rusak" / "keluhan_jalan_rusak.csv"
IDS = ROOT / "data" / "anotasi" / "test_set_ids.csv"
OUT_DISKUSI = ROOT / "data" / "processed" / "anotasi" / "perlu_diskusi.csv"
OUT_GOLD = ROOT / "data" / "anotasi" / "test_set_gold.csv"
TAB = ROOT / "reports" / "tables"

KATEGORI = ["keluhan", "laporan_perbaikan", "berita_umum", "bukan_jalan_rusak"]
URGENSI = ["Tinggi", "Sedang", "Rendah"]


# ------------------------------------------------------------------ baca & normalisasi
def norm_kategori(v):
    v = v.strip().lower().replace(" ", "_").replace("-", "_")
    if v not in KATEGORI:
        raise ValueError(f"kategori tidak dikenal: {v!r}")
    return v


def norm_urgensi(v):
    v = v.strip().capitalize()
    if v and v not in URGENSI:
        raise ValueError(f"urgensi tidak dikenal: {v!r}")
    return v


def baca_lembar(path):
    hasil = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            i = r["id_str"].strip().removeprefix("id_")
            kat, urg = norm_kategori(r["kategori"]), norm_urgensi(r["urgensi"])
            if (kat == "keluhan") != bool(urg):
                raise ValueError(f"{path.name} id {i}: urgensi wajib diisi hanya untuk kategori keluhan")
            hasil[i] = {"kategori": kat, "urgensi": urg, "full_text": r["full_text"]}
    return hasil


# ------------------------------------------------------------------ metrik
def cohen_kappa(a, b, kelas):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in kelas) / n ** 2
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def weighted_kappa(a, b, kelas):
    """Weighted kappa linear: beda 1 tingkat (Tinggi vs Sedang) dihukum lebih ringan dari beda 2 tingkat."""
    k, n = len(kelas), len(a)
    if n == 0:
        return float("nan")
    idx = {c: i for i, c in enumerate(kelas)}
    w = lambda i, j: abs(i - j) / (k - 1)
    obs = sum(w(idx[x], idx[y]) for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    exp = sum(ca[x] * cb[y] * w(idx[x], idx[y]) for x in kelas for y in kelas) / n ** 2
    return 1 - obs / exp if exp > 0 else 1.0


def tafsir_kappa(k):
    # Landis & Koch (1977)
    for batas, label in [(0.2, "sangat lemah"), (0.4, "lemah"), (0.6, "sedang"), (0.8, "kuat")]:
        if k <= batas:
            return label
    return "hampir sempurna"


def per_kelas(benar, prediksi, kelas):
    baris, f1s = [], []
    for k in kelas:
        tp = sum(b == k and p == k for b, p in zip(benar, prediksi))
        fp = sum(b != k and p == k for b, p in zip(benar, prediksi))
        fn = sum(b == k and p != k for b, p in zip(benar, prediksi))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        f1s.append(f1)
        baris.append({"kelas": k, "support": tp + fn, "precision": round(prec, 3), "recall": round(rec, 3),
                      "f1": round(f1, 3)})
    akurasi = sum(b == p for b, p in zip(benar, prediksi)) / len(benar) if benar else float("nan")
    return baris, akurasi, sum(f1s) / len(f1s)


def confusion(benar, prediksi, baris_kelas, kolom_kelas):
    c = Counter(zip(benar, prediksi))
    return [[c[(b, p)] for p in kolom_kelas] for b in baris_kelas]


def tulis_csv(path, rows, kolom=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=kolom or list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def md_tabel(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


# ------------------------------------------------------------------ main
def main():
    A, B = baca_lembar(FILE_A), baca_lembar(FILE_B)
    with open(IDS, encoding="utf-8") as f:
        ids = [r["id_str"] for r in csv.DictReader(f)]
    assert set(A) == set(B) == set(ids), "id lembar A, B, dan test_set_ids.csv tidak sama"
    with open(KELUHAN, encoding="utf-8") as f:
        pipa = {r["id_str"]: r for r in csv.DictReader(f) if r["id_str"] in set(ids)}

    # 1. Kesepakatan antar-anotator
    ka = [A[i]["kategori"] for i in ids]
    kb = [B[i]["kategori"] for i in ids]
    dua_keluhan = [i for i in ids if A[i]["kategori"] == B[i]["kategori"] == "keluhan"]
    ua = [A[i]["urgensi"] for i in dua_keluhan]
    ub = [B[i]["urgensi"] for i in dua_keluhan]
    gab = lambda X, i: X[i]["kategori"] + ("/" + X[i]["urgensi"] if X[i]["urgensi"] else "")
    ga, gb = [gab(A, i) for i in ids], [gab(B, i) for i in ids]
    kelas_gab = sorted(set(ga) | set(gb))
    sepakat = [
        ("Kategori (4 kelas)", len(ids), sum(x == y for x, y in zip(ka, kb)), cohen_kappa(ka, kb, KATEGORI), None),
        ("Urgensi (3 kelas, baris yang sama-sama keluhan)", len(ua), sum(x == y for x, y in zip(ua, ub)),
         cohen_kappa(ua, ub, URGENSI), weighted_kappa(ua, ub, URGENSI)),
        ("Kategori + urgensi (gabungan)", len(ids), sum(x == y for x, y in zip(ga, gb)),
         cohen_kappa(ga, gb, kelas_gab), None),
    ]
    rows_sepakat = [{"aspek": a, "n": n, "sepakat": s, "sepakat_%": round(100 * s / n, 1) if n else "",
                     "cohen_kappa": round(k, 3), "tafsir": tafsir_kappa(k),
                     "weighted_kappa_linear": "" if wk is None else round(wk, 3)} for a, n, s, k, wk in sepakat]
    tulis_csv(TAB / "eval_kesepakatan_anotator.csv", rows_sepakat)
    cm_kat = confusion(ka, kb, KATEGORI, KATEGORI)
    cm_urg = confusion(ua, ub, URGENSI, URGENSI)

    # 2. Baris yang perlu didiskusikan
    beda = [i for i in ids if gab(A, i) != gab(B, i)]
    diskusi = {}
    if FILE_DISKUSI.exists():
        with open(FILE_DISKUSI, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("final_kategori", "").strip():
                    i = r["id_str"].strip().removeprefix("id_")
                    kat, urg = norm_kategori(r["final_kategori"]), norm_urgensi(r.get("final_urgensi", ""))
                    if (kat == "keluhan") != bool(urg):
                        raise ValueError(f"hasil_diskusi id {i}: urgensi wajib diisi hanya untuk keluhan")
                    diskusi[i] = {"kategori": kat, "urgensi": urg}
    OUT_DISKUSI.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_DISKUSI, "w", newline="", encoding="utf-8-sig") as f:   # utf-8-sig: rapi di Excel
        w = csv.writer(f)
        w.writerow(["no", "id_str", "full_text", "kategori_A", "urgensi_A", "kategori_B", "urgensi_B",
                    "final_kategori", "final_urgensi", "catatan"])
        for n, i in enumerate(beda, 1):
            d = diskusi.get(i, {})
            w.writerow([n, "id_" + i, A[i]["full_text"], A[i]["kategori"], A[i]["urgensi"], B[i]["kategori"],
                        B[i]["urgensi"], d.get("kategori", ""), d.get("urgensi", ""), ""])

    # 3. Gold label
    gold, pending = {}, []
    for i in ids:
        if i not in beda:
            gold[i] = {"kategori": A[i]["kategori"], "urgensi": A[i]["urgensi"], "sumber": "sepakat"}
        elif i in diskusi:
            gold[i] = {**diskusi[i], "sumber": "diskusi"}
        else:
            pending.append(i)
    final = not pending
    if final:
        tulis_csv(OUT_GOLD, [{"id_str": i, "kategori": gold[i]["kategori"], "urgensi": gold[i]["urgensi"],
                              "sumber": gold[i]["sumber"]} for i in ids])
    status = "FINAL" if final else f"SEMENTARA ({len(pending)} baris belum didiskusikan, dievaluasi tanpa baris itu)"

    # 4. Evaluasi pipeline: presisi filter keluhan
    g_ids = [i for i in ids if i in gold]
    def breakdown(kunci):
        c = Counter((pipa[i][kunci], gold[i]["kategori"]) for i in g_ids)
        nilai = sorted({k for k, _ in c})
        return [[v] + [c[(v, k)] for k in KATEGORI] +
                [f"{100 * c[(v, 'keluhan')] / max(1, sum(c[(v, k)] for k in KATEGORI)):.0f}%"] for v in nilai]
    presisi = sum(gold[i]["kategori"] == "keluhan" for i in g_ids) / len(g_ids)
    dist_kat = Counter(gold[i]["kategori"] for i in g_ids)

    # 5. Label aturan vs gold urgensi (hanya gold = keluhan)
    gk = [i for i in g_ids if gold[i]["kategori"] == "keluhan"]
    benar = [gold[i]["urgensi"] for i in gk]
    pred = [pipa[i]["urgensi_aturan"].strip() or "(tanpa label)" for i in gk]
    per, akurasi, macro_f1 = per_kelas(benar, pred, URGENSI)
    tulis_csv(TAB / "eval_aturan_per_kelas.csv", per)
    cm_aturan = confusion(benar, pred, URGENSI, URGENSI + ["(tanpa label)"])
    tanpa_label = pred.count("(tanpa label)")
    ada = [(b, p) for b, p in zip(benar, pred) if p != "(tanpa label)"]
    akurasi_ada = sum(b == p for b, p in ada) / len(ada) if ada else float("nan")

    # ------------------------------------------------------------------ laporan
    L = [f"# Evaluasi Test Set ({status})", "",
         f"Test set: {len(ids)} keluhan hasil pipeline, sampel acak Slovin e=7% berstrata tipe akun, "
         "dilabeli buta oleh 2 anotator mengikuti `docs/pedoman-anotasi-urgensi.md`.", "",
         "## 1. Kesepakatan antar-anotator", "",
         md_tabel(["Aspek", "n", "Sepakat", "Sepakat %", "Cohen's κ", "Tafsir (Landis & Koch)", "Weighted κ (linear)"],
                  [[r["aspek"], r["n"], r["sepakat"], r["sepakat_%"], r["cohen_kappa"], r["tafsir"],
                    r["weighted_kappa_linear"]] for r in rows_sepakat]), "",
         "Confusion kategori (baris = A, kolom = B):", "",
         md_tabel(["A \\ B"] + KATEGORI, [[k] + row for k, row in zip(KATEGORI, cm_kat)]), "",
         "Confusion urgensi, baris yang sama-sama keluhan (baris = A, kolom = B):", "",
         md_tabel(["A \\ B"] + URGENSI, [[k] + row for k, row in zip(URGENSI, cm_urg)]), "",
         f"Baris berbeda (perlu diskusi): **{len(beda)}**, sudah diputuskan: {len(diskusi)}. "
         f"Daftar: `data/processed/anotasi/perlu_diskusi.csv`.", "",
         "## 2. Presisi filter keluhan pipeline", "",
         f"Dari {len(g_ids)} baris berlabel final, **{dist_kat['keluhan']} ({100 * presisi:.0f}%) memang keluhan**.", "",
         md_tabel(["Kategori final", "Jumlah", "%"],
                  [[k, dist_kat[k], f"{100 * dist_kat[k] / len(g_ids):.0f}%"] for k in KATEGORI]), "",
         "Menurut `status_wilayah` pipeline:", "",
         md_tabel(["status_wilayah"] + KATEGORI + ["% keluhan"], breakdown("status_wilayah")), "",
         "Menurut `tipe_akun`:", "",
         md_tabel(["tipe_akun"] + KATEGORI + ["% keluhan"], breakdown("tipe_akun")), "",
         "## 3. Label aturan vs label final (hanya keluhan)", "",
         f"- n = {len(gk)} keluhan; label aturan kosong (tidak ada kata penanda): {tanpa_label}",
         f"- Akurasi (label kosong dihitung salah): **{akurasi:.1%}**",
         f"- Akurasi pada baris yang punya label aturan: {akurasi_ada:.1%}",
         f"- Macro-F1: **{macro_f1:.3f}**", "",
         md_tabel(["Kelas", "Support", "Precision", "Recall", "F1"],
                  [[r["kelas"], r["support"], r["precision"], r["recall"], r["f1"]] for r in per]), "",
         "Confusion (baris = label final, kolom = label aturan):", "",
         md_tabel(["Final \\ Aturan"] + URGENSI + ["(tanpa label)"], [[k] + row for k, row in zip(URGENSI, cm_aturan)]),
         ""]
    TAB.mkdir(parents=True, exist_ok=True)
    (TAB / "eval_test_set.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    if final:
        print(f"\nGold label tersimpan: {OUT_GOLD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
