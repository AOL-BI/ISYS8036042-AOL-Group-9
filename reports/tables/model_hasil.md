# Hasil Eksperimen Model

Test set: 154 baris (keluhan menurut label final: 81). Data latih baru: 210 baris + review 78 baris.

## R. Filter relevansi (keluhan vs bukan)

Latih: 288 baris (56% keluhan). Uji: 154 baris.

| model | fitur | cv_macro_f1 | akurasi | macro_f1 | ci95 | precision_keluhan | recall_keluhan |
|---|---|---|---|---|---|---|---|
| Baseline: semua dianggap keluhan (pipeline sekarang) | - | nan | 0.526 | 0.345 | 0.31–0.38 | 0.526 | 1.000 |
| Baseline: keluhan jika lokasi DKI ditemukan | - | nan | 0.721 | 0.704 | 0.63–0.78 | 0.673 | 0.914 |
| Random Forest | teks | 0.768 | 0.760 | 0.759 | 0.69–0.82 | 0.768 | 0.778 |
| SVM (linear) | teks | 0.814 | 0.753 | 0.750 | 0.67–0.82 | 0.736 | 0.827 |
| Gradient-Boosted Trees | teks | 0.718 | 0.688 | 0.686 | 0.61–0.75 | 0.690 | 0.741 |
| Naive Bayes | teks | 0.784 | 0.740 | 0.739 | 0.67–0.81 | 0.741 | 0.778 |
| Random Forest | teks + meta | 0.799 | 0.734 | 0.728 | 0.65–0.80 | 0.708 | 0.840 |
| SVM (linear) | teks + meta | 0.815 | 0.708 | 0.699 | 0.62–0.77 | 0.680 | 0.840 |
| Gradient-Boosted Trees | teks + meta | 0.762 | 0.714 | 0.709 | 0.64–0.78 | 0.699 | 0.802 |
| Naive Bayes | teks + meta | 0.758 | 0.727 | 0.719 | 0.65–0.79 | 0.697 | 0.852 |

## U. Urgensi (3 kelas)

Uji: 81 keluhan (Tinggi 24, Sedang 50, Rendah 7). Label latih baru: 119 keluhan (Tinggi 21, Sedang 64, Rendah 34).

| model | data latih | n_latih | cv_macro_f1 | akurasi | macro_f1 | ci95 | f1_Tinggi | f1_Sedang | f1_Rendah |
|---|---|---|---|---|---|---|---|---|---|
| Baseline: label aturan (kosong = salah) | - | 0 | nan | 0.481 | 0.375 | 0.30–0.45 | 0.600 | 0.525 | 0.000 |
| Baseline: label aturan (kosong = Sedang) | - | 0 | nan | 0.605 | 0.422 | 0.34–0.49 | 0.600 | 0.667 | 0.000 |
| Baseline: selalu Sedang | - | 0 | nan | 0.617 | 0.254 | 0.22–0.28 | 0.000 | 0.763 | 0.000 |
| Random Forest | baru | 119 | 0.538 | 0.519 | 0.465 | 0.35–0.58 | 0.500 | 0.598 | 0.296 |
| SVM (linear) | baru | 119 | 0.549 | 0.543 | 0.470 | 0.35–0.58 | 0.476 | 0.667 | 0.267 |
| Gradient-Boosted Trees | baru | 119 | 0.576 | 0.593 | 0.528 | 0.41–0.64 | 0.622 | 0.667 | 0.296 |
| Naive Bayes | baru | 119 | 0.642 | 0.531 | 0.465 | 0.35–0.57 | 0.468 | 0.659 | 0.267 |
| Random Forest | baru + manual lama | 303 | 0.622 | 0.506 | 0.372 | 0.29–0.45 | 0.478 | 0.638 | 0.000 |
| SVM (linear) | baru + manual lama | 303 | 0.618 | 0.481 | 0.408 | 0.30–0.51 | 0.500 | 0.581 | 0.143 |
| Gradient-Boosted Trees | baru + manual lama | 303 | 0.625 | 0.494 | 0.394 | 0.30–0.49 | 0.490 | 0.614 | 0.080 |
| Naive Bayes | baru + manual lama | 303 | 0.570 | 0.531 | 0.470 | 0.36–0.57 | 0.500 | 0.659 | 0.250 |
| Random Forest | aturan + manual lama (cara lama) | 477 | 0.715 | 0.556 | 0.370 | 0.29–0.44 | 0.444 | 0.667 | 0.000 |
| SVM (linear) | aturan + manual lama (cara lama) | 477 | 0.721 | 0.543 | 0.368 | 0.29–0.44 | 0.464 | 0.639 | 0.000 |
| Gradient-Boosted Trees | aturan + manual lama (cara lama) | 477 | 0.747 | 0.556 | 0.380 | 0.30–0.45 | 0.500 | 0.639 | 0.000 |
| Naive Bayes | aturan + manual lama (cara lama) | 477 | 0.669 | 0.494 | 0.389 | 0.28–0.50 | 0.464 | 0.578 | 0.125 |

## U2. Urgensi biner (Tinggi vs Bukan Tinggi)

| model | data latih | akurasi | macro_f1 | ci95 | f1_Tinggi |
|---|---|---|---|---|---|
| Baseline: label aturan | - | 0.704 | 0.682 | 0.57–0.79 | 0.600 |
| Random Forest | baru | 0.728 | 0.622 | 0.50–0.74 | 0.421 |
| SVM (linear) | baru | 0.728 | 0.646 | 0.52–0.76 | 0.476 |
| Gradient-Boosted Trees | baru | 0.765 | 0.699 | 0.58–0.81 | 0.558 |
| Naive Bayes | baru | 0.716 | 0.678 | 0.56–0.78 | 0.566 |
| Random Forest | baru + manual lama | 0.753 | 0.679 | 0.55–0.79 | 0.524 |
| SVM (linear) | baru + manual lama | 0.753 | 0.688 | 0.56–0.79 | 0.545 |
| Gradient-Boosted Trees | baru + manual lama | 0.778 | 0.701 | 0.57–0.81 | 0.550 |
| Naive Bayes | baru + manual lama | 0.753 | 0.704 | 0.59–0.81 | 0.583 |
| Random Forest | aturan + manual lama (cara lama) | 0.605 | 0.556 | 0.43–0.66 | 0.407 |
| SVM (linear) | aturan + manual lama (cara lama) | 0.617 | 0.573 | 0.45–0.68 | 0.436 |
| Gradient-Boosted Trees | aturan + manual lama (cara lama) | 0.642 | 0.601 | 0.48–0.70 | 0.473 |
| Naive Bayes | aturan + manual lama (cara lama) | 0.593 | 0.553 | 0.43–0.66 | 0.421 |

Confusion matrix model terpilih dari data latih baru (CV tertinggi: Naive Bayes), baris = label final:

| final | Tinggi | Sedang | Rendah |
|---|---|---|---|
| Tinggi | 11 | 5 | 8 |
| Sedang | 11 | 28 | 11 |
| Rendah | 1 | 2 | 4 |
