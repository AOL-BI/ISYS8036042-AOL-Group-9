# Scraping Data

Semua data diambil dari X dengan [tweet-harvest](https://github.com/helmisatria/tweet-harvest) (butuh Node.js + auth token akun X).
Hasil disimpan di `data/raw/<sumber>/` dan **tidak di-commit**.

## Keyword List

### Project kelompok: jalan rusak per kecamatan (scraping ulang)

Dibuat oleh `generate_queries.py`: 10 frasa kerusakan jalan × 42 kecamatan (+ 24 jalan utama dengan `--jalan`).

```
("jalan rusak" OR "jalanan rusak" OR "jalan berlubang" OR "jalan bolong" OR "jalan ambles" OR "jalan amblas"
 OR "aspal rusak" OR "aspal bolong" OR "lubang jalan" OR "jalan bergelombang") <kecamatan> [jakarta]
 lang:id -filter:retweets since:2019-01-01 until:<besok>
```

- Nama kecamatan yang juga ada di luar DKI (Pancoran, Cipayung, Setiabudi, Taman Sari, Makasar, dst.) diberi tambahan `jakarta`.
- Lokasi di data tetap diambil dari **isi tweet** saat preprocessing, bukan dari query, supaya peta tidak sekadar mengulang daftar keyword.

```bash
python src/scraping/generate_queries.py              # lihat semua perintah (format Colab/bash)
python src/scraping/generate_queries.py --run        # jalankan langsung, hasil ke data/raw/jalan_rusak_v2/tweets-data/
python src/scraping/generate_queries.py --run --per-tahun --hanya Tebet,Cilandak   # lebih lengkap untuk kecamatan tertentu
```

Token: salin `.env.example` jadi `.env`, isi `TWEET_HARVEST_TOKEN`. Kalau kena rate limit, jalankan ulang perintah yang sama; file yang sudah ada dilewati.

**Di Colab:**

```python
!git clone https://github.com/AOL-BI/ISYS8036042-AOL-Group-9.git
%cd ISYS8036042-AOL-Group-9
import os; os.environ["TWEET_HARVEST_TOKEN"] = "<token>"
!python src/scraping/generate_queries.py --run
```

### Personal assignment (data yang sudah ada)

| Anggota | Topik | Folder | Query |
|---|---|---|---|
| Fio | Jalan rusak | `data/raw/fio/` | `jakarta AND jalan bolong OR jakarta AND jalan berlubang OR jakarta AND jalan rusak OR jakarta AND jalan ambles` |
| Mail | Fasilitas (PJU, trotoar, JPO, halte) | `data/raw/mail/` | `jakarta AND lampu jalan mati OR ...` per kategori (4 file) |
| Angel | Kemacetan | `data/raw/angel/` | `macet <lokasi> since:2025-01-01 until:2026-10-05`, dst. (10 lokasi, 13 kelompok kata) |

Catatan untuk query lama (alasan query baru ditulis ulang):

- Kata tanpa tanda kutip (`jalan rusak`) dicari terpisah, jadi tweet yang memuat "jalan" dan "rusak" di mana saja ikut terambil (mis. sindiran politik "jalan pikiran yang rusak").
- `OR` di X hanya mengikat kata di sebelahnya. Tanpa tanda kurung, `jakarta AND jalan bolong OR jakarta AND jalan berlubang` tidak dibaca sebagai dua kelompok.
- Opsi `-f "01-01-2025"` tidak membatasi tanggal: data Fio mulai 2019 dan data Mail mulai 2009. Batas tanggal ditulis di dalam query (`since:` / `until:`), seperti query Angel.
