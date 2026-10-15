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
├── jakarta_adm3.geojson               # 42 kecamatan
├── jakarta_adm4.geojson               # 261 kelurahan, unit analisis utama
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
| ID3174 | Kota Jakarta Barat | 8 | 56 |
| ID3175 | Kota Jakarta Utara | 6 | 31 |
| | **Total** | **42** | **261** |

> **Kepulauan Seribu (`ID3101`, 2 kecamatan, 6 kelurahan) tidak diikutkan** (keputusan tim). Filter ini sudah diterapkan di script ekstraksi lewat variabel `EXCLUDE_ADM2` di `src/preprocessing/extract_jakarta_boundaries.py`, jadi semua file di folder ini sudah bersih dan tidak perlu difilter ulang. Untuk mengikutkannya lagi, kosongkan `EXCLUDE_ADM2 = set()` lalu jalankan ulang script-nya.

> **3 poligon non-administratif juga dibuang** supaya jumlahnya sama dengan daftar resmi Pemprov/Kemendagri (42 kecamatan, 261 kelurahan daratan). Di data BPS, kode berakhiran `888`/`555` menandai area yang **bukan** kelurahan resmi:
>
> | pcode | Nama | Luas | Keterangan |
> |---|---|---|---|
> | `ID3175888888` | Danau Sunter | 0,15 km² | danau, juga tercatat sebagai "kecamatan" sendiri |
> | `ID3175555888` | Danau Sunter Dll | 0,50 km² | danau/waduk, juga tercatat sebagai "kecamatan" sendiri |
> | `ID3174080888` | Prepedan | 1,79 km² | area di Kec. Kalideres, berbatasan dengan Tegal Alur, Pegadungan, Kamal |
>
> Akibatnya ada **3 lubang kecil di peta ADM4** (terlihat di preview). Titik keluhan yang jatuh di area Prepedan tidak akan dapat kelurahan saat spatial join; kalau jumlahnya signifikan, tetapkan ke kelurahan terdekat. Di ADM3 tidak ada lubang untuk Prepedan (masuk Kec. Kali Deres). Aturannya ada di variabel `KODE_NON_ADMIN` pada script ekstraksi.

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

> `pcode` = kode wilayah BPS dengan prefix `ID`. Data Pemprov DKI memakai kode Kemendagri yang formatnya berbeda, jadi join ke data populasi dilakukan lewat nama (lihat bagian 2).

**Buka di QGIS:** drag & drop file `.geojson` ke kanvas, atau *Layer → Add Layer → Add Vector Layer*.

**Sitasi:** BPS & OCHA ROAP. *Indonesia – Subnational Administrative Boundaries*. Humanitarian Data Exchange (HDX).

## 2. Estimasi Penduduk per Kelurahan (2025)

| | |
|---|---|
| **Folder** | `populasi/` |
| **File utama** | `jakarta_populasi_kelurahan.csv` (261 kelurahan) |
| **Metode** | Penduduk per kelurahan 2017 diskalakan ke total penduduk per kota BPS 2025 |
| **Issue** | [#8](../../../../issues/8) |

### Kenapa estimasi, bukan data langsung?

Tidak ada data penduduk per kelurahan yang baru dan bisa di-download sekaligus. Dataset per kelurahan di Satu Data Jakarta berhenti di 2013–2019, sedangkan BPS hanya menerbitkan angka terbaru sampai level kota. Jadi keduanya digabung:

```
penduduk_2025_est = penduduk_2017 × (total BPS 2025 kota ÷ total 2017 kota)
```

**Asumsi:** proporsi penduduk antar-kelurahan di dalam satu kota tidak berubah sejak 2017. Total per kota dijamin sama persis dengan angka BPS.

| Kota | Penduduk 2017 (Pemprov) | BPS 2025 | Faktor skala |
|---|---|---|---|
| Jakarta Selatan | 2.189.015 | 2.219.225 | 1,0138 |
| Jakarta Timur | 2.946.594 | 3.085.058 | 1,0470 |
| Jakarta Pusat | 1.138.516 | 1.038.396 | 0,9121 |
| Jakarta Barat | 2.326.721 | 2.487.199 | 1,0690 |
| Jakarta Utara | 1.715.581 | 1.819.009 | 1,0603 |
| **Total** | **10.316.427** | **10.648.887** | |

### Isi folder

```
populasi/
├── jakarta_populasi_kelurahan.csv         # HASIL: pakai file ini
├── jakarta_kepadatan_preview.png          # peta kepadatan hasil estimasi
├── bps_penduduk_kota_2025.csv             # input: total penduduk per kota (BPS)
├── satudata_penduduk_wni_2017.csv         # input: penduduk WNI per kelurahan & jenis kelamin
├── satudata_penduduk_usia_2013.csv        # tidak dipakai (terlalu lama)
└── satudata_kepadatan_luas_2013-2019.csv  # tidak dipakai (kolom luas rusak, lihat catatan)
```

**Cara generate ulang** (dari root repo):

```bash
python src/preprocessing/build_populasi_kelurahan.py
```

Kalau ada angka BPS yang lebih baru, cukup ganti isi `bps_penduduk_kota_2025.csv` lalu jalankan ulang script-nya.

### Kolom `jakarta_populasi_kelurahan.csv`

| Kolom | Keterangan |
|---|---|
| `adm4_pcode` | kode kelurahan, **kunci join** ke `jakarta_adm4.geojson` |
| `adm4_name`, `adm3_pcode`, `adm3_name`, `adm2_pcode`, `adm2_name` | nama kelurahan, kecamatan, kota |
| `penduduk_2017` | penduduk WNI 2017 (laki-laki + perempuan), data asli Pemprov |
| `faktor_skala` | faktor pengali per kota (lihat tabel di atas) |
| `penduduk_2025_est` | **estimasi penduduk 2025**, kolom yang dipakai untuk analisis |
| `area_sqkm` | luas kelurahan (km²) dari batas wilayah HDX |
| `kepadatan_2025_est` | estimasi kepadatan (jiwa/km²) = `penduduk_2025_est ÷ area_sqkm` |

### Sumber

| Data | Sumber | Catatan |
|---|---|---|
| Penduduk per kelurahan 2017 | [Satu Data Jakarta: Jumlah Penduduk WNI Berdasarkan Kelurahan](https://data.go.id/dataset/dataset/data-jumlah-penduduk-wni-di-provinsi-dki-jakarta-berdasarkan-kelurahan) | data registrasi penduduk (terdaftar), hanya WNI |
| Penduduk per kota 2025 | BPS Provinsi DKI Jakarta, [tabel penduduk menurut kabupaten/kota](https://jakarta.bps.go.id/en/statistics-table/2/MTI3MCMy/jumlah-penduduk-menurut-kabupaten-kota-di-provinsi-dki-jakarta-.html) | **angka diambil dari [kutipan media](https://dataloka.id/humaniora/4899/jumlah-penduduk-jakarta-2025-berdasarkan-kabupaten-kota/), belum dicek langsung ke tabel BPS** |

### Catatan & keterbatasan (tulis di metodologi laporan)

- **Ini estimasi, bukan hasil sensus.** Kelurahan yang tumbuh jauh lebih cepat/lambat dari rata-rata kotanya sejak 2017 (misalnya ada apartemen baru atau relokasi) akan meleset.
- **Dua sumber beda konsep.** Data Pemprov = penduduk *terdaftar* (KTP/KK); BPS = penduduk yang *tinggal*. Ini terlihat di Jakarta Pusat: yang terdaftar di 2017 lebih banyak daripada yang tinggal di 2025 (faktor 0,91).
- **Pencocokan nama:** 261 dari 261 kelurahan cocok. 12 kelurahan beda ejaan antara dua sumber (mis. *Kalianyar/Kali Anyar*, *Tanjung Priuk/Tanjung Priok*, *Krendang/Kerendang*); 6 beda spasi ditangani otomatis, 6 beda huruf lewat daftar `ALIAS` di script.
- **`satudata_kepadatan_luas_2013-2019.csv` jangan dipakai menghitung penduduk:** mulai 2014 kolom luasnya salah satuan (total luas Jakarta jadi 6.785 km², seharusnya ±662 km²).
