# Data External

Data pendukung dari sumber resmi/publik (bukan hasil scraping).
Arsip mentah berukuran besar **tidak di-commit**. Ikuti langkah di bawah untuk download ulang.

## 1. Batas Wilayah DKI Jakarta (ADM2–ADM4)

| | |
|---|---|
| **Folder** | `batas-wilayah/` |
| **Level** | ADM2 = kota/kabupaten · ADM3 = kecamatan · ADM4 = kelurahan |
| **Tahun batas** | `valid_on` 2020-04-01 |
| **Sumber** | BPS via [HDX: Indonesia Subnational Administrative Boundaries (COD-AB)](https://data.humdata.org/dataset/indonesia-administrative-boundary-polygons-lines-and-places-levels-0-4b) |
| **Download** | `idn_admin_boundaries.geojson.zip` (456 MB) dari halaman HDX di atas |
| **CRS** | WGS84 (EPSG:4326) |
| **Lisensi** | CC BY-IGO |
| **Issue** | [#7](../../../../issues/7) |

**Isi folder:**

```
batas-wilayah/
├── idn_admin_boundaries.geojson.zip   # arsip asli ADM0–ADM4 se-Indonesia (456 MB, tidak di-commit)
├── jakarta_adm2.geojson               # 5 kota administrasi
├── jakarta_adm3.geojson               # 44 kecamatan
├── jakarta_adm4.geojson               # 264 kelurahan, unit analisis utama
├── jakarta_kelurahan.csv              # atribut kelurahan tanpa geometri, buat join ke data BPS
└── jakarta_adm4_preview.png
```

**Cara generate ulang:** taruh zip di folder ini, lalu jalankan dari root repo:

```bash
python src/preprocessing/extract_jakarta_boundaries.py
```

**Jumlah wilayah per kota/kabupaten:**

| adm2_pcode | Kota/Kabupaten | Kecamatan | Kelurahan |
|---|---|---|---|
| ID3171 | Kota Jakarta Selatan | 10 | 65 |
| ID3172 | Kota Jakarta Timur | 10 | 65 |
| ID3173 | Kota Jakarta Pusat | 8 | 44 |
| ID3174 | Kota Jakarta Barat | 8 | 57 |
| ID3175 | Kota Jakarta Utara | 8 | 33 |
| | **Total** | **44** | **264** |

> **Kepulauan Seribu (`ID3101`, 2 kecamatan, 6 kelurahan) tidak diikutkan** (keputusan tim). Filter ini sudah diterapkan di script ekstraksi lewat variabel `EXCLUDE_ADM2` di `src/preprocessing/extract_jakarta_boundaries.py`, jadi semua file di folder ini sudah bersih dan tidak perlu difilter ulang. Untuk mengikutkannya lagi, kosongkan `EXCLUDE_ADM2 = set()` lalu jalankan ulang script-nya.

**Kolom** (tiap file berisi kolom level itu + semua level di atasnya):

| Kolom | Keterangan |
|---|---|
| `adm4_name`, `adm4_pcode` | nama & kode kelurahan (**primary key** di ADM4, contoh `ID3171010001`) |
| `adm3_name`, `adm3_pcode` | kecamatan |
| `adm2_name`, `adm2_pcode` | kota/kabupaten administrasi |
| `adm1_name`, `adm1_pcode` | provinsi (`ID31`) |
| `area_sqkm` | luas (km²) |
| `center_lat`, `center_lon` | titik tengah wilayah |
| `valid_on` | tanggal berlaku batas |

> `pcode` = kode wilayah BPS dengan prefix `ID`. Buang prefix-nya (`3171010001`) untuk join ke tabel BPS (issue #8).

**Buka di QGIS:** drag & drop file `.geojson` ke kanvas, atau *Layer → Add Layer → Add Vector Layer*.

**Sitasi:** BPS & OCHA ROAP. *Indonesia – Subnational Administrative Boundaries*. Humanitarian Data Exchange (HDX).

## 2. Populasi per Kelurahan (BPS): _TBD_ (issue #8)
