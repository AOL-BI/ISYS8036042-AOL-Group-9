# Hotspot Getis-Ord Gi* dan kelas prioritas kecamatan DKI Jakarta

## Ringkasan cepat

| Mau apa | Perintah (dari root repo) | Butuh QGIS? |
|---|---|---|
| Peta + tabel untuk paper | `python src/spatial/peta_hotspot.py` | Tidak (pandas, numpy, matplotlib) |
| Hitung ulang Gi* + proyek/peta QGIS (Windows) | `src\spatial\run_hotspot_windows.bat --install` sekali, lalu `src\spatial\run_hotspot_windows.bat` | Ya |
| Hitung ulang Gi* + proyek/peta QGIS (macOS) | lihat bagian *Eksekusi ulang* | Ya |

Hasil Gi* sudah tersimpan di `reports/gis/outputs/kecamatan_hotspot_statistics.csv`, jadi untuk paper cukup perintah pertama. Keluarannya:

- `reports/figures/hs_01_prioritas_kecamatan.png`: peta kelas prioritas (17 kecamatan beranking + 25 abu-abu).
- `reports/figures/hs_02_gistar_zscore.png`: peta z-score Gi* laju semua kejadian dan laju urgensi Tinggi.
- `reports/tables/hotspot_ringkasan.md`, `reports/tables/hotspot_prioritas.csv`: tabel untuk Bab 4.

Gi* menjawab *apakah keluhan mengelompok secara spasial*; kelas prioritas menjawab *kecamatan mana yang didahulukan*. Keduanya terpisah: kelas prioritas **bukan** hasil uji Gi*.

## Hasil dan pengaturan

Analisis Gi* mengikuti parameter pada lampiran: ID `pcode`, **Queen contiguity orde 1**, focal observation disertakan (Gi*, bukan Gi), **9999 permutasi**, FDR **0,05**, dan dua variabel utama `per100rb_kejadian` serta `per100rb_tinggi`. Analisis tambahan `n_kejadian` tetap tersedia sebagai sensitivitas terhadap jumlah absolut. Setiap variabel diuji dan dikoreksi tersendiri.

Eksekusi memakai Python bawaan QGIS 3.44.14, PyQGIS untuk proyek/layout, serta esda 2.10.0 dan libpysal 4.15.1 untuk statistik. **Tidak ada eksekusi GeoDa yang diklaim.** Parameter yang diminta disamakan, tetapi nilai numerik tidak dijamin identik dengan GeoDa: seed, generator random, dan konvensi ekor uji dapat berbeda. Implementasi di sini secara eksplisit memakai uji permutasi kondisional **dua sisi** dan BH FDR. Jika Bab 3 menyebut perangkat lunak, tuliskan implementasi PySAL/PyQGIS ini; jangan menyebut hasil sebagai keluaran GeoDa tanpa menjalankannya di sana.

| Variabel | Jumlah p ≤ 0,05 sebelum FDR | Jumlah q ≤ 0,05 | p minimum | q minimum |
|---|---:|---:|---:|---:|
| `per100rb_kejadian` | 4 | 0 | 0,0025 | 0,1050 |
| `per100rb_tinggi` | 4 | 0 | 0,0132 | 0,4095 |
| `n_kejadian` (tambahan) | 2 | 0 | 0,0134 | 0,5628 |

**Tidak ada hotspot atau coldspot signifikan setelah FDR** pada ketiga variabel. Peta prioritas tetap berwarna karena memakai ranking, bukan hasil uji Gi*. Pada peta Gi* QGIS seluruh poligon abu-abu (kelas signifikansi); peta paper `hs_02` menampilkan z-score kontinu dengan garis putus-putus untuk p ≤ 0,05 sebelum FDR (eksploratif).

Sebelum koreksi, hasil eksploratif laju kejadian menandai Tebet, Tanah Abang, Menteng sebagai hotspot dan Pademangan sebagai coldspot. Laju urgensi tinggi menandai Kebayoran Baru, Tebet, Menteng sebagai hotspot dan Taman Sari sebagai coldspot. Jumlah absolut menandai Kebayoran Baru sebagai hotspot dan Pademangan sebagai coldspot. Temuan ini **tidak lolos FDR** dan tidak boleh disebut hotspot terkonfirmasi.

## Aturan kelas prioritas

Kelas prioritas hanya diberikan pada kecamatan yang memang masuk ranking, yaitu yang punya **≥ 5 kejadian** (`data_cukup = 1`, 17 kecamatan). Urutannya memakai kolom `ranking` dari `src/modeling/prediksi_final.py`:

1. laju kejadian urgensi Tinggi per 100.000 penduduk, menurun;
2. jika sama, laju Sedang, menurun;
3. jika masih sama, laju Rendah, menurun.

Ranking lalu dibagi tiga kelompok berurutan berukuran `ceil(n/3)`:

| `priority_label` | Ranking | Jumlah | Warna |
|---|---|---:|---|
| Priority 1 | 1–6 | 6 | Oranye tua |
| Priority 2 | 7–12 | 6 | Oranye |
| Priority 3 | 13–17 | 5 | Oranye muda |
| Insufficient data | – | 25 | Abu-abu |

`priority_order` sama dengan `ranking` (kosong untuk 25 kecamatan lain). Labelnya sengaja *Priority 1/2/3*, bukan Tinggi/Sedang/Rendah, supaya tidak tertukar dengan kelas **urgensi** keluhan. Kecamatan abu-abu tidak berarti jalannya baik: keluhannya terlalu sedikit untuk diurutkan dengan andal. Label poligon pada peta prioritas menampilkan nomor ranking. Proyek QGIS secara default mengaktifkan layer **Repair priority** saja agar tidak tertutup layer Gi*.

> Versi sebelumnya membagi **seluruh 42** kecamatan menjadi Tinggi/Sedang/Rendah (14/14/14). Itu diganti karena (a) 25 kecamatan dengan < 5 kejadian ikut diberi kelas padahal metode menyatakan datanya tidak cukup, dan (b) labelnya bentrok dengan kelas urgensi. Aturan di atas dipakai di `src/spatial/kecamatan_hotspot_analysis.py` (`assign_priority`) maupun `src/spatial/peta_hotspot.py`.

## Sumber, validasi, dan geometri

- Input: `reports/gis/kecamatan_hotspot_input.geojson`, 42 fitur, CRS84 dibaca sebagai EPSG:4326.
- Tabel: `reports/tables/ranking_kecamatan.csv`, 42 ID unik `pcode_kecamatan`.
- Referensi batas: `data/external/batas-wilayah/jakarta_adm3.geojson`; geometri asli cocok secara topologis untuk setiap ID. Ini pemeriksaan konsistensi repository, bukan verifikasi survei independen.
- Provenans: BPS / OCHA HDX, batas valid 2020-04-01; penduduk estimasi 2025. Rincian sumber dalam `data/external/README.md`.

Validasi memeriksa ID duplikat, kesamaan himpunan ID, kode daratan `ID3171`–`ID3175`, nama kecamatan, populasi positif, hitungan integer nonnegatif, jumlah kejadian = jumlah tiga kelas urgensi, `n_tweet >= n_kejadian`, perhitungan ulang laju dua desimal, eligibility dan urutan ranking asli. Kepulauan Seribu tidak termasuk.

Seluruh atribut numerik GeoJSON cocok dengan CSV. Perbedaan nama kota hanya awalan `Kota ` pada CSV. **Tidak perlu join ulang.** Ranking CSV digunakan setelah kesamaan ID dan urutannya terverifikasi. Kolom dengan null hanya ranking asli (25 null, sesuai eligibility).

Cilandak, Pancoran, dan Tebet mempunyai self-intersection. `shapely.make_valid` memperbaiki **salinan keluaran** sebelum proyeksi; perubahan luas absolut di bawah 0,000001 m². Semua output wajib valid, nonempty, dan bertipe poligon. Sumber asli tidak ditulis ulang. GeoPackage/proyek menggunakan **EPSG:32748 (WGS 84 / UTM zone 48S)**, satuan meter; ekspor GeoJSON menggunakan EPSG:4326.

Ada 188 kejadian, 42 observasi, enam wilayah bernilai nol, 14 nilai hitungan unik dan 33 nilai laju kejadian unik. Laju kejadian berkisar 0–13,98 per 100.000, mean 2,30, skewness 2,36. Variasi mencukupi untuk menghitung Gi*, tetapi sedikitnya kejadian dan distribusi miring membatasi daya uji. `n_tweet` bukan input Gi*: satu kejadian dapat menghasilkan beberapa tweet.

Skema lengkap kedua input, SHA-256 sumber, versi paket, perbaikan, ringkasan tiap variabel, kelas prioritas dan daftar tetangga tersimpan dalam `validation_and_analysis.json`.

## Bobot dan perhitungan statistik

Queen orde 1 dibentuk dari poligon yang diperbaiki: wilayah bertetangga jika memiliki vertex/batas yang sama. Hasilnya **satu komponen, tanpa island**. Bobot biner 1 digunakan untuk ketiga variabel dengan urutan ID sama. Script memiliki fallback symmetric KNN k=4 dari centroid EPSG:32748 bila Queen terputus; fallback **tidak digunakan** pada data ini.

`kecamatan_queen_order1.gal` menyimpan graf contiguity tanpa self-link, yang dapat dibaca kembali dengan libpysal/GeoDa. `star=True` menambahkan focal observation dengan bobot 1. CSV bobot turut mengekspor self-link secara eksplisit. Jika fallback dipakai pada input lain, periksa `weights_method` dalam JSON: GAL berisi graf terpilih, bukan otomatis Queen.

```python
G_Local(y, W(neighbors, id_order=ids), transform='B', star=True,
        permutations=9999, seed=20261028, n_jobs=1,
        keep_simulations=True, alternative='two-sided')
```

Z analitik diverifikasi terhadap formula Gi* focal-inclusive:

```text
Z_i = (sum_j w_ij x_j - mean(x) sum_j w_ij)
      / [sd_population(x) sqrt((n sum_j w_ij² - (sum_j w_ij)²)/(n-1))]
```

Inferensi utama menggunakan `p_sim` dua sisi yang dihitung esda 2.10 secara eksplisit; focal value tetap pada permutasi kondisional. Implementasi menggunakan percentile observasi dan percentile komplemennya, menyertakan ties dan koreksi Monte Carlo. Jangan menggandakan lagi `p_sim` ini. Konvensi default versi esda lama berbeda.

BH dilakukan pada 42 p-value **per variabel**: kalikan p terurut dengan 42/rank, terapkan cumulative minimum dari akhir, dan batasi ke 1. q ≤ 0,05 menentukan signifikansi; q ≤ 0,01 kelas warna lebih kuat. BH bukan probabilitas bahwa setiap hotspot salah; jaminan FDR bergantung asumsi independensi/dependensi positif yang sesuai, sedangkan neighborhood saling tumpang tindih. Analisis ini eksploratif, dengan koreksi terpisah, bukan gabungan semua variabel.

Kolom `*_z` menyimpan Z analitik. `*_z_perm` memakai mean dan deviasi simulasi kondisional, dan tandanya menentukan arah hotspot/coldspot pada klasifikasi permutasi. Dua Z dapat berbeda karena null berbeda. `*_p_norm_2s` dan `*_q_norm_bh` disimpan terpisah. Peta utama menggunakan `*_p_perm_2s` yang telah dikoreksi menjadi `*_q_bh`, bukan Z threshold, count, ranking, atau label prioritas.

## Eksekusi ulang dan pemeriksaan

Script ada di `src/spatial/`. Analisis Gi* dan proyek QGIS harus dijalankan dengan **Python milik QGIS** (butuh `qgis.core`), bukan Python sistem. Dependensi statistik (`esda`, `libpysal`, versi dikunci di `src/spatial/requirements-hotspot.txt`) dipasang ke `.venv/hotspot` di dalam repo, bukan ke instalasi QGIS. Folder `.venv/` tidak di-commit.

**Windows** (QGIS standalone installer atau OSGeo4W), dari Command Prompt:

```bat
src\spatial\run_hotspot_windows.bat --install
src\spatial\run_hotspot_windows.bat
src\spatial\run_hotspot_windows.bat --verify
```

Launcher mencari `C:\Program Files\QGIS 3.*\bin\python-qgis.bat` (atau `python-qgis-ltr.bat`, atau `C:\OSGeo4W`). Jika QGIS ada di tempat lain, jalankan dulu `set "QGIS_ROOT=D:\path\ke\QGIS 3.xx"`. Jika muncul `ModuleNotFoundError` untuk paket selain esda/libpysal (mis. `geopandas`), pasang paket itu dengan `"%QGIS_ROOT%\bin\python-qgis.bat" -m pip install --target .venv\hotspot <paket>`. Launcher Windows belum dites di semua versi QGIS; analisis asli dijalankan di macOS.

**macOS**:

```bash
PYTHONHOME=/Applications/QGIS.app/Contents/Frameworks \
  /Applications/QGIS.app/Contents/MacOS/python3.12 -m pip install \
  --target .venv/hotspot --no-deps -r src/spatial/requirements-hotspot.txt
bash src/spatial/run_hotspot_macos.sh
bash src/spatial/run_hotspot_macos.sh --verify
```

QGIS macOS menyediakan GeoPandas, NumPy, SciPy, pandas, Shapely, PyProj, scikit-learn, dan Numba. Versi aktual direkam dalam JSON. Launcher mengatur `PYTHONHOME`, QGIS `PYTHONPATH`, `PROJ_DATA`, `GDAL_DATA`, Qt offscreen dan cache Numba lokal. `QGIS_APP` dapat diset jika aplikasi ada di lokasi lain; nama executable perlu disesuaikan jika QGIS memakai versi Python berbeda.

**Alternatif: QGIS Python Console** (semua OS). Ganti path dengan lokasi repo di komputer masing-masing:

```python
from pathlib import Path
script = Path(r'D:\Project\ISYS8036042-AOL-Group-9\src\spatial\kecamatan_hotspot_analysis.py')
namespace = {'__file__': str(script), '__name__': '__main__'}
exec(compile(script.read_text(), str(script), 'exec'), namespace)
```

Console akan membersihkan proyek in-memory; simpan pekerjaan lain dahulu. Launcher terminal memakai proses terpisah. Output digenerasi ulang, input tidak diubah. GeoPackage baru ditulis ke file sementara lalu diganti agar tidak mengedit database yang sedang dibaca desktop; buka ulang proyek di QGIS setelah regenerasi agar membaca data dan style terbaru.

Buka `reports/gis/outputs/kecamatan_hotspot_project.qgz`; default canvas menampilkan prioritas. Melalui **Project → Layouts**, pilih **Repair priority**, **Gi\* all-incident rate**, **Gi\* high-urgency incident rate**, atau **Gi\* incident count (sensitivity)**. Layout mengunci daftar layer masing-masing sehingga tampilannya tidak bergantung pada layer canvas yang dicentang.

## Keluaran

Script (`src/spatial/`):

| File | Isi |
|---|---|
| `kecamatan_hotspot_analysis.py` | Validasi, label prioritas, statistik Gi*, proyek dan ekspor QGIS (Python QGIS) |
| `verify_hotspot_outputs.py` | Pemeriksaan output + hitung ulang statistik (Python QGIS) |
| `run_hotspot_windows.bat`, `run_hotspot_macos.sh` | Launcher Python QGIS |
| `requirements-hotspot.txt` | Versi esda/libpysal yang dikunci |
| `peta_hotspot.py` | Peta & tabel untuk paper dari CSV statistik (Python biasa, tanpa QGIS) |

Hasil QGIS, semua di `reports/gis/outputs/`:

| File | Isi |
|---|---|
| `kecamatan_hotspot_results.gpkg` | Layer `kecamatan_hotspot`, 42 poligon, atribut asal dan ketiga analisis |
| `kecamatan_hotspot_statistics.csv` | Atribut, label akhir, Gi*, Z, p, q, flag dan kelas statistik |
| `kecamatan_priority_labels.csv` | Kelas prioritas, ranking dan eligibility seluruh kecamatan |
| `kecamatan_hotspot_project.qgz` | Satu-satunya file proyek QGIS: empat layer, empat layout, path GeoPackage relatif; default hanya prioritas aktif |
| `kecamatan_priority_map.png` | Priority 1/2/3 + Insufficient data |
| `kecamatan_gistar_hotspot_map.png` | Gi* laju semua kejadian |
| `kecamatan_gistar_tinggi_map.png` | Gi* laju urgensi tinggi |
| `kecamatan_gistar_count_map.png` | Gi* jumlah kejadian, sensitivitas tambahan |
| `hasil_gistar_kejadian.geojson` | ID, prioritas dan statistik laju kejadian, EPSG:4326 |
| `hasil_gistar_tinggi.geojson` | ID, prioritas dan statistik laju urgensi tinggi, EPSG:4326 |
| `kecamatan_queen_order1.gal` | Graf bobot terpilih tanpa self-link |
| `spatial_weights.csv` | Tetangga biner termasuk focal link, berdasarkan ID |
| `sensitivity_raw_comparison.csv` | Crosstab laju kejadian vs jumlah absolut sebelum FDR |
| `validation_and_analysis.json` | Audit sumber, geometri, metode, kelas dan hasil |

Prefix statistik: `rate_` = laju kejadian, `high_` = laju urgensi tinggi, `count_` = jumlah kejadian. `*_significant` = 1 hanya untuk q ≤ 0,05; `*_raw_class` memakai p belum dikoreksi. `neighbor_count` tidak menyertakan self. PNG A4 landscape 220 dpi (2572 × 1818), dengan judul, legenda, batas kecamatan, north arrow, skala kilometer dan sumber.

## Keterbatasan dan referensi

Keluhan media sosial bukan sampel acak: akses internet, perilaku posting, ketelitian lokasi, deduplikasi, filter dan kesalahan model memengaruhi nilai. Sedikit keluhan dapat berarti underreporting. Validasi ini memeriksa agregat yang diberikan, bukan anotasi tweet privat atau semua geocoding. Batas 2020, MAUP, pilihan Queen dan null permutasi juga memengaruhi kesimpulan.

Populasi adalah estimasi proporsi WNI terdaftar 2017 yang diskalakan ke total kota 2025. Repository mencatat total kota diambil dari kutipan media dan belum dicek langsung terhadap BPS. Perbedaan registrasi/residensi, commuting dan paparan jalan membatasi makna laju per penduduk. Nilai dua desimal input dipertahankan. Tidak lolos FDR bukan bukti tidak ada masalah infrastruktur.

Referensi: [esda G_Local](https://pysal.org/esda/stable/generated/esda.G_Local.html), [implementasi signifikansi esda](https://github.com/pysal/esda/blob/main/esda/significance.py), [libpysal Queen](https://pysal.org/libpysal/generated/libpysal.weights.Queen.html), [GeoDa local G*](https://geodacenter.github.io/pygeoda/generated/pygeoda.local_gstar.html), [HDX Indonesia boundaries](https://data.humdata.org/dataset/indonesia-administrative-boundary-polygons-lines-and-places-levels-0-4b).
