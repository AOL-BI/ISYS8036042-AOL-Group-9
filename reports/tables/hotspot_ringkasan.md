# Ringkasan Hotspot (Getis-Ord Gi*) & Prioritas

Dibuat oleh `src/spatial/peta_hotspot.py` dari `reports/gis/outputs/kecamatan_hotspot_statistics.csv`.

## Gi* per variabel

| variable | p ≤ 0.05 (before FDR) | q ≤ 0.05 (after FDR) | min p | min q | exploratory high clusters (z > 0, p ≤ 0.05) | exploratory low clusters (z < 0, p ≤ 0.05) |
|---|---|---|---|---|---|---|
| All incidents per 100,000 residents | 4 | 0 | 0.0025 | 0.1050 | Menteng, Tanah Abang, Tebet | Pademangan |
| High-urgency incidents per 100,000 residents | 4 | 0 | 0.0132 | 0.4095 | Menteng, Tebet, Kebayoran Baru | Taman Sari |
| Incident count (sensitivity) | 2 | 0 | 0.0134 | 0.5628 | Kebayoran Baru | Pademangan |

Tidak ada kecamatan yang signifikan setelah koreksi FDR. Kecamatan dengan p ≤ 0,05 sebelum koreksi hanya dilaporkan sebagai temuan eksploratif.

## Kelas prioritas

Hanya kecamatan dengan ≥ 5 kejadian yang diberi kelas; urutan dari `ranking` (laju Tinggi → Sedang → Rendah per 100.000 penduduk).

Priority 1: ranking 1–6, Priority 2: ranking 7–12, Priority 3: ranking 13–17; Insufficient data: 25 kecamatan.

| ranking | priority_label | kecamatan | n_kejadian | per100rb_tinggi | per100rb_kejadian | rate_z | rate_q_bh | high_z | high_q_bh |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Priority 1 | Setia Budi | 16 | 3.490 | 13.980 | 1.893 | 0.871 | 1.186 | 0.917 |
| 2 | Priority 1 | Matraman | 7 | 2.100 | 3.670 | 0.400 | 0.914 | 1.261 | 0.906 |
| 3 | Priority 1 | Kelapa Gading | 13 | 1.390 | 9.010 | -0.311 | 0.684 | -0.060 | 0.917 |
| 4 | Priority 1 | Pulo Gadung | 8 | 1.310 | 2.630 | 0.504 | 0.871 | 1.680 | 0.906 |
| 5 | Priority 1 | Kebayoran Lama | 8 | 1.290 | 2.580 | -0.274 | 0.914 | 0.262 | 0.987 |
| 6 | Priority 1 | Grogol Petamburan | 14 | 1.250 | 5.850 | 0.445 | 0.914 | -0.564 | 0.906 |
| 7 | Priority 2 | Cilandak | 10 | 0.950 | 4.740 | -0.011 | 0.914 | 0.092 | 0.987 |
| 8 | Priority 2 | Senen | 5 | 0.850 | 4.270 | 0.711 | 0.871 | -0.617 | 0.906 |
| 9 | Priority 2 | Cilincing | 9 | 0.700 | 2.110 | 0.626 | 0.871 | 0.454 | 0.906 |
| 10 | Priority 2 | Jatinegara | 6 | 0.620 | 1.850 | -0.315 | 0.914 | 0.889 | 0.906 |
| 11 | Priority 2 | Tanah Abang | 5 | 0.610 | 3.050 | 3.070 | 0.137 | 1.570 | 0.880 |
| 12 | Priority 2 | Cakung | 8 | 0.560 | 1.500 | 0.778 | 0.871 | 1.262 | 0.906 |
| 13 | Priority 3 | Kramat Jati | 6 | 0.330 | 1.980 | -1.021 | 0.871 | -1.285 | 0.880 |
| 14 | Priority 3 | Jagakarsa | 6 | 0.310 | 1.850 | 0.088 | 0.890 | -0.239 | 0.987 |
| 15 | Priority 3 | Cengkareng | 6 | 0.180 | 1.090 | -0.867 | 0.871 | -0.824 | 0.906 |
| 16 | Priority 3 | Gambir | 9 | 0.000 | 9.700 | 1.323 | 0.871 | 0.265 | 0.906 |
| 17 | Priority 3 | Pademangan | 5 | 0.000 | 2.930 | -1.460 | 0.217 | -1.198 | 0.906 |

Tabel lengkap 42 kecamatan: `reports/tables/hotspot_prioritas.csv`.
