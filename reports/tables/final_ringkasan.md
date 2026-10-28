# Ringkasan Hasil Final (model: Random Forest)

## Dari keluhan pipeline ke keluhan relevan

| Tahap | Jumlah |
|---|---|
| Keluhan hasil pipeline | 807 |
| Relevan (keluhan jalan rusak) | 408 |
|   - dari label manusia | 242 |
|   - dari prediksi model | 166 |
| Relevan dengan lokasi sampai kecamatan | 325 |
| Relevan tanpa kecamatan (hanya kota / tanpa lokasi) | 83 |
| Kejadian (tweet sekecamatan dengan jeda <= 7 hari digabung) | 188 |

Kategori final menurut sumber label:

| kategori_final | latih | model | review | test_set |
|---|---|---|---|---|
| berita_umum | 45 | 0 | 19 | 16 |
| bukan_jalan_rusak | 34 | 0 | 2 | 43 |
| bukan_keluhan | 0 | 199 | 0 | 0 |
| keluhan | 119 | 166 | 42 | 81 |
| laporan_perbaikan | 12 | 0 | 15 | 14 |

## Distribusi urgensi keluhan relevan

| urgensi_final | latih | model | test_set | Total |
|---|---|---|---|---|
| Tinggi | 21 | 47 | 24 | 92 |
| Sedang | 64 | 124 | 50 | 238 |
| Rendah | 34 | 37 | 7 | 78 |
| Total | 119 | 208 | 81 | 408 |

Urgensi per kejadian (urgensi tertinggi di dalam kejadian):

| urgensi | kejadian |
|---|---|
| Tinggi | 48 |
| Sedang | 109 |
| Rendah | 31 |

Kejadian dengan tweet terbanyak:

| kecamatan | mulai | n_tweet | urgensi |
|---|---|---|---|
| Jagakarsa | 2026-05-29 08:29:22 | 31 | Tinggi |
| Matraman | 2026-02-09 09:05:00 | 13 | Tinggi |
| Cilandak | 2023-02-27 10:30:29 | 10 | Tinggi |
| Cilandak | 2022-10-15 20:23:23 | 9 | Tinggi |
| Pulo Gadung | 2026-07-06 13:06:14 | 6 | Tinggi |

## Ranking kecamatan (laju kejadian per 100 ribu penduduk; data cukup = minimal 5 kejadian)

Kecamatan dengan data cukup: 17 dari 42.

| ranking | kecamatan | kota | n_tweet | n_kejadian | n_tinggi | n_sedang | n_rendah | per100rb_tinggi | per100rb_sedang | per100rb_rendah |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Setia Budi | Kota Jakarta Selatan | 32 | 16 | 4 | 11 | 1 | 3.49 | 9.61 | 0.87 |
| 2 | Matraman | Kota Jakarta Timur | 21 | 7 | 4 | 3 | 0 | 2.10 | 1.57 | 0.00 |
| 3 | Kelapa Gading | Kota Jakarta Utara | 21 | 13 | 2 | 7 | 4 | 1.39 | 4.85 | 2.77 |
| 4 | Pulo Gadung | Kota Jakarta Timur | 15 | 8 | 4 | 3 | 1 | 1.31 | 0.98 | 0.33 |
| 5 | Kebayoran Lama | Kota Jakarta Selatan | 8 | 8 | 4 | 4 | 0 | 1.29 | 1.29 | 0.00 |
| 6 | Grogol Petamburan | Kota Jakarta Barat | 16 | 14 | 3 | 10 | 1 | 1.25 | 4.18 | 0.42 |
| 7 | Cilandak | Kota Jakarta Selatan | 30 | 10 | 2 | 3 | 5 | 0.95 | 1.42 | 2.37 |
| 8 | Senen | Kota Jakarta Pusat | 8 | 5 | 1 | 3 | 1 | 0.85 | 2.56 | 0.85 |
| 9 | Cilincing | Kota Jakarta Utara | 11 | 9 | 3 | 4 | 2 | 0.70 | 0.94 | 0.47 |
| 10 | Jatinegara | Kota Jakarta Timur | 6 | 6 | 2 | 2 | 2 | 0.62 | 0.62 | 0.62 |
| 11 | Tanah Abang | Kota Jakarta Pusat | 6 | 5 | 1 | 3 | 1 | 0.61 | 1.83 | 0.61 |
| 12 | Cakung | Kota Jakarta Timur | 16 | 8 | 3 | 4 | 1 | 0.56 | 0.75 | 0.19 |
| 13 | Kramat Jati | Kota Jakarta Timur | 6 | 6 | 1 | 5 | 0 | 0.33 | 1.65 | 0.00 |
| 14 | Jagakarsa | Kota Jakarta Selatan | 37 | 6 | 1 | 3 | 2 | 0.31 | 0.92 | 0.62 |
| 15 | Cengkareng | Kota Jakarta Barat | 11 | 6 | 1 | 4 | 1 | 0.18 | 0.73 | 0.18 |
| 16 | Gambir | Kota Jakarta Pusat | 9 | 9 | 0 | 6 | 3 | 0.00 | 6.47 | 3.23 |
| 17 | Pademangan | Kota Jakarta Utara | 8 | 5 | 0 | 4 | 1 | 0.00 | 2.34 | 0.59 |

Kecamatan dengan data tidak cukup (jumlah kejadian): Pasar Minggu (4), Pancoran (4), Tebet (4), Pasar Rebo (4), Duren Sawit (4), Menteng (4), Kebayoran Baru (3), Palmerah (3), Mampang Prapatan (2), Ciracas (2), Makasar (2), Kebon Jeruk (2), Taman Sari (2), Tanjung Priok (2), Johar Baru (1), Kemayoran (1), Kembangan (1), Tambora (1), Penjaringan (1), Pesanggrahan (0), Cipayung (0), Cempaka Putih (0), Sawah Besar (0), Kali Deres (0), Koja (0)
