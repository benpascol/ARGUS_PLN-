# 📜 RULEBOOK (The Constitution of ARGUS)

Buku ini adalah hukum tertinggi dan aturan main dalam perancangan, pengembangan, dan audit kode pada proyek **ARGUS (Automated Recognition & Grid Utility Surveillance)**. Siapapun dan agen AI manapun yang bekerja pada *codebase* ini diwajibkan mematuhi 7 pilar konstitusi di bawah ini tanpa kecuali.

---

## 🧭 Pilar 1: Filosofi Pengembangan (Core Engineering Philosophy)

1. **Zero Hallucination on Numbers (Akurasi Angka adalah Harga Mati):**
   Nomor meteran (11 digit) dan IDPEL (12 digit) adalah data transaksi keuangan PLN. Kesalahan 1 digit saja berakibat fatal pada salah tagih pelanggan. Prioritaskan metode deterministik dengan *checksum* (Barcode Scanner ZBar) di atas tebakan probabilistik AI/VLM.
2. **Auditability over Black-Box:**
   Sistem penilai audit korporat tidak boleh beroperasi seperti kotak hitam (*black-box*). Setiap vonis keputusan (**Sesuai**, **Tidak Sesuai**, **Blur**) **WAJIB** disertai alasan logis (*audit reason*) yang dapat dipertanggungjawabkan di depan manajemen PLN.
3. **Pragmatism & Cascading Efficiency:**
   Gunakan alat yang paling ringan dan hemat untuk menyelesaikan masalah di tahap awal. Saring jutaan piksel buram menggunakan OpenCV gratisan (<5 ms), saring meteran barcode dengan ZBar (<30 ms), dan selesaikan deteksi angka serta proteksi fraud secara lokal tanpa token cloud.
4. **Anti-Fraud Vigilance:**
   Sistem ini dirancang untuk mendeteksi manipulasi petugas lapangan. Jangan pernah membuat aturan logika yang langsung meloloskan status "Sesuai" hanya karena di Excel tertulis kelainan bacaan tertentu tanpa memverifikasi bukti citranya secara nyata.
5. **Pure Local & Offline-First Sovereignty (Kedaulatan Sistem Mandiri Tanpa Cloud VLM):**
   Seluruh arsitektur inti ARGUS (Tier 1 Blur, Stage 1/2 YOLO Digit OCR, dan Anti-Fraud Triage) **WAJIB** berjalan 100% secara lokal dan *offline* di lingkungan komputasi PLN. Dilarang keras menggantungkan logika penagihan pada API cloud pihak ketiga yang rentan limit, kedaluwarsa, atau terputus internet. Hal ini menjamin kedaulatan data pelanggan PLN, keandalan operasional, dan latensi ultra-cepat.

---

## 📝 Pilar 2: Aturan Manajemen Versi & Protokol AI (Git & Commits Rules)

1. **Gitflow Workflow (3 Level Branches):**
   - **Level 1 (`main`):** Titik puncak (*The Peak*). Dilarang commit langsung. Hanya berisi rilis stabil yang siap dipakai operasional PLN.
   - **Level 2 (`develop`):** Cabang integrasi (Panci Rebusan). Tempat pengujian gabungan modul deteksi blur, barcode, VLM, dan antarmuka. **Pembaruan dokumen *Trinity* (`WHITEBOARD.md`, `RULEBOOK.md`, `README.md`) HANYA boleh dilakukan di branch ini.**
   - **Level 3 (`feature/*`):** Cabang pengerjaan lokal terisolasi per fitur (misal: `feat/laplacian-blur`, `feat/zbar-meter`, `feat/vlm-refactor`).

2. **Protokol Khusus Agen AI (Wajib Dipatuhi oleh Antigravity / Jarvis / Ares):**
   - **TRINITY ANALYSIS:** Agen AI **WAJIB** membaca dan menyinkronkan isi `WHITEBOARD.md`, `RULEBOOK.md`, dan `README.md` sebelum menulis kode baru dan sesudah menyelesaikan tugas.
   - **STOP & THINK:** Periksa selalu status `git branch` sebelum memodifikasi kode.
   - **MINTA IZIN DULU:** Dilarang keras melakukan eksekusi `git push` atau `commit` sepihak tanpa konfirmasi eksplisit kepada Pascol (Ben). Tanyakan: *"Perubahan ini ingin di-commit dengan pesan apa dan ke branch mana?"*.

3. **Atomic & Conventional Commits:**
   - Satu commit = satu unit perubahan logis terisolasi.
   - Dilarang keras menumpuk pembaruan OpenCV, integrasi VLM, dan perbaikan Userscript dalam 1 commit raksasa.
   - Gunakan format standar: `feat:` (fitur baru), `fix:` (perbaikan bug), `docs:` (pembaruan dokumentasi), `refactor:` (perombakan struktur kode), `chore:` (kebutuhan dependensi/lingkungan).

---

## 💻 Pilar 3: Standar Penulisan Kode (Coding Standards)

1. **Python Pipeline (Core Batch Engine):**
   - Wajib mematuhi PEP 8, gunakan type hints eksplisit (`def process_image(img_path: str) -> dict:`).
   - Penanganan file citra wajib menggunakan blok konteks aman (`with open(...)` atau fungsi baca OpenCV yang memvalidasi `image is not None`).
   - Jangan pernah mengasumsikan format citra selalu valid; sediakan blok `try-except` untuk menangani file korup atau *truncated JPEG*.
2. **Userscript Browser (`Tanpa judul.txt` / Tampermonkey):**
   - Gunakan standar modern ES6+ (Async/Await, Classes, Promises).
   - Pisahkan logika pemrosesan ke dalam kelas modular: `APIManager`, `ImageProcessor`, `DecisionEngine`, `UIController`, dan `ExportManager`.
   - Hindari manipulasi DOM secara berulang di dalam *loop* data besar (8.000 baris); gunakan `DocumentFragment` atau batch rendering virtual scrolling.
3. **Respon API Lokal & Standar Kontrak JSON Terstruktur:**
   - Seluruh endpoint API lokal (`/predict` dan `/predict-base64`) **WAJIB** mengembalikan skema JSON deterministik (`stand_baca`, `status`, `tier_color`, `is_valid`, `latency_ms`).
   - Respon wajib bertipe data native Python (bersih dari tipe objek NumPy float/int) agar serialisasi JSON berjalan cepat dan bebas crash.
   - Menyediakan metadata lengkap termasuk latency inferensi lokal untuk diagnostik performa di front-end.

---

## 🗂 Pilar 4: Aturan Dokumentasi (The Holy Trinity of Docs)

1. `README.md` = **Wajah Proyek.** Menjelaskan visi, arsitektur *Cascading Multi-Tier Pipeline*, diagram alur sistem, spesifikasi komponen, dan status kesehatan proyek.
2. `WHITEBOARD.md` = **Dapur Kotor.** Tempat mencatat rencana kerja (*Grand Plan*), rekam jejak ide (*Ideas Log*), audit teknis jujur (*The Good, The Bad, The Ugly*), dan tabel inventaris *Issue & Solution Log*.
3. `RULEBOOK.md` = **Kitab Hukum.** Dokumen ini. Konstitusi dan batasan teknis yang tidak boleh dilanggar.

---

## 🛡 Pilar 5: Keamanan & Privasi Data PLN

1. **Zero Hardcoding Credentials:**
   Dilarang keras menuliskan kredensial rahasia (Token Portal PLN, secret keys, dll) langsung di dalam file kode sumber atau file yang dipublikasikan. Kredensial wajib dipanggil melalui environment variable (`.env`) atau `GM_getValue` terenkripsi pada browser.
2. **Kerahasiaan Data Konsumen:**
   Data master pelanggan (IDPEL, Nama, Alamat, Tarif, Daya, Foto KWH Meter) adalah informasi rahasia PT PLN (Persero). Dilarang mengunggah dataset foto atau file Excel ke repositori publik. Gunakan `.gitignore` untuk melindungi folder `DOkumentasi LBKB/` dan file `.xlsx`.

---

## 🔬 Pilar 6: Standar Keandalan Sistem Visi (Computer Vision Integrity)

1. **Conservative Blur Thresholding & ROI-Focused Assessment:**
   Nilai ambang batas deteksi blur (Laplacian Variance) harus disetel secara konservatif. Lebih baik meloloskan foto yang agak redup ke tahap Barcode/VLM (*False Negative Blur*) daripada membuang foto valid yang sebenarnya nomor meternya masih bisa dibaca (*False Positive Blur*). Penilaian ketajaman wajib difokuskan pada Region of Interest (ROI) meteran untuk mencegah tekstur kasar background (dinding, aspal) mengelabui varians Laplacian.
2. **Pre-processing CLAHE untuk ZBar:**
   Sebelum memvonis barcode tidak terbaca, sistem wajib mencoba pipeline peningkatan kontras adaptif (*Contrast Limited Adaptive Histogram Equalization* / CLAHE) dan binarisasi Otsu guna menembus silau pantulan mika (*glare*) dan debu lapangan.
3. **Pemberian Skor Keyakinan (Confidence Score):**
   Setiap hasil pembacaan OCR digit meteran wajib menyertakan estimasi tingkat keyakinan (*confidence score*). Jika skor di bawah batas minimum (misal $< 0.70$) atau terindikasi gap/silau, arahkan baris data tersebut ke antrean review manual teknisi (🟡 Triage).
4. **Presedensi Checksum Matematis:**
   Hasil pembacaan nomor seri ber-checksum (ZBar) berstatus kepastian mutlak. Stage 1 YOLO dan heuristik ketiadaan dial counter (`FAIL_COUNTER_NOT_FOUND`) berperan mendeteksi anomali/fraud non-meteran secara deterministik dan bebas biaya token.
5. **Penyelarasan Kode Kelainan LBKB PLN:**
   Pemetaan kode kelainan pada keputusan sistem harus mengacu pada standar resmi PLN:
   - `E`: RUMAH TUTUP
   - `F`: RUMAH KOSONG
   - `1`: KWH METER TINGGI
   - `2`: GANTI KWH METER
   - `3`: ANJING GALAK
   - `4`: PAGAR TERKUNCI
   - `5`: BARCODE RUSAK/TIDAK ADA
6. **Kontrak Data Formal Antar Modul (Input/Output Contract):**
   Setiap pertukaran data antar Tier (Tier 1 s.d. Tier 4) wajib menggunakan skema data formal terstandarisasi (`ImageSignal` dan `AuditVerdict`). Dilarang melempar tipe data mentah yang tidak terdefinisi guna menjamin interoperabilitas antara batch CLI Python dan userscript Tampermonkey.
7. **Evaluasi Metrik Ganda & Penanganan Imbalanced Data:**
   Sistem audit LBKB dilarang hanya dievaluasi menggunakan akurasi persentase tunggal (*single accuracy metric*). Karena kasus kelainan dan fraud di lapangan bersifat minoritas (*imbalanced data*), evaluasi performa sistem wajib menyertakan **Precision**, **Recall**, dan **F1-Score**, serta metrik operasional seperti **Barcode Hit-Rate** dan **API Cost Saving**.
8. **Validasi Empiris Skala Penuh via Ground Truth Sampling:**
   Sebelum sistem dinyatakan siap serah terima operasional ke PLN, verifikasi akhir wajib dilakukan dengan metode *random sampling* minimal 100 baris data yang diverifikasi manual bersama petugas pengawas PLN sebagai dasar justifikasi ilmiah laporan akhir.
9. **Anti-Partial Stand Emission & Strict Sequence Integrity:**
   Sistem DILARANG KERAS mengeluarkan hasil pembacaan parsial/sebatang kara ke kolom `STAN_BACA` (seperti kasus silau yang hanya menyisakan angka "6"). Untuk meteran analog, hasil bacaan wajib memenuhi deretan horizontal kontinu minimal 4–6 digit. Jika kurang dari itu, sistem wajib menolak dan memvonis `STAND_TIDAK_LENGKAP` atau `ANOMALI_GLARE_TERHALANG`.
10. **Glare Gatekeeping (Pencegahan Saturasi Silau Matahari):**
    Sebelum meneruskan crop counter box ke model digit, sistem wajib mengevaluasi persentase piksel silau (HSV: V > 240, S < 30). Jika piksel silau melebihi 20% luas area angka, sistem wajib menghentikan inferensi digit dan menandai `ANOMALI_GLARE_TERHALANG`.
11. **Local Decimal Handling for Digital Meters:**
    Meteran digital harus ditangani secara lokal menggunakan deteksi titik desimal (`dot`). Stand meter resmi penagihan PLN adalah angka integer di depan titik desimal (`val.split('.')[0]`), sedangkan digit di belakang koma diabaikan sesuai SOP penagihan energi.

---

## 🛑 Pilar 7: Single Source of Truth (SSOT)

1. **Workspace Resmi Tunggal:**
   Direktori **`d:\Hooh_Lah\PLN\ARGUS\`** adalah satu-satunya rumah resmi pengembangan proyek ini. Dilarang merujuk atau menduplikasi pekerjaan ke folder lama (`Anyar`, dll).
2. **Integritas Sinkronisasi:**
   Segala modifikasi algoritma pada skrip pengujian lokal Python harus selaras secara konseptual dengan logika yang diimplementasikan pada userscript browser `Tanpa judul.txt`. Keduanya harus menghasilkan vonis klasifikasi yang konsisten.
