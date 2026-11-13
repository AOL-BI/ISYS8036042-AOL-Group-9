# Pemetaan Keluhan Infrastruktur & Prioritas Perbaikan

> **AOL Business Intelligence (ISYS8036042) · Group 9 · BINUS University**
>
> Paper: *Urgency Classification of Road Damage Complaints on X for District-Level Repair Prioritization in Jakarta*

Proyek ini mengklasifikasikan urgensi keluhan jalan rusak di X/Twitter (Tinggi / Sedang / Rendah), lalu menyusun **ranking prioritas perbaikan per kecamatan** di DKI Jakarta dan menguji pengelompokan spasialnya dengan Getis-Ord Gi*. Metodologinya mengikuti **CRISP-DM**.

> ✅ **Status (13 Nov 2026): selesai.** Deliverable yang dikumpulkan ke LMS: **paper** dan **slide presentasi** (tidak disimpan di repo ini). Repo ini berisi kode, tabel, dan gambar yang dipakai di paper.

---

## 📊 Ringkasan Hasil

| Tahap | Hasil |
|---|---|
| Data | 3.935 tweet mentah → **807 kandidat keluhan** (2019–2026) |
| Test set | 154 tweet, dilabeli buta oleh 2 anotator · κ kategori 0,53 · κ urgensi 0,38 |
| Model relevansi (Random Forest) | macro-F1 **0,759** (baseline 0,704) · presisi keluhan 0,53 → 0,77 |
| Model urgensi (4 model) | macro-F1 0,465–0,528, interval kepercayaan tumpang tindih |
| Deployment | 408 keluhan relevan → **188 kejadian** (48 Tinggi, 109 Sedang, 31 Rendah) |
| Ranking | **17 dari 42 kecamatan** cukup data (≥ 5 kejadian); Priority 1: Setia Budi, Matraman, Kelapa Gading, Pulo Gadung, Kebayoran Lama, Grogol Petamburan |
| Stabilitas ranking | Spearman 0,93–0,99 terhadap SVM, GBT, NB |
| Hotspot Gi* | Tidak ada hotspot/coldspot signifikan setelah koreksi FDR |

Angka lengkap: [`final_ringkasan.md`](reports/tables/final_ringkasan.md), [`model_hasil.md`](reports/tables/model_hasil.md), [`perbandingan_model.md`](reports/tables/perbandingan_model.md), [`eval_test_set.md`](reports/tables/eval_test_set.md), [`hotspot_ringkasan.md`](reports/tables/hotspot_ringkasan.md).

## 👥 Tim

| Nama | NIM | Peran | Topik personal assignment |
|------|-----|-------|---------------------------|
| Muhammad Rasyid Ismail | 2802939676 | Data pipeline, modeling & evaluasi | Keluhan fasilitas publik rusak (PJU, trotoar, JPO, halte) |
| Angelina Oktaviani Putri | 2802939650 | Literature review, analisis hotspot (QGIS) | Kemacetan |
| Alifah Olinda Fiorinda | 2802939726 | Pembersihan data, anotasi, Bab 1 & 3 | Jalan rusak |

> Dosen mensyaratkan data personal assignment tiap anggota berbeda. Project kelompok memakai topik **jalan rusak**.

## 🎯 Scope

- **Wilayah:** DKI Jakarta, 5 kota administrasi daratan (Kepulauan Seribu tidak diikutkan).
- **Unit analisis:** **kecamatan (42)**. Keluhan terlalu jarang di level kelurahan (261) untuk laju yang stabil; agregat kelurahan hanya dipakai deskriptif.
- **Jenis infrastruktur:** jalan rusak (berlubang, bolong, ambles, bergelombang, aspal rusak). Jalan tol, trotoar, JPO, dan flyover **tidak** termasuk.
- **Periode data:** 2019 – 2026
- **Sumber data:** keluhan warga & media di X/Twitter (scraping dengan tweet-harvest), batas wilayah BPS via HDX (GeoJSON), estimasi penduduk per kelurahan (Satu Data Jakarta 2017 diskalakan ke total kota 2025)

## 🔄 CRISP-DM → Kode

| Fase | Isi | Script / file |
|---|---|---|
| Business Understanding | Kriteria urgensi dari UU 22/2009 & Permen PU 13/2011 | [`docs/pedoman-anotasi-urgensi.md`](docs/pedoman-anotasi-urgensi.md) |
| Data Understanding | Volume, sumber, waktu, ketelitian lokasi | `notebooks/02_data_understanding.ipynb` |
| Data Preparation | Pembersihan, filter relevansi, ekstraksi lokasi, populasi | `src/scraping/`, `src/preprocessing/` |
| Modeling | TF-IDF + RF / SVM / GBT / NB, relevansi & urgensi | `src/modeling/eksperimen_model.py` |
| Evaluation | Test set buta, Cohen's kappa, macro-F1 + bootstrap CI | `src/evaluation/evaluasi_test_set.py`, `src/modeling/eksperimen_model.py` |
| Deployment | Prediksi, gabung jadi kejadian, ranking, perbandingan model, Gi* | `src/modeling/prediksi_final.py`, `src/modeling/bandingkan_model.py`, `src/spatial/` |

## 🗓️ Timeline

Detail task ada di [GitHub Project board](https://github.com/orgs/AOL-BI/projects/1).

| Milestone | Periode | Isi utama |
|-----------|---------|-----------|
| **M0** Kickoff & Prerequisites | 24 Sep – 4 Okt | Setup repo, finalisasi scope, konsultasi #1, cek kelayakan sumber data |
| **M1** Data Preparation | 28 Sep – 20 Okt | Literature review, akuisisi data, preprocessing, integrasi & EDA |
| **M2** Modeling | 19 Okt – 3 Nov | Hotspot spasial, labeling & feature engineering, modeling prediktif, konsultasi #2 |
| **M3** Evaluation & Recommendation | 1 – 5 Nov | Evaluasi model, insight & rekomendasi |
| **M4** Deliverables & Submission | 19 Okt – 13 Nov | Paper, presentasi, submission |

**Deadline akhir:** 13 November 2026, 23:30 WIB

## 🧰 Tools

- **Python** (pandas, scikit-learn, matplotlib): scraping, preprocessing, modeling, evaluasi, peta untuk paper
- **QGIS + PySAL** (esda, libpysal): Getis-Ord Gi* dan proyek peta QGIS
- **tweet-harvest** (Node.js): scraping X
- **GitHub Projects:** manajemen task & timeline

> **KNIME** sempat dipakai di awal, lalu diganti Python supaya 4 model bisa dibandingkan dengan konfigurasi yang sama dan hasilnya bisa direproduksi. Folder `knime/` disimpan sebagai arsip.

## 📁 Struktur Folder

```
.
├── data/
│   ├── raw/            # hasil scraping mentah + lembar anotasi terisi (tidak di-commit)
│   ├── processed/      # data bersih & hasil prediksi (tidak di-commit)
│   ├── anotasi/        # id test set & data latih yang dibekukan + label gold test set (tanpa teks)
│   └── external/       # batas wilayah DKI (HDX/BPS), data populasi
├── src/
│   ├── scraping/       # generator query tweet-harvest
│   ├── preprocessing/
│   │   ├── preprocess_jalan_rusak.py      # pipeline utama: data/raw/* -> data/processed/jalan_rusak/
│   │   ├── common.py                      # modul bersama (normalisasi teks, gazetteer, dll.)
│   │   ├── clean_tweets.py                # pipeline pembersihan versi awal (Fio), dokumentasi di docs/
│   │   ├── extract_jakarta_boundaries.py  # batas wilayah DKI dari data HDX
│   │   ├── build_populasi_kelurahan.py    # estimasi penduduk 2025 per kelurahan
│   │   ├── buat_test_set.py               # sampel test set + lembar anotasi buta (2 anotator)
│   │   ├── buat_lembar_latih.py           # sampel data latih + lembar anotasi (3 anotator)
│   │   └── personal/                      # arsip personal assignment tiap anggota
│   ├── evaluation/
│   │   └── evaluasi_test_set.py           # kesepakatan anotator, label gold, evaluasi label aturan
│   ├── modeling/
│   │   ├── eksperimen_model.py            # 4 model × relevansi/urgensi, evaluasi di test set
│   │   ├── prediksi_final.py              # deployment: prediksi -> kejadian -> ranking kecamatan
│   │   └── bandingkan_model.py            # dampak pilihan model ke ranking
│   └── spatial/
│       ├── buat_input_hotspot.py          # batas kecamatan + ranking -> reports/gis/kecamatan_hotspot_input.geojson
│       ├── kecamatan_hotspot_analysis.py  # Gi* (PySAL) + proyek & peta QGIS (butuh Python QGIS)
│       ├── verify_hotspot_outputs.py      # cek ulang output QGIS
│       ├── run_hotspot_windows.bat / run_hotspot_macos.sh
│       └── peta_hotspot.py                # peta prioritas & Gi* untuk paper (Python biasa)
├── notebooks/          # 01_pembersihan_data.ipynb, 02_data_understanding.ipynb
├── docs/
│   ├── pembersihan-data.md          # tahapan pembersihan & filtering relevansi
│   ├── pedoman-anotasi-urgensi.md   # pedoman label kategori & urgensi
│   ├── qgis_hotspot_workflow.md     # detail metode Gi* & cara menjalankan QGIS
│   └── meeting-notes/
├── reports/
│   ├── figures/        # du_* = Data Understanding, hs_* = hotspot & prioritas (*_paper = selebar 1 kolom paper)
│   ├── tables/         # du_*, eval_*, model_*, perbandingan_*, final_ringkasan, ranking_kecamatan, hotspot_*
│   └── gis/            # input & output analisis hotspot (GeoPackage, proyek QGIS, peta, statistik)
├── knime/              # arsip workflow KNIME awal (tidak dipakai di hasil akhir)
├── requirements.txt
└── .env.example
```

## ⚙️ Setup

```bash
git clone https://github.com/AOL-BI/ISYS8036042-AOL-Group-9.git
cd ISYS8036042-AOL-Group-9

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows (macOS/Linux: cp .env.example .env)
```

**Data:** folder `data/raw` dan `data/processed` tidak ada di git. Data mentah ada di **OneDrive tim** di path `/data/raw/data.zip`. Isinya 7 folder:

| Folder | Isi |
|---|---|
| `fio/`, `mail/`, `angel/` | Hasil scraping awal & dataset personal assignment |
| `jalan_rusak_v2/` | Scraping ulang per kecamatan (bisa dibuat ulang, lihat [`src/scraping/README.md`](src/scraping/README.md)) |
| `labels/` | Label manual lama |
| `labels_test/` | Lembar anotasi test set (anotator A & B), hasil diskusi, review pola petugas |
| `labels_latih/` | Lembar anotasi data latih (Mail, Fio, Angel) |

1. Download `data.zip` dari OneDrive tim (`/data/raw/data.zip`).
2. Copy ke folder `data/raw/` di repo ini, jadi `data/raw/data.zip`.
3. Extract **langsung di `data/raw/`**, jangan ke subfolder baru:
   - **7-Zip / WinRAR:** klik kanan `data.zip` → *Extract Here*.
   - **Windows Explorer:** klik kanan → *Extract All…* → **hapus `\data` di ujung path tujuan**, sehingga tujuannya `...\data\raw`, lalu *Extract*.
   - **PowerShell** (dari root repo):
     ```powershell
     Expand-Archive data\raw\data.zip -DestinationPath data\raw
     ```
4. Cek hasilnya: harus ada 7 folder di atas langsung di bawah `data/raw/`. Kalau yang muncul `data/raw/data/angel/...`, berarti salah extract: pindahkan isi `data/raw/data/` ke `data/raw/`, lalu hapus folder `data/raw/data/`.

## 🔁 Reproduksi Hasil

Semua script menghitung path dari root repo, jadi bisa dijalankan dari folder mana pun. Jalankan berurutan:

```bash
# Data Preparation
python src/preprocessing/preprocess_jalan_rusak.py      # data/raw/* -> data/processed/jalan_rusak/

# Data Understanding: jalankan notebooks/02_data_understanding.ipynb -> reports/figures/du_*, reports/tables/du_*

# Evaluation: kesepakatan anotator + label gold test set
python src/evaluation/evaluasi_test_set.py              # -> reports/tables/eval_*, data/anotasi/test_set_gold.csv

# Modeling + Evaluation: 4 model, relevansi & urgensi
python src/modeling/eksperimen_model.py                 # -> reports/tables/model_*

# Deployment: model utama (Random Forest) -> ranking kecamatan
python src/modeling/prediksi_final.py                   # -> reports/tables/ranking_kecamatan.csv, final_ringkasan.md
python src/modeling/bandingkan_model.py                 # -> reports/tables/perbandingan_*

# Analisis spasial
python src/spatial/buat_input_hotspot.py                # -> reports/gis/kecamatan_hotspot_input.geojson
python src/spatial/peta_hotspot.py                      # -> reports/figures/hs_*, reports/tables/hotspot_*
```

- **Gi\* & proyek QGIS** (`reports/gis/outputs/`) sudah tersimpan di repo. Untuk menghitung ulang, perlu Python milik QGIS: `src\spatial\run_hotspot_windows.bat` (Windows) atau `bash src/spatial/run_hotspot_macos.sh` (macOS). Detail: [`docs/qgis_hotspot_workflow.md`](docs/qgis_hotspot_workflow.md).
- **Scraping ulang** (opsional, `jalan_rusak_v2` sudah ada di `data.zip`): `python src/scraping/generate_queries.py --run`, butuh `TWEET_HARVEST_TOKEN` di `.env`.
- **Lembar anotasi** dibuat oleh `buat_test_set.py` dan `buat_lembar_latih.py` dari id yang sudah dibekukan di `data/anotasi/`. Keduanya tidak menimpa lembar yang sudah terisi. Test set **tidak pernah** dipakai untuk melatih model.

## 🔀 Alur Kerja Tim

1. **Satu issue = satu branch.** Format nama branch: `<tipe>/<no-issue>-<deskripsi-singkat>`
   - Contoh: `feat/6-keyword-scraping`, `data/7-geojson-kelurahan`, `docs/9-literature-review`
2. **Commit message** singkat dan jelas, sebut nomor issue-nya: `feat: tambah scraper keyword jalan rusak (#6)`
3. **Pull Request** ke `main`, tulis `Closes #<no-issue>` di deskripsi supaya issue otomatis tertutup. Minta minimal 1 anggota lain untuk review.
4. **Update status** di Project board (Todo → In Progress → Done).

## 🗄️ Kebijakan Data

- Data mentah & hasil olahan **tidak di-commit** ke repo karena berisi teks tweet dan username. Data mentah disimpan di OneDrive tim (`/data/raw/data.zip`), cara pakainya di bagian **Setup** di atas.
- Yang di-commit hanya id, label, dan agregat tanpa teks (`data/anotasi/`, `reports/tables/`), plus file kecil di `data/external/`.
- **Jangan pernah commit** API key/token. Simpan di `.env`.
- Username di data olahan diganti hash (`ANONIM_SALT` di `.env`).
