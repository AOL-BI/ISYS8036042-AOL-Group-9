"""Ekstrak batas wilayah DKI Jakarta (ADM2 kota, ADM3 kecamatan, ADM4 kelurahan)
dari dataset HDX COD-AB Indonesia.

Input : data/external/batas-wilayah/idn_admin_boundaries.geojson.zip
Output: jakarta_adm2.geojson, jakarta_adm3.geojson, jakarta_adm4.geojson,
        jakarta_kelurahan.csv (folder yang sama)
Cara pakai (dari root repo): python src/preprocessing/extract_jakarta_boundaries.py

Hanya pakai library bawaan Python. File dibaca per baris langsung dari zip
(tanpa extract), koordinat dibulatkan ke 6 desimal (~0.1 m).
"""
import collections
import csv
import json
import zipfile

D = "data/external/batas-wilayah"
ZIP = f"{D}/idn_admin_boundaries.geojson.zip"
PROVINSI = b'"adm1_pcode":"ID31"'  # DKI Jakarta
LEVEL_NAMA = {2: "kota/kabupaten", 3: "kecamatan", 4: "kelurahan"}


def kolom(level):
    cols = []
    for lv in range(level, 0, -1):
        cols += [f"adm{lv}_name", f"adm{lv}_pcode"]
    return cols + ["area_sqkm", "center_lat", "center_lon", "valid_on"]


def rnd(c):
    return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 6), round(c[1], 6)]


def ekstrak(z, level):
    keep = kolom(level)
    feats = []
    with z.open(f"idn_admin{level}.geojson") as f:
        for raw in f:
            if not raw.startswith(b'{"type":"Feature"') or PROVINSI not in raw:
                continue
            ft = json.loads(raw.rstrip().rstrip(b","))
            g = ft["geometry"]
            g["coordinates"] = rnd(g["coordinates"])
            feats.append({"type": "Feature",
                          "properties": {k: ft["properties"].get(k) for k in keep},
                          "geometry": g})
    feats.sort(key=lambda x: x["properties"][f"adm{level}_pcode"])
    out = {"type": "FeatureCollection", "name": f"jakarta_adm{level}",
           "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
           "features": feats}
    with open(f"{D}/jakarta_adm{level}.geojson", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    pc = [x["properties"][f"adm{level}_pcode"] for x in feats]
    dup = [k for k, v in collections.Counter(pc).items() if v > 1]
    print(f"ADM{level} ({LEVEL_NAMA[level]}): {len(feats)} fitur, pcode duplikat: {dup or '-'}")
    return feats, keep


def main():
    z = zipfile.ZipFile(ZIP)
    for level in (2, 3):
        ekstrak(z, level)
    feats, keep = ekstrak(z, 4)
    with open(f"{D}/jakarta_kelurahan.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keep)
        w.writeheader()
        for x in feats:
            w.writerow(x["properties"])
    print("CSV atribut kelurahan: jakarta_kelurahan.csv")


if __name__ == "__main__":
    main()
