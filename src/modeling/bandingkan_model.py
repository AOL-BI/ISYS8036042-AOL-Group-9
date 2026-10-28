"""Bandingkan 4 model (RF, GBT, SVM, NB) dalam satu tabel — tanpa menimpa hasil model utama.

Dua sudut perbandingan:
  A. Kinerja di test set     : dibaca dari reports/tables/model_relevansi.csv & model_urgensi.csv
                               (hasil src/modeling/eksperimen_model.py; jalankan itu dulu kalau belum ada).
  B. Dampak ke hasil akhir   : tiap model dijalankan lewat alur prediksi_final.py (tanpa menulis file),
                               lalu dibandingkan jumlah keluhan relevan, distribusi urgensi, jumlah kejadian,
                               dan ranking kecamatan (kemiripan dengan model utama: Spearman & irisan Top-5/Top-10).

Cara pakai (dari root repo):
    python src/modeling/bandingkan_model.py
Output:
    reports/tables/perbandingan_model.md        tabel siap pakai untuk Bab 4
    reports/tables/perbandingan_ranking.csv     ranking 42 kecamatan per model berdampingan
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eksperimen_model import MODEL, TAB, URG  # noqa: E402
from prediksi_final import MODEL_UTAMA, jalankan, md  # noqa: E402

SINGKAT = {"Random Forest": "RF", "Gradient-Boosted Trees": "GBT", "SVM (linear)": "SVM", "Naive Bayes": "NB"}


def spearman(a, b):
    """Korelasi peringkat Spearman tanpa scipy (pakai rank pandas)."""
    a, b = pd.Series(a).rank(), pd.Series(b).rank()
    return float(a.corr(b))


def kinerja_test_set():
    rel_p, urg_p = TAB / "model_relevansi.csv", TAB / "model_urgensi.csv"
    if not (rel_p.exists() and urg_p.exists()):
        return None
    rel = pd.read_csv(rel_p)
    rel = rel[rel["fitur"] == "teks"].set_index("model")
    urg = pd.read_csv(urg_p)
    urg = urg[urg["data latih"] == "baru"].set_index("model")
    baris = []
    for m in MODEL:
        baris.append({
            "model": SINGKAT[m],
            "relevansi macro-F1": rel.loc[m, "macro_f1"], "relevansi CI95": rel.loc[m, "ci95"],
            "presisi keluhan": rel.loc[m, "precision_keluhan"],
            "urgensi macro-F1": urg.loc[m, "macro_f1"], "urgensi CI95": urg.loc[m, "ci95"],
            "F1 Tinggi": urg.loc[m, "f1_Tinggi"], "F1 Sedang": urg.loc[m, "f1_Sedang"],
            "F1 Rendah": urg.loc[m, "f1_Rendah"],
        })
    return pd.DataFrame(baris)


def main():
    hasil = {}
    for m in MODEL:
        print(f"[jalan] {m} ...")
        hasil[m] = jalankan(m, simpan=False, cetak=False)

    # ---------------------------------------------------- B1. ringkasan hasil akhir
    ring = []
    for m, h in hasil.items():
        k, kj, kec = h["keluhan"], h["kejadian"], h["kecamatan"]
        rel = k[k["relevan"]]
        dari_model = rel[rel["sumber_kategori"] == "model"]
        dist = kj["urgensi"].value_counts().reindex(URG, fill_value=0)
        top5 = kec.dropna(subset=["ranking"]).sort_values("ranking")["kecamatan"].head(5)
        ring.append({
            "model": SINGKAT[m],
            "keluhan relevan": len(rel),
            "  dari prediksi model": len(dari_model),
            "kejadian": len(kj),
            "kejadian Tinggi": dist["Tinggi"], "kejadian Sedang": dist["Sedang"], "kejadian Rendah": dist["Rendah"],
            "kecamatan data cukup": int(kec["data_cukup"].sum()),
            "Top-5": ", ".join(top5),
        })
    ring = pd.DataFrame(ring)

    # ---------------------------------------------------- B2. ranking berdampingan + kemiripan
    utama = hasil[MODEL_UTAMA]["kecamatan"].set_index("kecamatan")
    rk = pd.DataFrame({"kota": utama["kota"]})
    for m, h in hasil.items():
        kec = h["kecamatan"].set_index("kecamatan")
        rk[f"rank_{SINGKAT[m]}"] = kec["ranking"]
        rk[f"kejadian_{SINGKAT[m]}"] = kec["n_kejadian"]
    rk = rk.sort_values(f"rank_{SINGKAT[MODEL_UTAMA]}", na_position="last")
    TAB.mkdir(parents=True, exist_ok=True)
    rk.reset_index().to_csv(TAB / "perbandingan_ranking.csv", index=False)

    mirip = []
    ru = rk[f"rank_{SINGKAT[MODEL_UTAMA]}"]
    for m in MODEL:
        if m == MODEL_UTAMA:
            continue
        r = rk[f"rank_{SINGKAT[m]}"]
        sama = ru.notna() & r.notna()
        top = lambda s, n: set(s[s.fillna(10 ** 6) <= n].index)
        mirip.append({
            "model": SINGKAT[m],
            "kecamatan dibandingkan": int(sama.sum()),
            f"Spearman vs {SINGKAT[MODEL_UTAMA]}": round(spearman(ru[sama], r[sama]), 3) if sama.sum() > 2 else float("nan"),
            "irisan Top-5": f"{len(top(ru, 5) & top(r, 5))}/5",
            "irisan Top-10": f"{len(top(ru, 10) & top(r, 10))}/10",
        })
    mirip = pd.DataFrame(mirip)

    # ---------------------------------------------------- laporan
    L = ["# Perbandingan Model", ""]
    kin = kinerja_test_set()
    if kin is not None:
        L += ["## A. Kinerja di test set (label latih pedoman baru, fitur teks)", "",
              md(kin, 3), "",
              "Sumber: `model_relevansi.csv` & `model_urgensi.csv` (src/modeling/eksperimen_model.py).", ""]
    else:
        L += ["## A. Kinerja di test set", "", "_Belum ada. Jalankan `python src/modeling/eksperimen_model.py` dulu._", ""]
    L += ["## B. Dampak ke hasil akhir (semua keluhan pipeline)", "",
          "Baris berlabel manusia memakai label manusia di semua model, jadi perbedaan hanya berasal dari baris "
          "yang diprediksi model.", "",
          md(ring), "",
          f"## C. Kemiripan ranking kecamatan dengan model utama ({SINGKAT[MODEL_UTAMA]})", "",
          "Spearman dihitung pada kecamatan yang masuk ranking di kedua model (data cukup).", "",
          md(mirip, 3), "",
          "Ranking lengkap berdampingan: `reports/tables/perbandingan_ranking.csv`.", ""]
    (TAB / "perbandingan_model.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
