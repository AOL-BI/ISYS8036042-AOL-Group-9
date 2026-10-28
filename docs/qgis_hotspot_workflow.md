# QGIS: tiga kelas prioritas dan Getis-Ord Gi* DKI Jakarta

## Hasil dan pengaturan terbaru

Permintaan terbaru menggunakan **seluruh 42 kecamatan** untuk label akhir prioritas **Rendah, Sedang, Tinggi**. Kolom `priority_label` berisi tepat tiga nilai tersebut, masing-masing 14 kecamatan. Ini kelas prioritas relatif, bukan kategori signifikansi statistik.

Analisis Gi* mengikuti parameter pada lampiran: ID `pcode`, **Queen contiguity orde 1**, focal observation disertakan (Gi*, bukan Gi), **9999 permutasi**, FDR **0,05**, dan dua variabel utama `per100rb_kejadian` serta `per100rb_tinggi`. Analisis tambahan `n_kejadian` tetap tersedia sebagai sensitivitas terhadap jumlah absolut. Setiap variabel diuji dan dikoreksi tersendiri.

Eksekusi memakai Python bawaan QGIS 3.44.14, PyQGIS untuk proyek/layout, serta esda 2.10.0 dan libpysal 4.15.1 untuk statistik. **Tidak ada eksekusi GeoDa yang diklaim.** Parameter yang diminta disamakan, tetapi nilai numerik tidak dijamin identik dengan GeoDa: seed, generator random, dan konvensi ekor uji dapat berbeda. Implementasi di sini secara eksplisit memakai uji permutasi kondisional **dua sisi** dan BH FDR. Jika Bab 3 menyebut perangkat lunak, tuliskan implementasi PySAL/PyQGIS ini; jangan menyebut hasil sebagai keluaran GeoDa tanpa menjalankannya di sana.

| Variabel | Jumlah p ≤ 0,05 sebelum FDR | Jumlah q ≤ 0,05 | p minimum | q minimum |
|---|---:|---:|---:|---:|
| `per100rb_kejadian` | 4 | 0 | 0,0025 | 0,1050 |
| `per100rb_tinggi` | 4 | 0 | 0,0132 | 0,4095 |
| `n_kejadian` (tambahan) | 2 | 0 | 0,0134 | 0,5628 |

**Tidak ada hotspot atau coldspot signifikan setelah FDR** pada ketiga variabel. Peta prioritas tetap berwarna karena memakai pembagian relatif, bukan hasil uji Gi*. Seluruh poligon Gi* berwarna abu-abu sesuai hasil statistik.

Sebelum koreksi, hasil eksploratif laju kejadian menandai Tebet, Tanah Abang, Menteng sebagai hotspot dan Pademangan sebagai coldspot. Laju urgensi tinggi menandai Kebayoran Baru, Tebet, Menteng sebagai hotspot dan Taman Sari sebagai coldspot. Jumlah absolut menandai Kebayoran Baru sebagai hotspot dan Pademangan sebagai coldspot. Temuan ini **tidak lolos FDR** dan tidak boleh disebut hotspot terkonfirmasi.

## Aturan tiga kelas prioritas

Urutkan semua kecamatan secara leksikografis:

1. `per100rb_tinggi` menurun.
2. Jika sama, `per100rb_sedang` menurun.
3. Jika masih sama, `per100rb_rendah` menurun.
4. Jika ketiga laju sama, `pcode` menaik sebagai pemutus seri yang deterministik.

| Label akhir (`priority_label`) | Urutan baru (`priority_order`) | Jumlah | Warna |
|---|---|---:|---|
| Tinggi | 1–14 | 14 | Merah tua |
| Sedang | 15–28 | 14 | Merah muda |
| Rendah | 29–42 | 14 | Merah sangat muda |

Ini pembagian tiga kelompok berukuran sama berdasarkan **urutan**, bukan interval nilai sama, weighted score, atau aturan dari signifikansi Gi*. Pada data sekarang tidak ada seri nilai di batas antarkelompok. Dengan definisi relatif ini, 14 wilayah selalu masuk Tinggi walaupun seluruh tingkat keluhan rendah. Prioritas Rendah tidak berarti tidak membutuhkan perbaikan.

Kolom asli `ranking` dan `data_cukup` **dipertahankan**. Script upstream `src/modeling/prediksi_final.py` hanya memberi ranking pada kecamatan dengan `n_kejadian >= 5`, sehingga 17 wilayah beranking dan 25 null. Atas pilihan pengguna, kelas baru mencakup 25 wilayah tersebut juga; `priority_order` 1–42 berbeda dari ranking asli 1–17. Metode pengurutan urgensi tetap sama. Kelas untuk wilayah berdatum sedikit harus ditafsirkan hati-hati.

Label poligon dan legenda prioritas hanya menampilkan Rendah, Sedang, Tinggi. Proyek secara default mengaktifkan layer **Prioritas perbaikan** saja agar tidak tertutup layer Gi*. Layer statistik dan layout terpisah tetap tersedia.

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

Dari root repository, gunakan Python milik QGIS, bukan Python sistem:

```bash
PYTHONHOME=/Applications/QGIS.app/Contents/Frameworks \
  /Applications/QGIS.app/Contents/MacOS/python3.12 -m pip install \
  --target .venv/hotspot --no-deps -r reports/gis/requirements-hotspot.txt
bash reports/gis/run_hotspot_macos.sh
bash reports/gis/run_hotspot_macos.sh --verify
```

QGIS yang terpasang menyediakan GeoPandas, NumPy, SciPy, pandas, Shapely, PyProj, scikit-learn, dan Numba. Versi aktual direkam dalam JSON; distribusi lain mungkin memerlukan dependensi tambahan. Launcher mengatur `PYTHONHOME`, QGIS `PYTHONPATH`, `PROJ_DATA`, `GDAL_DATA`, Qt offscreen dan cache Numba lokal. `QGIS_APP` dapat diset jika aplikasi ada di lokasi lain; nama executable perlu disesuaikan jika QGIS memakai versi Python berbeda.

Alternatif di QGIS Python Console:

```python
from pathlib import Path
script = Path('/Users/aengelinaa/Documents/AOL-BIA/ISYS8036042-AOL-Group-9/reports/gis/outputs/kecamatan_hotspot_analysis.py')
namespace = {'__file__': str(script), '__name__': '__main__'}
exec(compile(script.read_text(), str(script), 'exec'), namespace)
```

Console akan membersihkan proyek in-memory; simpan pekerjaan lain dahulu. Launcher terminal memakai proses terpisah. Output digenerasi ulang, input tidak diubah. GeoPackage baru ditulis ke file sementara lalu diganti agar tidak mengedit database yang sedang dibaca desktop; buka ulang proyek di QGIS setelah regenerasi agar membaca data dan style terbaru.

Buka `kecamatan_hotspot_project.qgz`; default canvas menampilkan prioritas. Melalui **Project → Layouts**, pilih **Prioritas perbaikan**, **Gi* laju kejadian**, **Gi* laju urgensi tinggi**, atau **Incident count sensitivity**. Layout mengunci daftar layer masing-masing sehingga tampilannya tidak bergantung pada layer canvas yang dicentang.

## Keluaran

Semua berlokasi di `reports/gis/outputs/`:

| File | Isi |
|---|---|
| `kecamatan_hotspot_analysis.py` | Validasi, label prioritas, statistik, proyek dan ekspor |
| `kecamatan_hotspot_results.gpkg` | Layer `kecamatan_hotspot`, 42 poligon, atribut asal dan ketiga analisis |
| `kecamatan_hotspot_statistics.csv` | Atribut, label akhir, Gi*, Z, p, q, flag dan kelas statistik |
| `kecamatan_priority_labels.csv` | Label final dan urutan seluruh kecamatan, ranking serta eligibility asli |
| `kecamatan_hotspot_project.qgz` | Empat layer, empat layout, path GeoPackage relatif; default hanya prioritas aktif |
| `kecamatan_priority_map.png` | Tiga kelas prioritas: Rendah, Sedang, Tinggi |
| `kecamatan_gistar_hotspot_map.png` | Gi* laju kejadian |
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
