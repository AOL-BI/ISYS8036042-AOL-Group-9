# Pemetaan Keluhan Infrastruktur & Prioritas Perbaikan

> **AOL Business Intelligence (ISYS8036042) · Group 9 · BINUS University**

Proyek ini membangun **model prediktif** dari keluhan masyarakat soal infrastruktur yang diambil dari media sosial. Keluhan dipetakan per kelurahan untuk menemukan *hotspot* dan membantu menentukan prioritas perbaikan.

> ⚠️ **Status:** scope & problem statement sedang difinalisasi ([#3](../../issues/3)). Bagian *Latar Belakang* dan *Scope* di bawah akan diperbarui setelah konsultasi dosen #1 ([#4](../../issues/4)).

---

## 👥 Tim

| Nama | NIM | Peran |
|------|-----|-------|
| Muhammad Rasyid Ismail | 2802939676 | _TBD_ |
| Angelina Oktaviani Putri | 2802939650 | _TBD_ |
| Alifah Olinda Fiorinda | 2802939726 | _TBD_ |

## 🎯 Scope (draft)

- **Wilayah:** DKI Jakarta, 5 kota administrasi daratan (Kepulauan Seribu tidak diikutkan). Unit analisis: kelurahan (261)
- **Jenis infrastruktur:** _TBD_
- **Sumber data:** keluhan dari media sosial (scraping), batas wilayah kelurahan (GeoJSON), estimasi penduduk per kelurahan (Satu Data Jakarta 2017 diskalakan ke BPS 2025)
- **Output:** model prediktif + peta *hotspot* keluhan

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
│   └── external/       # GeoJSON kelurahan, data populasi BPS
├── src/
│   ├── scraping/       # generator query tweet-harvest
│   └── preprocessing/  # pipeline jalan rusak + modul bersama (common.py)
│       └── personal/   # script/notebook personal assignment masing-masing anggota (arsip)
├── knime/              # workflow KNIME hasil export (.knwf)
├── notebooks/          # EDA & eksperimen (Jupyter)
├── docs/
│   └── meeting-notes/  # notulen konsultasi dosen & rapat tim
├── reports/
│   └── figures/        # grafik & peta untuk laporan/presentasi
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

## 🔁 Pipeline Data

Semua script menghitung path dari root repo, jadi bisa dijalankan dari folder mana pun (lokal maupun Colab setelah `git clone`).

```bash
# 1. Scraping ulang per kecamatan (lihat src/scraping/README.md)
python src/scraping/generate_queries.py --run

# 2. Preprocessing gabungan: data/raw/* -> data/processed/jalan_rusak/
python src/preprocessing/preprocess_jalan_rusak.py
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

## 🔀 Alur Kerja Tim

1. **Satu issue = satu branch.** Format nama branch: `<tipe>/<no-issue>-<deskripsi-singkat>`
   - Contoh: `feat/6-keyword-scraping`, `data/7-geojson-kelurahan`, `docs/9-literature-review`
2. **Commit message** singkat dan jelas, sebut nomor issue-nya: `feat: tambah scraper keyword jalan rusak (#6)`
3. **Pull Request** ke `main`, tulis `Closes #<no-issue>` di deskripsi supaya issue otomatis tertutup. Minta minimal 1 anggota lain untuk review.
4. **Update status** di Project board (Todo → In Progress → Done).

## 🗄️ Kebijakan Data

- Data mentah & hasil olahan **tidak di-commit** ke repo. Simpan di Google Drive tim: _link TBD_
- File kecil di `data/external/` (misal GeoJSON < 10 MB) boleh di-commit.
- **Jangan pernah commit** API key/token. Simpan di `.env`.
- Data hasil scraping yang dibagikan harus dianonimkan (hapus username/nama akun).
