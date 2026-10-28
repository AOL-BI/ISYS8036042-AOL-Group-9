# Pedoman Anotasi Urgensi Keluhan Jalan Rusak

Pedoman ini dipakai untuk melabeli **test set** secara manual. Test set dipakai untuk mengevaluasi
label aturan dan model, jadi anotasinya harus **independen**: anotator hanya membaca teks tweet,
tanpa melihat label aturan, label anotator lain, atau hasil model.

## 1. Prosedur

1. Dua anotator melabeli file yang sama secara terpisah (`test_set_anotator_A.csv` dan `test_set_anotator_B.csv`). Jangan saling melihat jawaban sebelum selesai.
2. Isi kolom `kategori` dulu. Kolom `urgensi` **hanya diisi kalau `kategori` = `keluhan`**.
3. Nilai hanya dari isi teks. Jangan membuka link, gambar, atau profil akun.
4. Kalau ragu, tetap pilih satu jawaban dan tulis alasannya di kolom `catatan`.
5. Setelah keduanya selesai, hitung kesepakatan (Cohen's kappa), lalu diskusikan baris yang berbeda sampai sepakat. Hasil kesepakatan menjadi **label emas** (*gold label*).
6. Simpan hasil di `data/raw/labels_test/`. **Jangan** taruh di `data/raw/labels/`, karena folder itu dibaca pipeline sebagai label latih.

## 2. Kolom `kategori`

| Nilai | Kapan dipakai | Contoh (parafrase) |
|---|---|---|
| `keluhan` | Menceritakan **kerusakan jalan yang nyata** (dilihat, dialami, atau dilaporkan masih ada), siapa pun pengirimnya (warga, media, polisi lalu lintas, anggota dewan). **Lokasi tidak harus spesifik**; "jalanan Jakarta" pun boleh, asal kerusakannya konkret | "Jalan berlubang di depan halte X, hati-hati melintas"; "Tolong jalan di kampung kami diperbaiki, sudah 6 bulan rusak" |
| `laporan_perbaikan` | Kerusakan **sudah atau sedang ditangani** petugas dan inti pesannya adalah kegiatan penanganan | "Kegiatan tindak lanjut jalan berlubang oleh Sudin Bina Marga"; "Sedang ada perbaikan jalan di Jl. Y, hati-hati melintas" |
| `berita_umum` | Berita, kebijakan, statistik, ajakan, atau **opini/komentar umum** tentang jalan rusak tanpa menceritakan kerusakan konkret | "Bina Marga mencatat 6.000 titik jalan berlubang"; "Gubernur minta jalan rusak segera diperbaiki"; "Cara mengadu jalan rusak" |
| `bukan_jalan_rusak` | Yang rusak bukan jalan (pagar, trotoar, JPO, CCTV), lokasi di luar DKI, jalan tol, atau "lubang" bukan kerusakan (mis. nama tempat "Kampung Lubang") | "Pagar pembatas di halte dirusak pengunjuk rasa" |

Pertanyaan kunci untuk membedakan `keluhan` dan `berita_umum`: *"Ada jalan rusak sungguhan yang sedang diceritakan, atau hanya membicarakan jalan rusak secara umum?"*

| Contoh (parafrase) | Kategori |
|---|---|
| "Jakarta banyak jalan rusak ya" | `berita_umum` |
| "Jalan rusak di Jakarta makin parah tiap musim hujan, gubernurnya ngapain aja" | `berita_umum` |
| "Jalanan Jakarta banyak lubang, tadi pagi hampir jatuh" | `keluhan` (Tinggi) |
| "Jalan-jalan di Jakarta Timur banyak yang retak" | `keluhan` (Rendah) |

Catatan: "TL" di tweet bisa berarti **traffic light** (lokasi) atau **tindak lanjut** (penanganan). Baca konteksnya.

## 3. Kolom `urgensi` (hanya untuk `kategori` = `keluhan`)

Pilih **kelas tertinggi** yang buktinya ada di teks.

| Kelas | Kriteria | Penanda yang biasa muncul |
|---|---|---|
| **Tinggi** | Sudah ada korban, atau kerusakan membuat jalan tidak bisa dilalui dengan aman | korban jiwa atau luka, kecelakaan/terjatuh/terperosok karena jalan rusak; jalan ambles, longsor, runtuh; lubang besar/dalam/menganga; jalan ditutup atau dialihkan karena kerusakan |
| **Sedang** | Kerusakan nyata yang membahayakan atau mengganggu, tapi belum ada korban dan jalan masih bisa dilalui | peringatan rawan/bahaya/hati-hati; menyebabkan macet atau penyempitan; rusak parah atau meluas; permintaan segera diperbaiki atau keluhan berulang ("tak kunjung diperbaiki") |
| **Rendah** | Kerusakan ringan tanpa indikasi bahaya atau gangguan | retak, bergelombang, lubang kecil, aspal keriting; atau hanya menyebut "jalan rusak" tanpa keterangan dampak |

Aturan bantu:

- Peringatan polisi/TMC bahwa ada lubang yang **sudah ditutup barrier sementara** tetap `keluhan` (kerusakannya masih ada), urgensinya dinilai dari kondisi kerusakannya.
- Retweet atau kutipan dinilai dari isi teks yang dikutip.
- Kata emosional saja ("kesel banget") tidak menaikkan urgensi tanpa keterangan kondisi atau dampak.

## 4. Perbedaan dengan label aturan yang sudah ada (perlu disepakati tim)

Label aturan di `preprocess_jalan_rusak.py` memasukkan **pemberitaan agregat** ("495 ruas jalan rusak", "6.934 titik") ke kelas **Rendah**,
dan sebagian label manual lama memberi urgensi pada **laporan perbaikan petugas**. Di pedoman ini keduanya **bukan keluhan**
(`berita_umum` dan `laporan_perbaikan`), karena urgensi menilai kondisi kerusakan di satu lokasi, bukan kinerja instansi atau
statistik se-Jakarta. Kalau tim memakai pedoman ini, aturan dan label lama perlu disesuaikan sebelum modeling.
