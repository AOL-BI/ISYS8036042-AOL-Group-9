"""Script final (CRISP-DM: Deployment) — dari keluhan hasil pipeline ke ranking prioritas per kecamatan.

Alur:
  1. Latih model RELEVANSI (keluhan vs bukan) dari label pedoman baru: data latih 210 + review 78 baris.
  2. Latih model URGENSI (Tinggi/Sedang/Rendah) dari keluhan berlabel pedoman baru (data latih saja).
     Konfigurasi sama persis dengan yang dievaluasi di src/modeling/eksperimen_model.py
     (TF-IDF unigram+bigram dari text_clean, random oversampling, test set TIDAK ikut dilatih).
  3. Terapkan ke semua keluhan hasil pipeline. Baris yang punya label manusia (test set, data latih,
     review) memakai label manusia; sisanya memakai prediksi model.
  4. Gabungkan tweet menjadi KEJADIAN: tweet di kecamatan yang sama dengan jeda <= 7 hari dari tweet
     sebelumnya dianggap membahas kejadian yang sama (satu kejadian viral bisa diberitakan belasan akun).
     Urgensi kejadian = urgensi tertinggi di dalamnya.
  5. Agregasi per kecamatan: jumlah & laju KEJADIAN per 100 ribu penduduk tiap kelas urgensi, lalu ranking:
     laju Tinggi -> laju Sedang -> laju Rendah. Kecamatan dengan < 5 kejadian ditandai data tidak cukup.

Cara pakai (dari root repo):
    python src/modeling/prediksi_final.py                       # model utama: Random Forest
    python src/modeling/prediksi_final.py --model "Gradient-Boosted Trees"
    python src/modeling/bandingkan_model.py                     # bandingkan 4 model sekaligus
Output model utama (Random Forest):
    data/processed/final/keluhan_final.csv              per tweet: kategori & urgensi final + probabilitas (tidak di-commit)
    data/processed/final/kejadian_final.csv             per kejadian (kecamatan, mulai, jumlah tweet, urgensi)
    data/processed/final/agregat_kelurahan_final.csv    per kelurahan (deskriptif, tidak di-commit)
    reports/tables/ranking_kecamatan.csv                42 kecamatan + ranking (di-commit, tanpa teks)
    reports/tables/final_ringkasan.md                   angka untuk Bab 4
Model lain menulis file yang sama dengan akhiran nama model (mis. ranking_kecamatan_gbt.csv),
jadi hasil model utama TIDAK tertimpa.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eksperimen_model import (GOLD, KELUHAN, MODEL, ROOT, SEED, TAB, URG, fitur,  # noqa: E402
                              label_latih_baru, label_review, oversample)

BATAS = ROOT / "data" / "external" / "batas-wilayah" / "jakarta_kelurahan.csv"
POPULASI = ROOT / "data" / "external" / "populasi" / "jakarta_populasi_kelurahan.csv"
OUT = ROOT / "data" / "processed" / "final"
MIN_KEJADIAN = 5
JEDA_HARI = 7
PER = 100_000
RANK_URG = {"Tinggi": 3, "Sedang": 2, "Rendah": 1}
MODEL_UTAMA = "Random Forest"
AKHIRAN = {"Random Forest": "", "Gradient-Boosted Trees": "_gbt", "SVM (linear)": "_svm", "Naive Bayes": "_nb"}


def tandai_kejadian(df):
    """Beri id kejadian: per kecamatan, tweet berurutan waktu dengan jeda <= JEDA_HARI digabung."""
    df = df.copy()
    df["_t"] = pd.to_datetime(df["created_at"])
    df = df.sort_values(["kecamatan", "_t"])
    baru = (df["kecamatan"] != df["kecamatan"].shift()) | (df["_t"].diff() > pd.Timedelta(days=JEDA_HARI))
    df["id_kejadian"] = baru.cumsum()
    return df.drop(columns="_t")


def latih_dan_prediksi(nama_model, train_df, y_train, target_df):
    """Fit model + kembalikan prediksi dan probabilitas untuk target_df."""
    rng = np.random.default_rng(SEED)
    Xtr, Xte = fitur(train_df, target_df, meta=False)
    Xo, yo = oversample(Xtr, np.asarray(y_train), rng)
    m = MODEL[nama_model]()
    m.fit(Xo, yo)
    pred = m.predict(Xte)
    proba = None
    if hasattr(m, "predict_proba"):
        proba = pd.DataFrame(m.predict_proba(Xte), columns=m.classes_, index=target_df.index)
    return pred, proba


def md(df, angka=2):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(f"{v:.{angka}f}" if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(out)


def jalankan(nama_model=MODEL_UTAMA, simpan=True, cetak=True):
    """Jalankan seluruh alur untuk satu model. Mengembalikan dict berisi tabel hasil (untuk perbandingan).
    simpan=False: tidak menulis file apa pun."""
    akhiran = AKHIRAN[nama_model]
    nama_file = lambda nama, ext: f"{nama}{akhiran}.{ext}"

    k = pd.read_csv(KELUHAN, dtype=str)
    gold = pd.read_csv(GOLD, dtype=str, keep_default_na=False)
    baru = label_latih_baru()
    rev = label_review()
    test_ids = set(gold["id_str"])
    assert not (set(baru["id_str"]) | set(rev["id_str"])) & test_ids, "data latih bocor ke test set!"

    # ---------------------------------------------------- label manusia (pedoman baru) per id
    manusia = pd.concat([
        gold[["id_str", "kategori", "urgensi"]].assign(sumber="test_set"),
        baru[["id_str", "kategori", "urgensi"]].assign(sumber="latih"),
        rev[["id_str", "kategori", "urgensi"]].assign(sumber="review"),
    ]).drop_duplicates("id_str").set_index("id_str")

    # ---------------------------------------------------- 1. relevansi
    lat_r = k.merge(pd.concat([baru, rev])[["id_str", "kategori"]], on="id_str")
    yr = np.where(lat_r["kategori"] == "keluhan", "keluhan", "bukan")
    pred_r, proba_r = latih_dan_prediksi(nama_model, lat_r, yr, k)
    k["prob_keluhan"] = proba_r["keluhan"].round(3) if proba_r is not None else np.nan
    k["kategori_model"] = np.where(pred_r == "keluhan", "keluhan", "bukan_keluhan")
    k["kategori_final"] = k["kategori_model"]
    k["sumber_kategori"] = "model"
    ada = k["id_str"].isin(manusia.index)
    k.loc[ada, "kategori_final"] = k.loc[ada, "id_str"].map(manusia["kategori"])
    k.loc[ada, "sumber_kategori"] = k.loc[ada, "id_str"].map(manusia["sumber"])
    k["relevan"] = k["kategori_final"] == "keluhan"

    # ---------------------------------------------------- 2. urgensi
    lat_u = k.merge(baru[(baru["kategori"] == "keluhan") & (baru["urgensi"].isin(URG))][["id_str", "urgensi"]]
                    .rename(columns={"urgensi": "y"}), on="id_str")
    pred_u, proba_u = latih_dan_prediksi(nama_model, lat_u, lat_u["y"].values, k)
    k["urgensi_model"] = pred_u
    if proba_u is not None:
        for c in URG:
            k[f"prob_{c.lower()}"] = proba_u[c].round(3)
    k["urgensi_final"] = k["urgensi_model"]
    k["sumber_urgensi"] = "model"
    ada_u = k["id_str"].isin(manusia.index[manusia["urgensi"].isin(URG)])
    k.loc[ada_u, "urgensi_final"] = k.loc[ada_u, "id_str"].map(manusia["urgensi"])
    k.loc[ada_u, "sumber_urgensi"] = k.loc[ada_u, "id_str"].map(manusia["sumber"])
    k.loc[~k["relevan"], ["urgensi_final", "sumber_urgensi"]] = ""

    kolom = ["id_str", "created_at", "tahun", "bulan", "tipe_akun", "kota", "kecamatan", "kelurahan", "adm4_pcode",
             "level_lokasi", "ambigu_kelurahan", "lokasi_ambigu", "status_wilayah", "kategori_final",
             "sumber_kategori", "prob_keluhan", "urgensi_final", "sumber_urgensi", "urgensi_aturan"] + \
            [c for c in k.columns if c.startswith("prob_") and c != "prob_keluhan"]
    if simpan:
        OUT.mkdir(parents=True, exist_ok=True)
        TAB.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------- 3. agregasi
    batas = pd.read_csv(BATAS, dtype=str)
    pop = pd.read_csv(POPULASI, dtype={"adm4_pcode": str})
    kel = batas[["adm4_pcode", "adm4_name", "adm3_name", "adm3_pcode", "adm2_name"]].merge(
        pop[["adm4_pcode", "penduduk_2025_est"]], on="adm4_pcode")
    kec = kel.groupby(["adm3_pcode", "adm3_name", "adm2_name"], as_index=False)["penduduk_2025_est"].sum()
    rel = k[k["relevan"]]
    berlokasi = rel[rel["kecamatan"].notna() & (rel["kecamatan"] != "")]

    berlokasi = tandai_kejadian(berlokasi)
    k = k.merge(berlokasi[["id_str", "id_kejadian"]], on="id_str", how="left")
    kejadian = berlokasi.assign(_r=berlokasi["urgensi_final"].map(RANK_URG)).groupby("id_kejadian").agg(
        kecamatan=("kecamatan", "first"), mulai=("created_at", "min"), n_tweet=("id_str", "count"), _r=("_r", "max"))
    kejadian["urgensi"] = kejadian["_r"].map({v: k_ for k_, v in RANK_URG.items()})
    kejadian = kejadian.drop(columns="_r")
    if simpan:
        kejadian.to_csv(OUT / nama_file("kejadian_final", "csv"))

    hit = kejadian.pivot_table(index="kecamatan", columns="urgensi", values="n_tweet", aggfunc="count",
                               fill_value=0).reindex(columns=URG, fill_value=0)
    hit.columns = [f"n_{c.lower()}" for c in URG]
    tw = berlokasi.groupby("kecamatan")["id_str"].count().rename("n_tweet")
    kec = kec.merge(hit, left_on="adm3_name", right_index=True, how="left").merge(
        tw, left_on="adm3_name", right_index=True, how="left")
    for c in [f"n_{u.lower()}" for u in URG] + ["n_tweet"]:
        kec[c] = kec[c].fillna(0).astype(int)
    kec["n_kejadian"] = kec[[f"n_{c.lower()}" for c in URG]].sum(axis=1)
    for c in ["kejadian"] + [u.lower() for u in URG]:
        kec[f"per100rb_{c}"] = (kec[f"n_{c}"] / kec["penduduk_2025_est"] * PER).round(2)
    kec["data_cukup"] = kec["n_kejadian"] >= MIN_KEJADIAN
    urut = kec[kec["data_cukup"]].sort_values(["per100rb_tinggi", "per100rb_sedang", "per100rb_rendah"],
                                             ascending=False)
    kec["ranking"] = kec["adm3_pcode"].map({p: i for i, p in enumerate(urut["adm3_pcode"], 1)}).astype("Int64")
    kec = kec.rename(columns={"adm3_pcode": "pcode_kecamatan", "adm3_name": "kecamatan", "adm2_name": "kota"})
    kec = kec.sort_values(["ranking", "n_kejadian"], ascending=[True, False], na_position="last")
    if simpan:
        kec.to_csv(TAB / nama_file("ranking_kecamatan", "csv"), index=False)

    kel_rel = rel[rel["adm4_pcode"].notna() & (rel["adm4_pcode"] != "")]
    hk = kel_rel.pivot_table(index="adm4_pcode", columns="urgensi_final", values="id_str", aggfunc="count",
                             fill_value=0).reindex(columns=URG, fill_value=0)
    hk.columns = [f"n_{c.lower()}" for c in URG]
    agk = kel.merge(hk, left_on="adm4_pcode", right_index=True, how="left").fillna(0)
    agk["n_keluhan"] = agk[[f"n_{c.lower()}" for c in URG]].sum(axis=1).astype(int)
    agk["kelurahan_tebakan"] = agk["adm4_pcode"].map(
        kel_rel.groupby("adm4_pcode")["ambigu_kelurahan"].apply(lambda s: int((s == "True").sum()))).fillna(0).astype(int)
    if simpan:
        agk.to_csv(OUT / nama_file("agregat_kelurahan_final", "csv"), index=False)

    if simpan:
        k[kolom + ["id_kejadian"]].to_csv(OUT / nama_file("keluhan_final", "csv"), index=False)

    # ---------------------------------------------------- 4. ringkasan
    n = len(k)
    L = [f"# Ringkasan Hasil Final (model: {nama_model})", "",
         "## Dari keluhan pipeline ke keluhan relevan", "",
         md(pd.DataFrame([
             ["Keluhan hasil pipeline", n],
             ["Relevan (keluhan jalan rusak)", int(k["relevan"].sum())],
             ["  - dari label manusia", int((k["relevan"] & (k["sumber_kategori"] != "model")).sum())],
             ["  - dari prediksi model", int((k["relevan"] & (k["sumber_kategori"] == "model")).sum())],
             ["Relevan dengan lokasi sampai kecamatan", len(berlokasi)],
             ["Relevan tanpa kecamatan (hanya kota / tanpa lokasi)", int(k["relevan"].sum()) - len(berlokasi)],
             [f"Kejadian (tweet sekecamatan dengan jeda <= {JEDA_HARI} hari digabung)", len(kejadian)],
         ], columns=["Tahap", "Jumlah"])), "",
         "Kategori final menurut sumber label:", "",
         md(pd.crosstab(k["kategori_final"], k["sumber_kategori"]).reset_index()), "",
         "## Distribusi urgensi keluhan relevan", "",
         md(pd.crosstab(rel["urgensi_final"], rel["sumber_urgensi"], margins=True, margins_name="Total")
            .reindex(URG + ["Total"]).reset_index()), "",
         "Urgensi per kejadian (urgensi tertinggi di dalam kejadian):", "",
         md(kejadian["urgensi"].value_counts().reindex(URG).rename_axis("urgensi").reset_index(name="kejadian")), "",
         "Kejadian dengan tweet terbanyak:", "",
         md(kejadian.sort_values("n_tweet", ascending=False).head(5).reset_index()[
             ["kecamatan", "mulai", "n_tweet", "urgensi"]]), "",
         f"## Ranking kecamatan (laju kejadian per 100 ribu penduduk; data cukup = minimal {MIN_KEJADIAN} kejadian)", "",
         f"Kecamatan dengan data cukup: {int(kec['data_cukup'].sum())} dari {len(kec)}.", "",
         md(kec[kec["data_cukup"]][["ranking", "kecamatan", "kota", "n_tweet", "n_kejadian", "n_tinggi", "n_sedang",
                                  "n_rendah", "per100rb_tinggi", "per100rb_sedang", "per100rb_rendah"]]), "",
         "Kecamatan dengan data tidak cukup (jumlah kejadian): " + ", ".join(
             f"{r.kecamatan} ({r.n_kejadian})" for r in kec[~kec["data_cukup"]].itertuples()), ""]
    if simpan:
        (TAB / nama_file("final_ringkasan", "md")).write_text("\n".join(L), encoding="utf-8")
    if cetak:
        print("\n".join(L))
    return {"model": nama_model, "keluhan": k, "kejadian": kejadian, "kecamatan": kec}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL_UTAMA, choices=list(MODEL))
    args = ap.parse_args()
    jalankan(args.model)


if __name__ == "__main__":
    main()
