# Pemetaan Keluhan Infrastruktur & Prioritas Perbaikan

> **AOL Business Intelligence (ISYS8036042) · Group 9 · BINUS University**

Proyek ini membangun **model prediktif** dari keluhan masyarakat soal infrastruktur yang diambil dari media sosial. Keluhan dipetakan per kelurahan untuk menemukan *hotspot* dan membantu menentukan prioritas perbaikan.

> 📍 **Status (21 Okt 2026):** scope sudah final dan data sudah siap (M1 selesai). Sekarang masuk **M2 Modeling**: analisis hotspot, labeling urgensi, dan penentuan target model prediktif.

---

## 👥 Tim

| Nama | NIM | Peran | Topik personal assignment |
|------|-----|-------|---------------------------|
| Muhammad Rasyid Ismail | 2802939676 | _TBD_ | Keluhan fasilitas publik rusak (PJU, trotoar, JPO, halte) |
| Angelina Oktaviani Putri | 2802939650 | _TBD_ | Kemacetan |
| Alifah Olinda Fiorinda | 2802939726 | _TBD_ | Jalan rusak |

> Dosen mensyaratkan data personal assignment tiap anggota berbeda. Project kelompok memakai topik **jalan rusak**.

## 🎯 Scope

- **Wilayah:** DKI Jakarta, 5 kota administrasi daratan (Kepulauan Seribu tidak diikutkan). Unit analisis: kelurahan (261)
- **Jenis infrastruktur:** jalan rusak (berlubang, bolong, ambles, bergelombang, aspal rusak). Jalan tol, trotoar, JPO, dan flyover **tidak** termasuk.
- **Periode data:** 2019 – sekarang
- **Sumber data:** keluhan warga & media di X/Twitter (scraping dengan tweet-harvest), batas wilayah kelurahan (GeoJSON), estimasi penduduk per kelurahan (Satu Data Jakarta 2017 diskalakan ke BPS 2025)
- **Output:** model prediktif + peta *hotspot* keluhan per kelurahan. Target prediksi masih ditentukan di M2 ([#36](../../issues/36)); kandidatnya klasifikasi urgensi keluhan (lihat `docs/pembersihan-data.md`).

## 🗓️ Timeline

Detail task ada di [GitHub Project board](https://github.com/orgs/AOL-BI/projects/1).

| Milestone | Periode | Isi utama |
|-----------|---------|-----------|
| **M0** Kickoff & Prerequisites | 24 Sep – 4 Okt | Setup repo, finalisasi scope, konsultasi #1, cek kelayakan sumber data |
| **M1** Data Preparation | 28 Sep – 20 Okt | Literature review, akuisisi data, preprocessing, integrasi & EDA |
| **M2** Modeling | 19 Okt – 3 Nov | Hotspot spasial, labeling & feature engineering, modeling prediktif, konsultasi #2 |
| **M3** Evaluation & Recommendation | 1 – 5 Nov | Evaluasi model, insight & rekomendasi |
| **M4** Deliverables & Submission | 19 Okt – 13 Nov | Final report, presentasi, submission |

**Deadline akhir:** 13 November 2026, 23:30 WIB

## 🧰 Tools

- **Python:** scraping & preprocessing data
- **KNIME:** modeling (tanpa coding)
- **GitHub Projects:** manajemen task & timeline

## 📁 Struktur Folder

```
.
├── data/
│   ├── raw/            # hasil scraping mentah (tidak di-commit)
│   ├── processed/      # data bersih siap modeling (tidak di-commit)
│   ├── anotasi/        # test_set_ids.csv: id test set yang dibekukan (di-commit, tanpa teks)
│   └── external/       # GeoJSON kelurahan, data populasi BPS
├── src/
│   ├── scraping/       # generator query tweet-harvest
│   └── preprocessing/
│       ├── preprocess_jalan_rusak.py      # pipeline utama: data/raw/* -> data/processed/jalan_rusak/
│       ├── common.py                      # modul bersama (normalisasi teks, gazetteer, dll.)
│       ├── clean_tweets.py                # pipeline pembersihan & filtering relevansi (Fio), dokumentasi di docs/
│       ├── extract_jakarta_boundaries.py  # batas wilayah DKI dari data HDX
│       ├── build_populasi_kelurahan.py    # estimasi penduduk 2025 per kelurahan
│       ├── buat_test_set.py               # sampel test set + lembar anotasi buta (2 anotator)
│       └── personal/                      # arsip personal assignment tiap anggota
├── knime/              # workflow KNIME (root repo = KNIME workspace; data hasil eksekusi tidak di-commit)
├── notebooks/          # 01_pembersihan_data.ipynb, 02_data_understanding.ipynb (CRISP-DM)
├── docs/
│   ├── pembersihan-data.md  # penjelasan tahapan pembersihan & filtering relevansi
│   ├── pedoman-anotasi-urgensi.md  # pedoman label kategori & urgensi untuk test set
│   └── meeting-notes/       # notulen konsultasi dosen & rapat tim
├── reports/
│   ├── figures/        # grafik & peta untuk laporan/presentasi (du_* = Data Understanding)
│   └── tables/         # tabel pendukung laporan (data dictionary, isu kualitas data, dll.)
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

**Data:** folder `data/raw` dan `data/processed` tidak ada di git. Data mentah diambil dari **OneDrive tim** di path `/data/raw/data.zip`. Isinya folder `labels/`, `fio/`, `mail/`, dan `angel/`; folder `jalan_rusak_v2/` didapat dengan scraping ulang (lihat [`src/scraping/README.md`](src/scraping/README.md)).

1. Download `data.zip` dari OneDrive tim (`/data/raw/data.zip`).
2. Copy ke folder `data/raw/` di repo ini, jadi `data/raw/data.zip`.
3. Extract **langsung di `data/raw/`**, jangan ke subfolder baru:
   - **7-Zip / WinRAR:** klik kanan `data.zip` → *Extract Here*.
   - **Windows Explorer:** klik kanan → *Extract All…* → **hapus `\data` di ujung path tujuan**, sehingga tujuannya `...\data\raw`, lalu *Extract*.
   - **PowerShell** (dari root repo):
     ```powershell
     Expand-Archive data\raw\data.zip -DestinationPath data\raw
     ```
4. Cek hasilnya. Strukturnya harus seperti ini:
   ```
   data/raw/
   ├── angel/
   ├── fio/
   ├── labels/
   ├── mail/
   └── data.zip     # boleh dihapus setelah di-extract (sudah di-ignore git)
   ```
   Kalau yang muncul `data/raw/data/angel/...`, berarti salah extract: pindahkan isi `data/raw/data/` ke `data/raw/`, lalu hapus folder `data/raw/data/`.
5. Jalankan scraping (`jalan_rusak_v2`) dan pipeline di bawah untuk membuat `data/processed/`.

**KNIME:** buka **root repo ini sebagai KNIME workspace** (*File → Switch Workspace*). Path di workflow `knime/` relatif ke workspace, jadi akan error kalau repo dibuka dari workspace lain.

## 🔁 Pipeline Data

Semua script menghitung path dari root repo, jadi bisa dijalankan dari folder mana pun (lokal maupun Colab setelah `git clone`).

```bash
# 1. Scraping ulang per kecamatan (lihat src/scraping/README.md)
python src/scraping/generate_queries.py --run

# 2. Preprocessing gabungan: data/raw/* -> data/processed/jalan_rusak/
python src/preprocessing/preprocess_jalan_rusak.py
```

Pipeline pembersihan versi Fio (`clean_tweets.py`) bisa dijalankan terpisah; outputnya `data_final.csv`, `terbuang_topik.csv`, dan `sampel_label_manual.csv` (sampel anotasi dengan rumus Slovin). Detail tahapannya di [`docs/pembersihan-data.md`](docs/pembersihan-data.md).

```bash
# --input harus folder yang langsung berisi CSV (tidak membaca subfolder)
python src/preprocessing/clean_tweets.py --input data/raw/fio --output data/processed/clean_tweets
```

| Output (`data/processed/jalan_rusak/`) | Isi |
|---|---|
| `keluhan_jalan_rusak.csv` | Data utama modeling: teks, lokasi (kota/kecamatan/kelurahan), fitur waktu, tipe akun, label urgensi |
| `laporan_perbaikan.csv` | Publikasi perbaikan oleh instansi, layer pembanding untuk peta prioritas |
| `agregat_kelurahan.csv` / `agregat_kecamatan.csv` | Semua 261 kelurahan / 42 kecamatan (termasuk yang 0 keluhan) + penduduk 2025 |
| `untuk_dilabeli.csv` | Keluhan yang belum berlabel manual, isi kolom `urgensi` lalu simpan ke `data/raw/labels/` |
| `semua_kandidat.csv` | Semua baris + alasan dibuang, untuk audit |
| `ringkasan.md` | Angka untuk bagian Data Understanding |

Label urgensi manual: file CSV berkolom `id_str` + `urgensi` (`Tinggi` / `Sedang` / `Rendah` / `tidak_relevan`) di `data/raw/labels/`. Label manual menimpa label aturan.

**Test set (evaluasi):** `python src/preprocessing/buat_test_set.py` membuat lembar anotasi untuk 2 anotator di `data/processed/anotasi/` dari id beku di `data/anotasi/test_set_ids.csv`. Isi sesuai [`docs/pedoman-anotasi-urgensi.md`](docs/pedoman-anotasi-urgensi.md), simpan hasilnya di `data/raw/labels_test/`. **Jangan** taruh di `data/raw/labels/`, dan keluarkan id test set dari data latih model.

## 🔀 Alur Kerja Tim

1. **Satu issue = satu branch.** Format nama branch: `<tipe>/<no-issue>-<deskripsi-singkat>`
   - Contoh: `feat/6-keyword-scraping`, `data/7-geojson-kelurahan`, `docs/9-literature-review`
2. **Commit message** singkat dan jelas, sebut nomor issue-nya: `feat: tambah scraper keyword jalan rusak (#6)`
3. **Pull Request** ke `main`, tulis `Closes #<no-issue>` di deskripsi supaya issue otomatis tertutup. Minta minimal 1 anggota lain untuk review.
4. **Update status** di Project board (Todo → In Progress → Done).

## 🗄️ Kebijakan Data

- Data mentah & hasil olahan **tidak di-commit** ke repo. Data mentah disimpan di OneDrive tim (`/data/raw/data.zip`), cara pakainya di bagian **Setup** di atas.
- File kecil di `data/external/` (misal GeoJSON < 10 MB) boleh di-commit.
- **Jangan pernah commit** API key/token. Simpan di `.env`.
- Data hasil scraping yang dibagikan harus dianonimkan (hapus username/nama akun).
