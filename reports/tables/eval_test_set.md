# Evaluasi Test Set (FINAL)

Test set: 154 keluhan hasil pipeline, sampel acak Slovin e=7% berstrata tipe akun, dilabeli buta oleh 2 anotator mengikuti `docs/pedoman-anotasi-urgensi.md`.

## 1. Kesepakatan antar-anotator

| Aspek | n | Sepakat | Sepakat % | Cohen's κ | Tafsir (Landis & Koch) | Weighted κ (linear) |
|---|---|---|---|---|---|---|
| Kategori (4 kelas) | 154 | 107 | 69.5 | 0.528 | sedang |  |
| Urgensi (3 kelas, baris yang sama-sama keluhan) | 64 | 42 | 65.6 | 0.378 | lemah | 0.364 |
| Kategori + urgensi (gabungan) | 154 | 85 | 55.2 | 0.442 | sedang |  |

Confusion kategori (baris = A, kolom = B):

| A \ B | keluhan | laporan_perbaikan | berita_umum | bukan_jalan_rusak |
|---|---|---|---|---|
| keluhan | 64 | 3 | 6 | 5 |
| laporan_perbaikan | 5 | 12 | 5 | 1 |
| berita_umum | 5 | 1 | 7 | 4 |
| bukan_jalan_rusak | 8 | 1 | 3 | 24 |

Confusion urgensi, baris yang sama-sama keluhan (baris = A, kolom = B):

| A \ B | Tinggi | Sedang | Rendah |
|---|---|---|---|
| Tinggi | 13 | 5 | 1 |
| Sedang | 10 | 27 | 1 |
| Rendah | 2 | 3 | 2 |

Baris berbeda (perlu diskusi): **69**, sudah diputuskan: 69. Daftar: `data/processed/anotasi/perlu_diskusi.csv`.

## 2. Presisi filter keluhan pipeline

Dari 154 baris berlabel final, **81 (53%) memang keluhan**.

| Kategori final | Jumlah | % |
|---|---|---|
| keluhan | 81 | 53% |
| laporan_perbaikan | 14 | 9% |
| berita_umum | 16 | 10% |
| bukan_jalan_rusak | 43 | 28% |

Menurut `status_wilayah` pipeline:

| status_wilayah | keluhan | laporan_perbaikan | berita_umum | bukan_jalan_rusak | % keluhan |
|---|---|---|---|---|---|
| dki | 74 | 13 | 7 | 16 | 67% |
| jakarta_umum | 7 | 1 | 9 | 27 | 16% |

Menurut `tipe_akun`:

| tipe_akun | keluhan | laporan_perbaikan | berita_umum | bukan_jalan_rusak | % keluhan |
|---|---|---|---|---|---|
| media_resmi | 50 | 10 | 14 | 9 | 60% |
| warga | 31 | 4 | 2 | 34 | 44% |

## 3. Label aturan vs label final (hanya keluhan)

- n = 81 keluhan; label aturan kosong (tidak ada kata penanda): 13
- Akurasi (label kosong dihitung salah): **48.1%**
- Akurasi pada baris yang punya label aturan: 57.4%
- Macro-F1: **0.375**

| Kelas | Support | Precision | Recall | F1 |
|---|---|---|---|---|
| Tinggi | 24 | 0.5 | 0.75 | 0.6 |
| Sedang | 50 | 0.7 | 0.42 | 0.525 |
| Rendah | 7 | 0.0 | 0.0 | 0.0 |

Confusion (baris = label final, kolom = label aturan):

| Final \ Aturan | Tinggi | Sedang | Rendah | (tanpa label) |
|---|---|---|---|---|
| Tinggi | 18 | 5 | 0 | 1 |
| Sedang | 17 | 21 | 2 | 10 |
| Rendah | 1 | 4 | 0 | 2 |
