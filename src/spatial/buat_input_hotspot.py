"""Buat input analisis hotspot: batas 42 kecamatan + atribut ranking (CRISP-DM: Deployment -> analisis spasial).

Menggabungkan
    data/external/batas-wilayah/jakarta_adm3.geojson   batas kecamatan (BPS/HDX, CRS84)
    reports/tables/ranking_kecamatan.csv                hasil src/modeling/prediksi_final.py
menjadi
    reports/gis/kecamatan_hotspot_input.geojson         input src/spatial/kecamatan_hotspot_analysis.py & peta_hotspot.py

Cara pakai (dari root repo, library bawaan Python):
    python src/spatial/buat_input_hotspot.py
Jalankan ulang setiap kali ranking_kecamatan.csv berubah, lalu jalankan ulang analisis Gi*.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATAS = ROOT / "data/external/batas-wilayah/jakarta_adm3.geojson"
RANKING = ROOT / "reports/tables/ranking_kecamatan.csv"
OUT = ROOT / "reports/gis/kecamatan_hotspot_input.geojson"

INT = ["penduduk_2025_est", "n_tweet", "n_kejadian", "n_tinggi", "n_sedang", "n_rendah"]
FLOAT = ["per100rb_kejadian", "per100rb_tinggi", "per100rb_sedang", "per100rb_rendah"]


def main():
    batas = json.loads(BATAS.read_text(encoding="utf-8"))
    with RANKING.open(encoding="utf-8") as f:
        rk = {r["pcode_kecamatan"]: r for r in csv.DictReader(f)}
    fitur = []
    for ft in batas["features"]:
        p = ft["properties"]
        r = rk[p["adm3_pcode"]]
        prop = {"pcode": p["adm3_pcode"], "kecamatan": r["kecamatan"],
                "kota": r["kota"].replace("Kota ", "", 1)}
        prop.update({k: int(r[k]) for k in INT})
        prop.update({k: float(r[k]) for k in FLOAT})
        prop["data_cukup"] = 1 if r["data_cukup"] == "True" else 0
        prop["ranking"] = int(float(r["ranking"])) if r["ranking"] else None
        fitur.append({"type": "Feature", "properties": prop, "geometry": ft["geometry"]})
    if len(fitur) != 42 or len(rk) != 42:
        raise SystemExit("Jumlah kecamatan bukan 42; cek input.")
    gj = {"type": "FeatureCollection", "name": "kecamatan_hotspot_input", "crs": batas["crs"], "features": fitur}
    OUT.write_text(json.dumps(gj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[simpan] {OUT.relative_to(ROOT)} ({len(fitur)} kecamatan)")


if __name__ == "__main__":
    main()
