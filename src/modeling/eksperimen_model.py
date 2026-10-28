"""Eksperimen model (CRISP-DM: Modeling + Evaluation) untuk dua tugas:

  R. Relevansi : apakah baris hasil pipeline benar-benar KELUHAN jalan rusak? (biner)
  U. Urgensi   : Tinggi / Sedang / Rendah untuk keluhan (dan versi biner Tinggi vs Bukan Tinggi)

Data latih (pedoman baru, docs/pedoman-anotasi-urgensi.md):
  - data/raw/labels_latih/latih_{mail,fio,angel}.csv   210 baris (15 baris bersama -> voting mayoritas)
  - data/raw/labels_test/review_pola_petugas.csv       78 baris, kolom keputusan (hanya kategori)
  - pembanding: label manual lama & label aturan dari keluhan_jalan_rusak.csv
Data uji: data/anotasi/test_set_gold.csv (154 baris; 81 keluhan). Tidak pernah dipakai untuk latih/tuning.

Fitur : TF-IDF unigram+bigram dari text_clean (+ opsional fitur meta tipe_akun, status_wilayah, level_lokasi).
Model : Random Forest (utama), SVM linear, Gradient-Boosted Trees, Naive Bayes (Complement).
Kelas tidak seimbang: random oversampling HANYA di data latih.
Metrik: macro-F1 (utama) + akurasi; interval kepercayaan 95% dari bootstrap test set.

Cara pakai (dari root repo):
    pip install scikit-learn
    python src/modeling/eksperimen_model.py
Output: reports/tables/model_*.csv dan reports/tables/model_hasil.md
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold
from sklearn.naive_bayes import ComplementNB
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
KELUHAN = ROOT / "data" / "processed" / "jalan_rusak" / "keluhan_jalan_rusak.csv"
GOLD = ROOT / "data" / "anotasi" / "test_set_gold.csv"
LATIH_IDS = ROOT / "data" / "anotasi" / "latih_ids.csv"
LATIH_DIR = ROOT / "data" / "raw" / "labels_latih"
REVIEW = ROOT / "data" / "raw" / "labels_test" / "review_pola_petugas.csv"
TAB = ROOT / "reports" / "tables"
SEED = 42
URG = ["Tinggi", "Sedang", "Rendah"]
ALIAS_URG = {"ringan": "Rendah", "sdang": "Sedang"}   # salah ketik yang ditemukan di lembar anotasi
META = ["tipe_akun", "status_wilayah", "level_lokasi"]


# ============================================================ data
def norm_kat(v):
    return str(v).strip().lower().replace(" ", "_")


def norm_urg(v):
    v = str(v).strip().lower()
    v = ALIAS_URG.get(v, v)
    return v.capitalize() if v else ""


def label_latih_baru():
    ids = pd.read_csv(LATIH_IDS, dtype=str)
    rows = []
    for nama in ["mail", "fio", "angel"]:
        d = pd.read_csv(LATIH_DIR / f"latih_{nama}.csv", dtype=str, keep_default_na=False, encoding="utf-8-sig")
        d["id_str"] = d["id_str"].str.removeprefix("id_")
        d["kategori"] = d["kategori"].map(norm_kat)
        d["urgensi"] = d["urgensi"].map(norm_urg)
        d["anotator"] = nama
        rows.append(d[["id_str", "kategori", "urgensi", "anotator"]])
    semua = pd.concat(rows)
    bersama = set(ids.loc[ids["anotator"] == "bersama", "id_str"])

    def voting(g):
        kat = g["kategori"].mode()
        kat = kat.iloc[0] if len(kat) == 1 else ("keluhan" if (g["kategori"] == "keluhan").sum() >= 2 else g["kategori"].iloc[0])
        urg = ""
        if kat == "keluhan":
            u = [x for x in g.loc[g["kategori"] == "keluhan", "urgensi"] if x]
            if u:
                m = pd.Series(u).mode()
                urg = m.iloc[0] if len(m) == 1 else "Sedang"     # seri -> kelas tengah
        return pd.Series({"kategori": kat, "urgensi": urg})

    tunggal = semua[~semua["id_str"].isin(bersama)][["id_str", "kategori", "urgensi"]]
    vote = semua[semua["id_str"].isin(bersama)].groupby("id_str").apply(voting).reset_index()
    out = pd.concat([tunggal, vote], ignore_index=True)
    out["sumber"] = "latih_baru"
    return out


def label_review():
    r = pd.read_csv(REVIEW, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return pd.DataFrame({"id_str": r["id_str"].str.removeprefix("id_"), "kategori": r["keputusan"].map(norm_kat),
                         "urgensi": "", "sumber": "review"})


# ============================================================ fitur & model
def fitur(train_df, test_df, meta):
    v = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    Xtr, Xte = v.fit_transform(train_df["text_clean"].fillna("")), v.transform(test_df["text_clean"].fillna(""))
    if meta:
        dtr = pd.get_dummies(train_df[META].fillna("na"))
        dte = pd.get_dummies(test_df[META].fillna("na")).reindex(columns=dtr.columns, fill_value=0)
        Xtr = hstack([Xtr, csr_matrix(dtr.values.astype(float))]).tocsr()
        Xte = hstack([Xte, csr_matrix(dte.values.astype(float))]).tocsr()
    return Xtr, Xte


def oversample(X, y, rng):
    y = np.asarray(y)
    kelas, jumlah = np.unique(y, return_counts=True)
    idx = np.concatenate([rng.choice(np.where(y == k)[0], jumlah.max(), replace=True) for k in kelas])
    return X[idx], y[idx]


MODEL = {
    "Random Forest": lambda: RandomForestClassifier(n_estimators=500, random_state=SEED, n_jobs=-1),
    "SVM (linear)": lambda: LinearSVC(C=0.5, random_state=SEED),
    "Gradient-Boosted Trees": lambda: GradientBoostingClassifier(random_state=SEED),
    "Naive Bayes": lambda: ComplementNB(),
}


def latih_prediksi(nama, train_df, y_train, test_df, meta):
    rng = np.random.default_rng(SEED)
    Xtr, Xte = fitur(train_df, test_df, meta)
    Xo, yo = oversample(Xtr, y_train, rng)
    m = MODEL[nama]()
    m.fit(Xo, yo)
    return m.predict(Xte)


def cv_macro_f1(nama, df, y, labels, meta, k=5):
    y = np.asarray(y)
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEED)
    skor = []
    for tr, te in skf.split(df, y):
        p = latih_prediksi(nama, df.iloc[tr], y[tr], df.iloc[te], meta)
        skor.append(f1_score(y[te], p, labels=labels, average="macro", zero_division=0))
    return float(np.mean(skor))


def bootstrap_ci(y, p, labels, n=2000):
    rng = np.random.default_rng(SEED)
    y, p = np.asarray(y), np.asarray(p)
    s = [f1_score(y[i], p[i], labels=labels, average="macro", zero_division=0)
         for i in (rng.integers(0, len(y), len(y)) for _ in range(n))]
    return np.percentile(s, [2.5, 97.5])


def skor(y, p, labels, pos=None):
    out = {"akurasi": accuracy_score(y, p), "macro_f1": f1_score(y, p, labels=labels, average="macro", zero_division=0)}
    lo, hi = bootstrap_ci(y, p, labels)
    out["ci95"] = f"{lo:.2f}–{hi:.2f}"
    if pos:
        out["precision_keluhan"] = precision_score(y, p, pos_label=pos, zero_division=0)
        out["recall_keluhan"] = recall_score(y, p, pos_label=pos, zero_division=0)
    for k, f in zip(labels, f1_score(y, p, labels=labels, average=None, zero_division=0)):
        out[f"f1_{k}"] = f
    return out


def md(df):
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(f"{v:.3f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(rows)


# ============================================================ main
def main():
    k = pd.read_csv(KELUHAN, dtype=str)
    gold = pd.read_csv(GOLD, dtype=str, keep_default_na=False)
    test = k.merge(gold.rename(columns={"kategori": "g_kat", "urgensi": "g_urg"})[["id_str", "g_kat", "g_urg"]], on="id_str")
    test_ids = set(test["id_str"])
    baru = label_latih_baru()
    rev = label_review()
    assert not (set(baru["id_str"]) | set(rev["id_str"])) & test_ids, "data latih bocor ke test set!"
    L = [f"# Hasil Eksperimen Model", "",
         f"Test set: {len(test)} baris (keluhan menurut label final: {(test['g_kat'] == 'keluhan').sum()}). "
         f"Data latih baru: {len(baru)} baris + review {len(rev)} baris.", ""]

    # ------------------------------------------------ R. relevansi
    lat_r = k.merge(pd.concat([baru, rev])[["id_str", "kategori", "sumber"]], on="id_str")
    yr = np.where(lat_r["kategori"] == "keluhan", "keluhan", "bukan")
    yt = np.where(test["g_kat"] == "keluhan", "keluhan", "bukan")
    LR = ["keluhan", "bukan"]
    hasil = [{"model": "Baseline: semua dianggap keluhan (pipeline sekarang)", "fitur": "-", "cv_macro_f1": np.nan,
              **skor(yt, np.array(["keluhan"] * len(yt)), LR, "keluhan")},
             {"model": "Baseline: keluhan jika lokasi DKI ditemukan", "fitur": "-", "cv_macro_f1": np.nan,
              **skor(yt, np.where(test["status_wilayah"] == "dki", "keluhan", "bukan"), LR, "keluhan")}]
    pred_r = {}
    for meta in (False, True):
        for nama in MODEL:
            p = latih_prediksi(nama, lat_r, yr, test, meta)
            tag = "teks + meta" if meta else "teks"
            pred_r[(nama, tag)] = p
            hasil.append({"model": nama, "fitur": tag, "cv_macro_f1": cv_macro_f1(nama, lat_r, yr, LR, meta),
                          **skor(yt, p, LR, "keluhan")})
    hr = pd.DataFrame(hasil)
    TAB.mkdir(parents=True, exist_ok=True)
    hr.to_csv(TAB / "model_relevansi.csv", index=False)
    L += ["## R. Filter relevansi (keluhan vs bukan)", "",
          f"Latih: {len(lat_r)} baris ({(yr == 'keluhan').mean():.0%} keluhan). Uji: {len(test)} baris.", "",
          md(hr[["model", "fitur", "cv_macro_f1", "akurasi", "macro_f1", "ci95", "precision_keluhan", "recall_keluhan"]]), ""]

    # ------------------------------------------------ U. urgensi
    tk = test[test["g_kat"] == "keluhan"].copy()
    base = k[~k["id_str"].isin(test_ids)]
    baru_k = baru[(baru["kategori"] == "keluhan") & (baru["urgensi"] != "")]
    set_latih = {
        "baru": k.merge(baru_k[["id_str", "urgensi"]].rename(columns={"urgensi": "y"}), on="id_str"),
        "baru + manual lama": pd.concat([
            k.merge(baru_k[["id_str", "urgensi"]].rename(columns={"urgensi": "y"}), on="id_str"),
            base[base["sumber_label"] == "manual"].assign(y=lambda d: d["urgensi_manual"])]),
        "aturan + manual lama (cara lama)": base[base["urgensi"].notna()].assign(y=lambda d: d["urgensi"]),
    }
    hasil, best = [], None
    yg = tk["g_urg"].values
    hasil.append({"model": "Baseline: label aturan (kosong = salah)", "data latih": "-", "n_latih": 0,
                  "cv_macro_f1": np.nan, **skor(yg, tk["urgensi_aturan"].fillna("(kosong)").values, URG)})
    hasil.append({"model": "Baseline: label aturan (kosong = Sedang)", "data latih": "-", "n_latih": 0,
                  "cv_macro_f1": np.nan, **skor(yg, tk["urgensi_aturan"].fillna("Sedang").values, URG)})
    hasil.append({"model": "Baseline: selalu Sedang", "data latih": "-", "n_latih": 0, "cv_macro_f1": np.nan,
                  **skor(yg, np.array(["Sedang"] * len(yg)), URG)})
    biner = []
    yb = np.where(yg == "Tinggi", "Tinggi", "Bukan Tinggi")
    LB = ["Tinggi", "Bukan Tinggi"]
    biner.append({"model": "Baseline: label aturan", "data latih": "-",
                  **skor(yb, np.where(tk["urgensi_aturan"] == "Tinggi", "Tinggi", "Bukan Tinggi"), LB)})
    for nama_set, df in set_latih.items():
        df = df[df["y"].isin(URG)].drop_duplicates("id_str")
        for nama in MODEL:
            p = latih_prediksi(nama, df, df["y"].values, tk, False)
            r = {"model": nama, "data latih": nama_set, "n_latih": len(df),
                 "cv_macro_f1": cv_macro_f1(nama, df, df["y"].values, URG, False), **skor(yg, p, URG)}
            hasil.append(r)
            if nama_set == "baru" and (best is None or r["cv_macro_f1"] > best[0]):
                best = (r["cv_macro_f1"], nama, p)
            pb = latih_prediksi(nama, df, np.where(df["y"] == "Tinggi", "Tinggi", "Bukan Tinggi"), tk, False)
            biner.append({"model": nama, "data latih": nama_set, **skor(yb, pb, LB)})
    hu = pd.DataFrame(hasil)
    hu.to_csv(TAB / "model_urgensi.csv", index=False)
    hb = pd.DataFrame(biner)
    hb.to_csv(TAB / "model_urgensi_biner.csv", index=False)
    dist = baru_k["urgensi"].value_counts().reindex(URG, fill_value=0)
    L += ["## U. Urgensi (3 kelas)", "",
          f"Uji: {len(tk)} keluhan (Tinggi {sum(yg == 'Tinggi')}, Sedang {sum(yg == 'Sedang')}, Rendah {sum(yg == 'Rendah')}). "
          f"Label latih baru: {len(baru_k)} keluhan (Tinggi {dist['Tinggi']}, Sedang {dist['Sedang']}, Rendah {dist['Rendah']}).", "",
          md(hu[["model", "data latih", "n_latih", "cv_macro_f1", "akurasi", "macro_f1", "ci95", "f1_Tinggi", "f1_Sedang", "f1_Rendah"]]), "",
          "## U2. Urgensi biner (Tinggi vs Bukan Tinggi)", "",
          md(hb[["model", "data latih", "akurasi", "macro_f1", "ci95", "f1_Tinggi"]]), ""]
    if best:
        cm = confusion_matrix(yg, best[2], labels=URG)
        L += [f"Confusion matrix model terpilih dari data latih baru (CV tertinggi: {best[1]}), baris = label final:", "",
              md(pd.DataFrame(cm, index=URG, columns=URG).reset_index().rename(columns={"index": "final"})), ""]
    (TAB / "model_hasil.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
