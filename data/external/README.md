# Data External

Data pendukung dari sumber resmi/publik (bukan hasil scraping).
File geometri berukuran besar **tidak di-commit**. Ikuti langkah di bawah untuk download ulang.

## 1. geoBoundaries: Indonesia ADM2 (Kabupaten/Kota)

| | |
|---|---|
| **Folder** | `geoboundaries/` |
| **Level** | ADM2 = kabupaten/kota (519 unit), **bukan kelurahan** |
| **Tahun batas** | 2020 (source updated Jan 2023) |
| **Sumber asli** | BPS, WFP, OCHA ROAP via [HDX](https://data.humdata.org/dataset/indonesia-administrative-boundary-polygons-lines-and-places-levels-0-4b) |
| **Download** | https://www.geoboundaries.org → Indonesia → ADM2 → `geoBoundaries-IDN-ADM2-all.zip` |
| **Lisensi** | CC BY 3.0 IGO |
| **Issue** | [#7](../../../../issues/7) |

**Isi folder:**

```
geoboundaries/
├── geoBoundaries-IDN-ADM2-all.zip         # arsip asli (95 MB, tidak di-commit)
└── IDN-ADM2/
    ├── geoBoundaries-IDN-ADM2_simplified.geojson   # 11 MB, dipakai untuk peta/EDA (tidak di-commit)
    ├── geoBoundaries-IDN-ADM2-metaData.json/.txt
    ├── geoBoundaries-IDN-ADM2-PREVIEW.png
    └── CITATION-AND-USE-geoBoundaries.txt
```

Versi full-resolution (`.geojson` 159 MB, `.shp`, `.topojson`) ada di dalam zip. Extract kalau butuh presisi tinggi.

**Kolom atribut:** `shapeName` (nama kab/kota), `shapeID`, `shapeGroup` (`IDN`), `shapeType` (`ADM2`)

**Sitasi wajib (untuk laporan):**
> Runfola, D. et al. (2020). geoBoundaries: A global database of political administrative boundaries. *PLoS ONE* 15(4): e0231866. https://doi.org/10.1371/journal.pone.0231866

## 2. Batas Kelurahan (ADM4): _TBD_

## 3. Populasi per Kelurahan (BPS): _TBD_ (issue #8)
