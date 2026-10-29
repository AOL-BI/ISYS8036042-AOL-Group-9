"""Peta prioritas & peta Getis-Ord Gi* untuk paper (Python murni, jalan di Windows tanpa QGIS).

Script ini TIDAK menghitung ulang Gi*. Statistik Gi* dihitung oleh
src/spatial/kecamatan_hotspot_analysis.py (PySAL esda/libpysal di dalam QGIS) dan disimpan di
reports/gis/outputs/kecamatan_hotspot_statistics.csv. Di sini kita hanya:
  1. membuat kelas prioritas dari `ranking` (hanya 17 kecamatan dengan >= 5 kejadian),
  2. menggambar peta prioritas dan peta z-score Gi* (bahasa Inggris, untuk paper),
  3. menulis tabel ringkasan untuk Bab 4.

Aturan prioritas (sama dengan assign_priority() di kecamatan_hotspot_analysis.py):
  - Hanya kecamatan dengan data_cukup = 1 (n_kejadian >= 5) yang diberi prioritas.
  - Urutan = kolom `ranking` dari src/modeling/prediksi_final.py
    (laju kejadian High -> Medium -> Low per 100.000 penduduk).
  - Dibagi tiga kelompok berurutan berukuran ceil(n/3): untuk n = 17 -> 1-6, 7-12, 13-17.
  - Sisanya: "Insufficient data (<5 incidents)" (abu-abu, tanpa kelas).
  Label sengaja "Priority 1/2/3", bukan High/Medium/Low, supaya tidak tertukar dengan kelas urgensi.

Cara pakai (dari root repo):
    python src/spatial/peta_hotspot.py
Butuh: pandas, numpy, matplotlib (sudah ada di requirements.txt).
Output:
    reports/figures/hs_01_prioritas_kecamatan.png
    reports/figures/hs_02_gistar_zscore.png
    reports/figures/hs_01_prioritas_kecamatan_paper.png   (selebar 1 kolom paper, tanpa judul)
    reports/figures/hs_02_gistar_zscore_paper.png         (selebar 1 kolom paper, tanpa judul)
    reports/tables/hotspot_prioritas.csv
    reports/tables/hotspot_ringkasan.md
"""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.patches import Patch, Polygon  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/gis/kecamatan_hotspot_input.geojson"
STATS = ROOT / "reports/gis/outputs/kecamatan_hotspot_statistics.csv"
FIG = ROOT / "reports/figures"
TAB = ROOT / "reports/tables"

ALPHA = 0.05
N_KELAS = 3
GI_VARS = [  # prefix kolom di STATS, judul panel
    ("rate", "All incidents per 100,000 residents"),
    ("high", "High-urgency incidents per 100,000 residents"),
]
EXTRA_VARS = [("count", "Incident count (sensitivity)")]

# Warna: prioritas = satu hue berurutan (gelap = lebih prioritas); Gi* = divergen biru-abu-merah.
WARNA_PRIORITAS = {"Priority 1": "#a8401a", "Priority 2": "#e0703f", "Priority 3": "#f5b48f"}
WARNA_KOSONG = "#e4e3df"
INK, INK_MUTED, OUTLINE = "#1f1f1d", "#6b6a66", "#ffffff"
CMAP_Z = LinearSegmentedColormap.from_list(
    "gi_div", ["#184f95", "#6da7ec", "#f0efec", "#ef8f86", "#b3261e"])
SUMBER = ("Sources: X/Twitter road-damage complaints (model + human labels, incidents merged within 7 days); BPS / OCHA HDX boundaries (2020); "
          "population estimate 2025. Mainland DKI Jakarta, 42 kecamatan.")


# ----------------------------------------------------------------------------- data
def baca_geometri():
    """GeoJSON -> {pcode: [ring_xy, ...]} dalam km (proyeksi equirectangular lokal), + atribut."""
    gj = json.loads(INPUT.read_text(encoding="utf-8"))
    lat0 = np.mean([c[1] for f in gj["features"] for c in _ring_luar(f["geometry"])])
    kx, ky = 111.320 * math.cos(math.radians(lat0)), 110.574  # km per derajat
    geom, attr = {}, []
    for f in gj["features"]:
        p = f["properties"]
        polys = f["geometry"]["coordinates"]
        if f["geometry"]["type"] == "Polygon":
            polys = [polys]
        geom[p["pcode"]] = [np.array([[x * kx, y * ky] for x, y, *_ in poly[0]]) for poly in polys]
        attr.append(p)
    return geom, pd.DataFrame(attr)


def _ring_luar(g):
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    return [c for poly in polys for c in poly[0]]


def kelas_prioritas(df):
    """Priority 1/2/3 dari `ranking` untuk kecamatan data_cukup; sisanya Insufficient data."""
    df = df.copy()
    ok = df["data_cukup"].astype(bool) & df["ranking"].notna()
    n = int(ok.sum())
    ukuran = math.ceil(n / N_KELAS)
    df["priority_group"] = np.where(ok, np.ceil(df["ranking"] / ukuran), np.nan)
    df["priority_label"] = df["priority_group"].map(lambda g: f"Priority {int(g)}" if pd.notna(g) else
                                                    "Insufficient data")
    batas = {f"Priority {k + 1}": (k * ukuran + 1, min((k + 1) * ukuran, n)) for k in range(N_KELAS)}
    return df, batas


def gabung():
    geom, attr = baca_geometri()
    st = pd.read_csv(STATS)
    kolom = ["pcode"] + [c for c in st.columns if c.split("_")[0] in {"rate", "high", "count"}] + ["neighbor_count"]
    df = attr.merge(st[kolom], on="pcode", how="left", validate="one_to_one")
    if len(df) != 42 or df["rate_z"].isna().any():
        raise SystemExit("Statistik Gi* tidak lengkap. Jalankan dulu src/spatial/kecamatan_hotspot_analysis.py.")
    df, batas = kelas_prioritas(df)
    return geom, df, batas


# ----------------------------------------------------------------------------- gambar
def gambar_poligon(ax, geom, df, warna, hatch=None, lw=0.6, edge=OUTLINE, ls="-"):
    for _, r in df.iterrows():
        for ring in geom[r["pcode"]]:
            ax.add_patch(Polygon(ring, closed=True, facecolor=warna(r), edgecolor=edge, linewidth=lw,
                                 hatch=hatch(r) if hatch else None, linestyle=ls))


def atur_peta(ax, geom, skala=1.0, ornamen=True):
    xy = np.vstack([ring for rings in geom.values() for ring in rings])
    pad = 1.0
    ax.set_xlim(xy[:, 0].min() - pad, xy[:, 0].max() + pad)
    ax.set_ylim(xy[:, 1].min() - pad, xy[:, 1].max() + pad)
    ax.set_aspect("equal")
    ax.axis("off")
    if not ornamen:
        return
    # skala 5 km + panah utara
    x0, y0 = xy[:, 0].min(), xy[:, 1].min() - 0.2
    ax.plot([x0, x0 + 5], [y0, y0], color=INK, lw=2 * skala, solid_capstyle="butt")
    for t in (0, 5):
        ax.plot([x0 + t, x0 + t], [y0 - 0.25, y0 + 0.25], color=INK, lw=skala)
    ax.text(x0 + 2.5, y0 + 0.45, "5 km", ha="center", va="bottom", fontsize=8 * skala, color=INK)
    xn, yn = xy[:, 0].max() - 0.5, xy[:, 1].max() - 3.0
    ax.annotate("N", xy=(xn, yn + 2.2), xytext=(xn, yn), ha="center", va="center", fontsize=10 * skala,
                fontweight="bold", color=INK, arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2 * skala))


def centroid(rings):
    ring = max(rings, key=lambda r: len(r))
    x, y = ring[:, 0], ring[:, 1]
    a = x[:-1] * y[1:] - x[1:] * y[:-1]
    A = a.sum() / 2
    if abs(A) < 1e-9:
        return x.mean(), y.mean()
    return ((x[:-1] + x[1:]) * a).sum() / (6 * A), ((y[:-1] + y[1:]) * a).sum() / (6 * A)


def peta_prioritas(geom, df, batas):
    fig = plt.figure(figsize=(11, 7.2), dpi=200)
    ax = fig.add_axes([0.02, 0.08, 0.62, 0.82])
    gambar_poligon(ax, geom, df,
                   warna=lambda r: WARNA_PRIORITAS.get(r["priority_label"], WARNA_KOSONG),
                   hatch=lambda r: None if r["priority_label"] in WARNA_PRIORITAS else "////")
    for _, r in df[df["ranking"].notna()].iterrows():
        cx, cy = centroid(geom[r["pcode"]])
        gelap = r["priority_label"] == "Priority 1"
        ax.text(cx, cy, str(int(r["ranking"])), ha="center", va="center", fontsize=8, fontweight="bold",
                color="#ffffff" if gelap else INK)
    atur_peta(ax, geom)

    n_ok = int(df["ranking"].notna().sum())
    fig.text(0.02, 0.955, "Road-Damage Repair Priority by Kecamatan, DKI Jakarta", fontsize=15,
             fontweight="bold", color=INK)
    fig.text(0.02, 0.918, f"{n_ok} kecamatan with ≥5 incidents, ranked by High → Medium → Low "
             "incident rate per 100,000 residents. Numbers on the map are ranks.", fontsize=9.5, color=INK_MUTED)

    leg = [Patch(facecolor=WARNA_PRIORITAS[k], edgecolor="#bdbcb8", label=f"{k}  (rank {a}–{b})")
           for k, (a, b) in batas.items()]
    leg.append(Patch(facecolor=WARNA_KOSONG, edgecolor="#bdbcb8", hatch="////",
                     label=f"Insufficient data (<5 incidents), n = {42 - n_ok}"))
    fig.legend(handles=leg, loc="upper left", bbox_to_anchor=(0.66, 0.89), frameon=False, fontsize=9,
               title="Priority class", title_fontsize=10, alignment="left")

    # daftar ranking di kanan
    urut = df[df["ranking"].notna()].sort_values("ranking")
    baris = [f"{int(r.ranking):>2}. {r.kecamatan}  ({r.per100rb_tinggi:.2f} / {r.per100rb_kejadian:.2f})"
             for r in urut.itertuples()]
    fig.text(0.66, 0.66, "Rank. Kecamatan  (High rate / all rate)", fontsize=8.5, fontweight="bold", color=INK)
    fig.text(0.66, 0.645, "\n".join(baris), fontsize=8.2, color=INK, va="top", family="monospace",
             linespacing=1.45)
    fig.text(0.02, 0.03, SUMBER + "\nPriority classes are relative groups of the ranking, not Gi* significance "
             "classes. Gray areas may still have complaints but too few incidents to rank.",
             fontsize=7.5, color=INK_MUTED)
    out = FIG / "hs_01_prioritas_kecamatan.png"
    fig.savefig(out, facecolor="#ffffff")
    plt.close(fig)
    return out


def peta_gistar(geom, df):
    vmax = math.ceil(max(df[f"{p}_z"].abs().max() for p, _ in GI_VARS) * 2) / 2
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    fig = plt.figure(figsize=(12, 7.0), dpi=200)
    axes = [fig.add_axes([0.01, 0.17, 0.47, 0.66]), fig.add_axes([0.50, 0.17, 0.47, 0.66])]
    for ax, (p, judul) in zip(axes, GI_VARS):
        gambar_poligon(ax, geom, df, warna=lambda r, p=p: CMAP_Z(norm(r[f"{p}_z"])))
        raw = df[df[f"{p}_p_perm_2s"] <= ALPHA]
        gambar_poligon(ax, geom, raw, warna=lambda r: "none", lw=1.6, edge=INK, ls=(0, (3, 2)))
        for _, r in raw.iterrows():
            cx, cy = centroid(geom[r["pcode"]])
            ax.text(cx, cy, r["kecamatan"], ha="center", va="center", fontsize=6.8, color=INK,
                    bbox=dict(boxstyle="round,pad=0.15", fc="#ffffffcc", ec="none"))
        atur_peta(ax, geom)
        n_fdr = int((df[f"{p}_q_bh"] <= ALPHA).sum())
        ax.set_title(f"{judul}\n{n_fdr} significant after BH-FDR (q ≤ 0.05) · min q = "
                     f"{df[f'{p}_q_bh'].min():.3f}", fontsize=10, color=INK, loc="left")

    cax = fig.add_axes([0.30, 0.115, 0.40, 0.02])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=CMAP_Z), cax=cax, orientation="horizontal")
    cb.set_label("Gi* z-score  (blue = low values clustered, red = high values clustered)", fontsize=8.5,
                 color=INK)
    cb.ax.tick_params(labelsize=8, colors=INK)
    cb.outline.set_visible(False)

    fig.text(0.01, 0.955, "Getis-Ord Gi* of Road-Damage Incidents by Kecamatan, DKI Jakarta", fontsize=15,
             fontweight="bold", color=INK)
    fig.text(0.01, 0.915, "Queen contiguity (binary, focal unit included), 9,999 conditional permutations, "
             "two-sided, Benjamini–Hochberg FDR per variable. Dashed outline = p ≤ 0.05 before FDR "
             "(exploratory only).", fontsize=9, color=INK_MUTED)
    fig.text(0.01, 0.015, SUMBER, fontsize=7.5, color=INK_MUTED)
    out = FIG / "hs_02_gistar_zscore.png"
    fig.savefig(out, facecolor="#ffffff")
    plt.close(fig)
    return out


# ------------------------------------------------- versi selebar 1 kolom paper IEEE (±3,4 inci)
# Tanpa judul (judul ada di caption Word) dan huruf dibuat besar relatif ukuran cetak.
def peta_prioritas_paper(geom, df, batas):
    fig = plt.figure(figsize=(3.4, 3.3), dpi=300)
    ax = fig.add_axes([0.0, 0.14, 1.0, 0.86])
    plt.rcParams["hatch.linewidth"] = 0.4
    gambar_poligon(ax, geom, df, lw=0.3,
                   warna=lambda r: WARNA_PRIORITAS.get(r["priority_label"], WARNA_KOSONG),
                   hatch=lambda r: None if r["priority_label"] in WARNA_PRIORITAS else "////")
    for _, r in df[df["ranking"].notna()].iterrows():
        cx, cy = centroid(geom[r["pcode"]])
        ax.text(cx, cy, str(int(r["ranking"])), ha="center", va="center", fontsize=5.5, fontweight="bold",
                color="#ffffff" if r["priority_label"] == "Priority 1" else INK)
    atur_peta(ax, geom, skala=0.65)
    n_ok = int(df["ranking"].notna().sum())
    leg = [Patch(facecolor=WARNA_PRIORITAS[k], edgecolor="#bdbcb8", lw=0.4, label=f"{k} (rank {a}–{b})")
           for k, (a, b) in batas.items()]
    leg.append(Patch(facecolor=WARNA_KOSONG, edgecolor="#bdbcb8", lw=0.4, hatch="////",
                     label=f"Insufficient data (<5 incidents, n = {42 - n_ok})"))
    fig.legend(handles=leg, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=2, frameon=False,
               fontsize=6, handlelength=1.4, columnspacing=1.0, handletextpad=0.5)
    out = FIG / "hs_01_prioritas_kecamatan_paper.png"
    fig.savefig(out, facecolor="#ffffff")
    plt.close(fig)
    return out


def peta_gistar_paper(geom, df):
    vmax = math.ceil(max(df[f"{p}_z"].abs().max() for p, _ in GI_VARS) * 2) / 2
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    fig = plt.figure(figsize=(3.4, 2.55), dpi=300)
    axes = [fig.add_axes([0.0, 0.17, 0.495, 0.75]), fig.add_axes([0.505, 0.17, 0.495, 0.75])]
    for i, (ax, (p, _)) in enumerate(zip(axes, GI_VARS)):
        gambar_poligon(ax, geom, df, lw=0.25, warna=lambda r, p=p: CMAP_Z(norm(r[f"{p}_z"])))
        raw = df[df[f"{p}_p_perm_2s"] <= ALPHA]
        gambar_poligon(ax, geom, raw, warna=lambda r: "none", lw=0.8, edge=INK, ls=(0, (2, 1.2)))
        atur_peta(ax, geom, skala=0.55, ornamen=(i == 0))
        ax.set_title(["(a) All incidents", "(b) High-urgency incidents"][i],
                     fontsize=6.3, color=INK, pad=2)
    cax = fig.add_axes([0.2, 0.115, 0.6, 0.03])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=CMAP_Z), cax=cax, orientation="horizontal")
    cb.set_label("Gi* z-score (dashed outline: p ≤ 0.05 before FDR)", fontsize=5.8, color=INK, labelpad=1.5)
    cb.ax.tick_params(labelsize=5.5, colors=INK, length=2, width=0.4, pad=1)
    cb.outline.set_visible(False)
    out = FIG / "hs_02_gistar_zscore_paper.png"
    fig.savefig(out, facecolor="#ffffff")
    plt.close(fig)
    return out


# ----------------------------------------------------------------------------- tabel
def md(df, nd=2):
    df = df.copy()
    for c in df.select_dtypes("float").columns:
        df[c] = df[c].map(lambda v: "" if pd.isna(v) else f"{v:.{nd}f}")
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    rows = ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def tabel(df, batas):
    kol = ["ranking", "priority_label", "kecamatan", "kota", "n_kejadian", "n_tinggi", "per100rb_tinggi",
           "per100rb_kejadian", "rate_z", "rate_p_perm_2s", "rate_q_bh", "high_z", "high_p_perm_2s", "high_q_bh"]
    pr = df.sort_values(["ranking", "kecamatan"], na_position="last")[kol]
    TAB.mkdir(parents=True, exist_ok=True)
    pr.to_csv(TAB / "hotspot_prioritas.csv", index=False)

    ring = []
    for p, judul in GI_VARS + EXTRA_VARS:
        raw = df[df[f"{p}_p_perm_2s"] <= ALPHA].sort_values(f"{p}_z", ascending=False)
        ring.append({
            "variable": judul,
            "p ≤ 0.05 (before FDR)": len(raw),
            "q ≤ 0.05 (after FDR)": int((df[f"{p}_q_bh"] <= ALPHA).sum()),
            "min p": df[f"{p}_p_perm_2s"].min(), "min q": df[f"{p}_q_bh"].min(),
            "exploratory high clusters (z > 0, p ≤ 0.05)": ", ".join(raw[raw[f"{p}_z"] > 0]["kecamatan"]) or "-",
            "exploratory low clusters (z < 0, p ≤ 0.05)": ", ".join(raw[raw[f"{p}_z"] < 0]["kecamatan"]) or "-",
        })
    ring = pd.DataFrame(ring)

    tampil = pr[pr["ranking"].notna()].copy()
    tampil["ranking"] = tampil["ranking"].astype(int)
    tampil = tampil[["ranking", "priority_label", "kecamatan", "n_kejadian", "per100rb_tinggi",
                     "per100rb_kejadian", "rate_z", "rate_q_bh", "high_z", "high_q_bh"]]
    L = ["# Ringkasan Hotspot (Getis-Ord Gi*) & Prioritas", "",
         "Dibuat oleh `src/spatial/peta_hotspot.py` dari `reports/gis/outputs/kecamatan_hotspot_statistics.csv`.", "",
         "## Gi* per variabel", "", md(ring, 4), "",
         "Tidak ada kecamatan yang signifikan setelah koreksi FDR. Kecamatan dengan p ≤ 0,05 sebelum koreksi "
         "hanya dilaporkan sebagai temuan eksploratif.", "",
         "## Kelas prioritas", "",
         "Hanya kecamatan dengan ≥ 5 kejadian yang diberi kelas; urutan dari `ranking` "
         "(laju Tinggi → Sedang → Rendah per 100.000 penduduk).", "",
         ", ".join(f"{k}: ranking {a}–{b}" for k, (a, b) in batas.items())
         + f"; Insufficient data: {int(df['ranking'].isna().sum())} kecamatan.", "",
         md(tampil, 3), "",
         "Tabel lengkap 42 kecamatan: `reports/tables/hotspot_prioritas.csv`.", ""]
    (TAB / "hotspot_ringkasan.md").write_text("\n".join(L), encoding="utf-8")
    return ring


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    geom, df, batas = gabung()
    f1 = peta_prioritas(geom, df, batas)
    f2 = peta_gistar(geom, df)
    f3 = peta_prioritas_paper(geom, df, batas)
    f4 = peta_gistar_paper(geom, df)
    ring = tabel(df, batas)
    print(ring.to_string(index=False))
    print("\nKelas:", df["priority_label"].value_counts().to_dict())
    for f in (f1, f2, f3, f4, TAB / "hotspot_prioritas.csv", TAB / "hotspot_ringkasan.md"):
        print("[simpan]", f.relative_to(ROOT))


if __name__ == "__main__":
    main()
