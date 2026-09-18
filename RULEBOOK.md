# 📜 RULEBOOK (The Constitution of ARGUS)

Buku ini adalah hukum tertinggi dan aturan main dalam perancangan, pengembangan, dan audit kode pada proyek **ARGUS (Automated Recognition & Grid Utility Surveillance)**. Siapapun dan agen AI manapun yang bekerja pada *codebase* ini diwajibkan mematuhi 7 pilar konstitusi di bawah ini tanpa kecuali.

---

## 🧭 Pilar 1: Filosofi Pengembangan (Core Engineering Philosophy)

1. **Zero Hallucination on Numbers (Akurasi Angka adalah Harga Mati):**
   Nomor meteran (11 digit) dan IDPEL (12 digit) adalah data transaksi keuangan PLN. Kesalahan 1 digit saja berakibat fatal pada salah tagih pelanggan. Prioritaskan metode deterministik dengan *checksum* (Barcode Scanner ZBar) di atas tebakan probabilistik AI/VLM.
2. **Auditability over Black-Box:**
   Sistem penilai audit korporat tidak boleh beroperasi seperti kotak hitam (*black-box*). Setiap vonis keputusan (**Sesuai**, **Tidak Sesuai**, **Blur**) **WAJIB** disertai alasan logis (*audit reason*) yang dapat dipertanggungjawabkan di depan manajemen PLN.
3. **Pragmatism & Cascading Efficiency:**
   Gunakan alat yang paling ringan dan hemat untuk menyelesaikan masalah di tahap awal. Saring jutaan piksel buram menggunakan OpenCV gratisan (<5 ms), saring meteran barcode dengan ZBar (<30 ms), dan hanya gunakan VLM/API berbayar untuk sisa citra yang membutuhkan penalaran semantik kompleks.
4. **Anti-Fraud Vigilance:**
   Sistem ini dirancang untuk mendeteksi manipulasi petugas lapangan. Jangan pernah membuat aturan logika yang langsung meloloskan status "Sesuai" hanya karena di Excel tertulis kelainan bacaan tertentu tanpa memverifikasi bukti citranya secara nyata.

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
3. **Respon VLM Terstruktur (Strict JSON Protocol):**
   - Setiap panggilan ke API VLM (NVIDIA NIM / Gemini) **WAJIB** memaksa output berformat JSON valid tanpa teks pembuka/penutup basa-basi (*strictly no conversational filler*). Sediakan mekanisme JSON regex parser cadangan jika model menambahkan markdown block ````json ... ````.

---

## 🗂 Pilar 4: Aturan Dokumentasi (The Holy Trinity of Docs)

1. `README.md` = **Wajah Proyek.** Menjelaskan visi, arsitektur *Cascading Multi-Tier Pipeline*, diagram alur sistem, spesifikasi komponen, dan status kesehatan proyek.
2. `WHITEBOARD.md` = **Dapur Kotor.** Tempat mencatat rencana kerja (*Grand Plan*), rekam jejak ide (*Ideas Log*), audit teknis jujur (*The Good, The Bad, The Ugly*), dan tabel inventaris *Issue & Solution Log*.
3. `RULEBOOK.md` = **Kitab Hukum.** Dokumen ini. Konstitusi dan batasan teknis yang tidak boleh dilanggar.

---

## 🛡 Pilar 5: Keamanan & Privasi Data PLN

1. **Zero Hardcoding Credentials:**
   Dilarang keras menuliskan API Key (NVIDIA NIM API Key, Token Portal PLN, dll) langsung di dalam file kode sumber atau file yang dipublikasikan. Kredensial wajib dipanggil melalui environment variable (`.env`) atau `GM_getValue` terenkripsi pada browser.
2. **Kerahasiaan Data Konsumen:**
   Data master pelanggan (IDPEL, Nama, Alamat, Tarif, Daya, Foto KWH Meter) adalah informasi rahasia PT PLN (Persero). Dilarang mengunggah dataset foto atau file Excel ke repositori publik. Gunakan `.gitignore` untuk melindungi folder `DOkumentasi LBKB/` dan file `.xlsx`.

---

## 🔬 Pilar 6: Standar Keandalan Sistem Visi (Computer Vision Integrity)

1. **Conservative Blur Thresholding:**
   Nilai ambang batas deteksi blur (Laplacian Variance) harus disetel secara konservatif. Lebih baik meloloskan foto yang agak redup ke tahap Barcode/VLM (*False Negative Blur*) daripada membuang foto valid yang sebenarnya nomor meternya masih bisa dibaca (*False Positive Blur*).
2. **Pemberian Skor Keyakinan (Confidence Score):**
   Setiap hasil pembacaan OCR teks spidol atau inferensi VLM wajib menyertakan estimasi tingkat keyakinan (*confidence score*). Jika skor di bawah batas minimum (misal $< 0.70$), arahkan baris data tersebut ke antrean review manual teknisi.
3. **Penyelarasan Kode Kelainan LBKB PLN:**
   Pemetaan kode kelainan pada keputusan sistem harus mengacu pada standar resmi PLN:
   - `E`: RUMAH TUTUP
   - `F`: RUMAH KOSONG
   - `1`: KWH METER TINGGI
   - `2`: GANTI KWH METER
   - `3`: ANJING GALAK
   - `4`: PAGAR TERKUNCI
   - `5`: BARCODE RUSAK/TIDAK ADA

---

## 🛑 Pilar 7: Single Source of Truth (SSOT)

1. **Workspace Resmi Tunggal:**
   Direktori **`d:\Hooh_Lah\PLN\ARGUS\`** adalah satu-satunya rumah resmi pengembangan proyek ini. Dilarang merujuk atau menduplikasi pekerjaan ke folder lama (`Anyar`, dll).
2. **Integritas Sinkronisasi:**
   Segala modifikasi algoritma pada skrip pengujian lokal Python harus selaras secara konseptual dengan logika yang diimplementasikan pada userscript browser `Tanpa judul.txt`. Keduanya harus menghasilkan vonis klasifikasi yang konsisten.
