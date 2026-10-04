# Pembersihan Data Keluhan Kerusakan Jalan DKI Jakarta

Pipeline praproses data tweet keluhan kerusakan jalan di DKI Jakarta, untuk
penelitian klasifikasi tingkat urgensi keluhan menggunakan TF-IDF dan Random Forest.

## Latar

Data hasil scraping media sosial bercampur dengan konten di luar ruang lingkup
penelitian: berita, idiom ("siang bolong", "gali lubang"), keluhan di luar DKI,
serta kerusakan objek lain yang kebetulan berlokasi di suatu jalan
("CCTV **di Jalan** Pejompongan **rusak**"). Skrip ini menyaring data tersebut
secara bertahap dan terdokumentasi.

## Tahapan

| No | Tahap | Keterangan |
|----|-------|------------|
| 1 | Penggabungan | Semua CSV hasil scraping digabung |
| 2 | Deduplikasi | Berdasarkan ID tweet dan teks ternormalisasi |
| 3 | Buang retweet | Baris berawalan `RT @` |
| 4 | Filter tahun | Default mulai 2019 |
| 5 | Ekstraksi lokasi | Gazetteer kawasan → kota administrasi; regex nama jalan |
| 6 | Filter area | Hanya DKI Jakarta |
| 7 | Filter topik | Subjek kerusakan harus jalan, bukan objek lain |
| 8 | Jenis konten | Pisahkan keluhan vs laporan perbaikan instansi |
| 9 | Sampling | Rumus Slovin untuk ukuran sampel anotasi manual |

### Penentuan subjek kerusakan

Tahap 7 tidak sekadar mencocokkan kata kunci, melainkan menentukan **objek mana
yang rusak** dengan tiga aturan:

1. Kata benda terdekat sebelum kata kerusakan menjadi kandidat subjek
2. Frasa lokatif (`di Jalan X`, `dekat gedung Y`) diperlakukan sebagai keterangan
   tempat, bukan subjek
3. Pola maju (`lubang di Jalan X`) tidak boleh melewati batas kalimat

Contoh perilaku:

| Teks | Hasil |
|------|-------|
| Dua kamera CCTV di Jalan Pejompongan rusak | dibuang |
| Trotoar di Jalan Kali Buaran ambles | dibuang |
| AC nya lagi rusak. Sepanjang jalan hoek2. | dibuang |
| Ruas Jalan Sudirman dekat gedung UOB rusak parah | disimpan |
| Memperbaiki lubang di Jalan Budi Mulia | disimpan |

## Cara pakai

```bash
pip install -r requirements.txt
python src/clean_tweets.py --input data/raw --output data/processed
```

Keluaran di folder `--output`:

- `data_final.csv` — data bersih siap dianalisis
- `terbuang_topik.csv` — baris yang tersaring, untuk audit dan lampiran metodologi
- `sampel_label_manual.csv` — sampel acak ukuran Slovin, siap dianotasi

## Konfigurasi

Parameter diubah di bagian atas `src/clean_tweets.py`:

| Parameter | Default | Fungsi |
|-----------|---------|--------|
| `TAHUN_MIN` | `2019` | Batas tahun paling awal |
| `WILAYAH_SEKITAR` | `False` | Sertakan Bekasi/Tangerang/Depok/Bogor |
| `BUANG_LAPORAN_PERBAIKAN` | `True` | Buang publikasi kinerja instansi |
| `BUANG_TROTOAR` | `True` | Buang keluhan trotoar |
| `BUANG_JPO` | `True` | Buang JPO dan jembatan layang |
| `BUANG_TOL` | `True` | Buang jalan tol |
| `WAJIB_LOKASI_SPESIFIK` | `False` | Wajib ada wilayah atau nama jalan |
| `MARGIN_ERROR` | `0.05` | Margin of error rumus Slovin |

## Keterbatasan

- Penyaringan berbasis aturan tidak memahami konteks semantik. Kalimat sindiran
  atau kiasan yang menyebut jalan rusak masih dapat lolos; penyaringan akhir
  dilakukan pada tahap anotasi dan klasifikasi.
- Tingkat keberhasilan ekstraksi lokasi terbatas pada tweet yang menyebut kawasan
  atau nama jalan secara eksplisit.
- Daftar gazetteer disusun manual dan belum mencakup seluruh kelurahan di DKI.

## Catatan data

Berkas data tidak disertakan dalam repositori ini (lihat `.gitignore`). Data
tweet memuat informasi akun publik sehingga perlu dianonimkan sebelum
dipublikasikan.
