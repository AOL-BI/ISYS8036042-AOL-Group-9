# Perbandingan Model

## A. Kinerja di test set (label latih pedoman baru, fitur teks)

| model | relevansi macro-F1 | relevansi CI95 | presisi keluhan | urgensi macro-F1 | urgensi CI95 | F1 Tinggi | F1 Sedang | F1 Rendah |
|---|---|---|---|---|---|---|---|---|
| RF | 0.759 | 0.69–0.82 | 0.768 | 0.465 | 0.35–0.58 | 0.500 | 0.598 | 0.296 |
| SVM | 0.750 | 0.67–0.82 | 0.736 | 0.470 | 0.35–0.58 | 0.476 | 0.667 | 0.267 |
| GBT | 0.686 | 0.61–0.75 | 0.690 | 0.528 | 0.41–0.64 | 0.622 | 0.667 | 0.296 |
| NB | 0.739 | 0.67–0.81 | 0.741 | 0.465 | 0.35–0.57 | 0.468 | 0.659 | 0.267 |

Sumber: `model_relevansi.csv` & `model_urgensi.csv` (src/modeling/eksperimen_model.py).

## B. Dampak ke hasil akhir (semua keluhan pipeline)

Baris berlabel manusia memakai label manusia di semua model, jadi perbedaan hanya berasal dari baris yang diprediksi model.

| model | keluhan relevan |   dari prediksi model | kejadian | kejadian Tinggi | kejadian Sedang | kejadian Rendah | kecamatan data cukup | Top-5 |
|---|---|---|---|---|---|---|---|---|
| RF | 408 | 166 | 188 | 48 | 109 | 31 | 17 | Setia Budi, Matraman, Kelapa Gading, Pulo Gadung, Kebayoran Lama |
| SVM | 436 | 194 | 201 | 43 | 122 | 36 | 18 | Matraman, Setia Budi, Kelapa Gading, Kebayoran Lama, Grogol Petamburan |
| GBT | 426 | 184 | 195 | 58 | 101 | 36 | 18 | Setia Budi, Matraman, Grogol Petamburan, Kelapa Gading, Pulo Gadung |
| NB | 427 | 185 | 199 | 48 | 114 | 37 | 18 | Matraman, Grogol Petamburan, Setia Budi, Kelapa Gading, Pulo Gadung |

## C. Kemiripan ranking kecamatan dengan model utama (RF)

Spearman dihitung pada kecamatan yang masuk ranking di kedua model (data cukup).

| model | kecamatan dibandingkan | Spearman vs RF | irisan Top-5 | irisan Top-10 |
|---|---|---|---|---|
| SVM | 17 | 0.990 | 4/5 | 10/10 |
| GBT | 17 | 0.934 | 4/5 | 9/10 |
| NB | 17 | 0.946 | 4/5 | 9/10 |

Ranking lengkap berdampingan: `reports/tables/perbandingan_ranking.csv`.
