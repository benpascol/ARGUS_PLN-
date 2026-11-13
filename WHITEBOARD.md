# 🎯 Section 1: Current Grand Plan

> [!NOTE]
> **👥 Roster Tim & Konvensi Kontribusi:**
>
> - **Lead Engineer (Perangkat Ini):** Pascol
> - **Anggota Tim / Kontributor:** _(Setiap rekan tim wajib mencantumkan nama masing-masing pada setiap pembaruan log/whiteboard)_
> - **Format Standar Log:** `[Tanggal] - [Nama Kontributor]` (contoh: `[31-10-2026] - Pascol`)

> [!IMPORTANT]
> **Fokus Utama Saat Ini:** Tahap 4 & 5 SELESAI secara arsitektur dan implementasi: **Dashboard Mandiri ARGUS V5** (`/dashboard`), **Local REST API Engine (FastAPI)**, **Human-in-the-Loop Modal Inspector**, **Celengan Feedback AI Persisten (Target 1.000 Kasus)**, **Ekspor Excel Resmi UP3 Mojokerto**, dan **Standalone Portable Packaging (`dist/ARGUS/ARGUS.exe`)**. Kini bersiap menuju **Pilot Run & Ground Truth Sampling 100 Baris bersama PT PLN (Persero) UP3 Mojokerto**.
> **Affected Areas:** Modul Visi (`src/vision_ai/`), API Backend (`src/api/`), Celengan Feedback (`src/feedback_vault.py`), Dashboard Mandiri (`web_extension/dashboard/`), Packaging (`build_exe.py`), Panduan (`PETUNJUK_PENGGUNAAN_ARGUS.txt`), dan Dokumen *Holy Trinity*.
> **Dokumentasi Resmi:** [`README.md`](file:///d:/Hooh_Lah/PLN/ARGUS/README.md), [`RULEBOOK.md`](file:///d:/Hooh_Lah/PLN/ARGUS/RULEBOOK.md), [`WHITEBOARD.md`](file:///d:/Hooh_Lah/PLN/ARGUS/WHITEBOARD.md).
> **Success Criteria:**
>
> 1. Terbuktinya metrik Laplacian Variance pada ROI dalam memisahkan foto buram/rusak dari foto layak audit pada sampel foto lapangan $\pm 20$ citra. _(Status: DONE ✅ - `quality_filter.py`)_
> 2. Terverifikasinya pembacaan nomor meteran 11 digit via Barcode Reader ZBar + CLAHE secara otomatis tanpa halusinasi pada KWH Meter prabayar bertipe stiker barcode. _(Status: HOLD (PLN) - `barcode_engine.py` siap pakai)_
> 3. Jaring Pengaman Anti-Fraud Heuristik via Stage 1 YOLO (`FAIL_COUNTER_NOT_FOUND`) aktif menolak foto non-meteran (aspal/jok/tanah) tanpa halusinasi angka. _(Status: DONE ✅ - 02-11-2026)_
> 4. Sinkronisasi logika Decision Engine dengan data kolom Excel sheet `Detail` / Rekap ACMT (`IDPEL`, `NAMA`, `STAN_LAPANGAN`) serta ekspor laporan resmi ber-hyperlink. _(Status: DONE ✅ - 12-11-2026)_
> 5. Evaluasi performa sistem berbasis metrik komprehensif (Precision, Recall, F1-Score, Barcode Hit-Rate, Cost Saving) dan validasi Ground Truth 100 sampel manual bersama PLN. _(Status: PLANNED — Menunggu Uji Lapangan PLN)_
> 6. Eksekusi pengemasan ganda (_dual-mode packaging_): Dashboard Web Mandiri + Standalone Portable Executable (`dist/ARGUS/ARGUS.exe`), Worker Pool paralel GPU, serta Celengan Feedback AI 1.000 kasus. _(Status: DONE ✅ - 13-11-2026)_

---

### 🚀 Roadmap Fase Pengembangan ARGUS (Sesuai Metodologi MLLC + IEEE):

#### 🔹 FASE 0: Validasi Ilmiah & Grounding Arsitektur [SELESAI ✅ — 26-09-2026]

- [x] **Riset Literatur & Komparasi Industri:** Validasi cascading pipeline vs Pure VLM vs Fine-tuned YOLO.
- [x] **Dokumentasi Ilmiah:** Penyusunan laporan validasi di [`Docs/ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md) dengan 6 sitasi jurnal terindeks (MDPI, IEEE, CMC).
- [x] **Penyusunan Roadmap Metodologi:** Pemetaan lengkap langkah pengembangan berbasis standar MLLC & IEEE di [`Docs/ARGUS_Methodology_Roadmap.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Methodology_Roadmap.md).
- [x] **Identifikasi Mitigasi Teknis:** Penambahan strategi ROI cropping untuk Laplacian dan enhancement CLAHE untuk ZBar.

#### 🔹 FASE 1: Pengujian Empiris Sampel & Benchmarking (PoC Lapangan) [AKTIF 🚀]

1. 🔲 **Langkah 1.1 — Seleksi & Organisasi Sampel Terstruktur (5 Skenario):**
   - Mengambil 15–20 sampel foto nyata dari `DOkumentasi LBKB/` dan mengorganisasikannya ke subfolder terpisah:
     - `data/samples/A_barcode_jelas/` (KWH Meter prabayar stiker barcode ideal - baseline hit-rate ZBar)
     - `data/samples/B_barcode_terhambat/` (Silau mika, pantulan matahari, debu tebal - uji ketangguhan CLAHE)
     - `data/samples/C_lcd_sudut_miring/` (KWH Meter dengan display LCD diambil dari sudut miring - uji Warp & OCR)
     - `data/samples/D_rintangan_fisik/` (Pagar gembok, pintu tutup kode E & F - uji YOLO-Cls & VLM)
     - `data/samples/E_foto_fraud/` (Aspal, jok motor, dinding kosong - uji deteksi anomali/fraud)
2. 🔲 **Langkah 1.2 — Benchmark Tier 1: Deteksi Blur OpenCV Laplacian (ROI-Focused):**
   - Menghitung $\text{Var}(L)$ pada area tengah ROI meteran (menghindari background clutter dinding/aspal).
   - Menguji perbandingan 3 threshold: 30, 80, 120 untuk mengukur _False Rejection_ vs _False Acceptance_.
3. 🔲 **Langkah 1.3 — Benchmark Tier 2A: Barcode Scanner ZBar + Preprocessing CLAHE:**
   - Uji 3 tahap bertahap (Baseline, +CLAHE, +Full Pipeline Otsu/Morph) untuk membaca nomor seri 11 digit.
4. 🔲 **Langkah 1.4 — Benchmark Tier 2B: Two-Stage Local YOLO Digit Reader & Digital Meter Handler:**
   - _Stage 1 (Localizer):_ `models/meter_counter_detector.pt` mendeteksi dan memotong (_crop_) kotak counter/layar display meteran dari foto utuh 540x960.
   - _Stage 2 (Digit OCR):_ `models/digit_ocr_detector.pt` mendeteksi bounding boxes angka `0-9` dan titik desimal `dot` secara lokal dalam 4.2 ms (mAP@50 96.1% via anti-flip training).
   - _Quality & Glare Gatekeeper:_ Memeriksa kebersihan crop sebelum dioper ke deteksi angka (mencegah false reading akibat silau seperti Sampel #6).
   - _Strict Sequence Validator:_
     - Meter Analog: Wajib deretan horizontal kontinu 4–6 digit (tolak angka sebatang kara/parsial).
     - Meter Digital: Pengurutan sumbu X dengan pemisah `dot` (angka depan koma = stand resmi PLN).
5. 🔲 **Langkah 1.5 — Tier 3: Klasifikasi Rintangan Lokal (YOLO-Cls [HOLD]) & Heuristik Zero-Counter [AKTIF ✅]:**
   - Mengadopsi deteksi ketiadaan dial counter (`FAIL_COUNTER_NOT_FOUND`) sebagai proteksi fraud langsung (aspal, jok motor, dinding kosong).
   - Menyiapkan arsitektur YOLO-Cls lokal (on HOLD) untuk dilatih di kemudian hari setelah dataset rintangan lapangan disediakan oleh PLN UP3 Mojokerto. Seluruh dependensi Cloud VLM dieliminasi total.
6. 🔲 **Langkah 1.6 — Dokumentasi Benchmark & Penguncian Threshold Resmi:**
   - Merekam seluruh angka hasil benchmark di `WHITEBOARD.md` (Section 3).
   - Mengunci nilai `BLUR_THRESHOLD`, `GLARE_THRESHOLD`, dan parameter CLAHE ke `RULEBOOK.md` dan `.env` sebagai Single Source of Truth.

#### 🔹 FASE 2: Perancangan Core Decision Engine & Arbitrase Logika

6. 🔲 **Langkah 2.1 — Desain Kontrak Data Formal (Input/Output Contract Schema):**
   - Mendefinisikan class skema data formal (`ImageSignal` dan `AuditVerdict`) sebelum menulis logika keputusan untuk menjamin konsistensi antar modul.
7. 🔲 **Langkah 2.2 — Implementasi Modul Arbitrase Keputusan Berjenjang:**
   - Membangun hierarki keputusan deterministik: Filter Blur (T1) $\rightarrow$ Match Barcode Checksum (T2) $\rightarrow$ Penalaran Scene VLM (T3).
   - Pemetaan ke 3 vonis resmi: `Sesuai dengan Data`, `Tidak Sesuai dengan Data`, `Hasil foto blur`.
8. 🔲 **Langkah 2.3 — Implementasi Confidence Scoring & Audit Trail Logging:**
   - Menghasilkan alasan keputusan berbahasa bisnis PLN (`audit_reason`) yang akuntabel.
   - Menetapkan routing data dengan `confidence_score < 0.70` ke antrean `PERLU_REVIEW_MANUAL = True`.
9. 🔲 **Langkah 2.4 — Evaluasi Decision Engine dengan Metrik Ganda (Bukan Hanya Akurasi):**
   - Menghitung **Precision**, **Recall** (terutama untuk menangkap fraud), **F1-Score**, **Barcode Hit-Rate**, dan **API Cost Saving** (target 70-80%).

#### 🔹 FASE 3: Dual-Mode Packaging, Dashboard Mandiri V5 & Integrasi Operasional [SELESAI ✅ — 13-11-2026]

10. ✅ **Langkah 3.1 — Modularisasi Backend Visi & Local FastAPI Engine (`src/vision_ai/`, `src/api/`):**
    - Pemisahan bersih `quality_filter.py`, `barcode_engine.py`, `counter_detector.py`, `digit_ocr.py`, `sequence_arbiter.py`, dan orchestrator `pipeline.py`.
    - Local FastAPI server (`src/api/server.py`, `routes/audit.py`, `routes/excel.py`, `routes/feedback.py`, `routes/views.py`) lengkap dengan deteksi hardware otomatis (`/api/system-info`) dan ekspor laporan Excel resmi ber-hyperlink (`src/audit_excel.py`).
11. ✅ **Langkah 3.2 — Dashboard Mandiri ARGUS V5, Human-in-the-Loop & Celengan Feedback AI (`web_extension/dashboard/`):**
    - Dual-mode upload + anti-duplikasi foto, auto-pairing rekap ACMT (`.xlsx`/`.csv`), mode audit `AUTO` / `MANDIRI` / `KOMPARASI`, Enterprise Virtual Pagination + quick sort kolom, serta Worker Pool batch paralel GPU.
    - Modal Pratinjau HD (`inspectPhoto`) dengan zoom/pan, navigasi `←`/`→` mengikuti filter & sortir aktif, hotkey vonis `[1..5]`, Smart Baseline Un-Edit, dan pemisahan Catatan PLN vs Catatan Model AI (`Salah Baca Angka`, `Digit Terpotong`, `Rolling Meleset`).
    - Celengan Feedback AI Persisten (`src/feedback_vault.py`, target 1.000 kasus unik, auto-pack ZIP ke `data/feedback_releases/`) dengan `#modal-vault-manager` dan tombol `Kemas Paket Sekarang`.
12. ✅ **Langkah 3.3 — Standalone Portable Executable (`build_exe.py` → `dist/ARGUS/ARGUS.exe`):**
    - Kemasan `--onedir` portabel dengan startup banner instan, unbuffered stdout, proteksi QuickEdit freeze Windows, auto-launch browser ke `/dashboard`, dan panduan lengkap [PETUNJUK_PENGGUNAAN_ARGUS.txt](file:///d:/Hooh_Lah/PLN/ARGUS/PETUNJUK_PENGGUNAAN_ARGUS.txt).

#### 🔹 FASE 4: Pilot Test Skala Penuh, Evaluasi & Serah Terima

12. 🔲 **Langkah 4.1 — Pilot Run Penuh Dataset Rek 12 2025:**
    - Eksekusi pipeline pada seluruh 7.470 foto dokumentasi LBKB, memantau stabilitas latensi dan error rate.
13. 🔲 **Langkah 4.2 — Evaluasi Akurasi Ilmiah via Ground Truth Sampling (100 Baris Manual):**
    - Mengambil 100 sampel baris acak dari output ARGUS dan memverifikasinya secara manual bersama petugas PLN.
    - Menghitung akurasi riil, false positive, dan false negative untuk pertanggungjawaban akademis/laporan magang.
14. 🔲 **Langkah 4.3 — Penyusunan Laporan Teknis, User Manual & Serah Terima Repo:**
    - Penulisan laporan akhir berstandar IEEE, panduan operasional pengguna, dan transfer knowledge ke tim PLN UP3 Mojokerto.

## 💡 Section 2: Ideas to Discuss (Log Ide & Keputusan Rekayasa)

_Log ide abadi. Jangan pernah menghapus ide di section ini. Gunakan sebagai arsip evolusi pemikiran tim._

### [Status: TERTETAPKAN] Pemilihan Nama & Identitas Proyek "ARGUS"

- **Tanggal & Inisiator:** `[18-09-2026]` - Pascol
- **Konteks & Latar Belakang:** Proyek audit foto kelainan bacaan LBKB PLN membutuhkan identitas dan nama sandi (_codename_) yang berwibawa, mencerminkan akurasi tinggi, serta selevel dengan proyek GAPIN.
- **Keputusan Rekayasa:** Dipilih nama **ARGUS** _(Automated Recognition & Grid Utility Surveillance)_, terinspirasi dari Argus Panoptes—raksasa bermata seratus dalam mitologi Yunani yang tidak pernah tidur dan bertugas mengawasi bukti dengan kewaspadaan penuh.

### [Status: TERTETAPKAN] Pemilihan Arsitektur Cascading Multi-Tier Pipeline vs Single-Model VLM

- **Tanggal & Inisiator:** `[18-09-2026]` - Pascol
- **Konteks & Latar Belakang:** Menimbang apakah sistem harus 100% menggunakan VLM (seperti skrip lama `Tanpa judul.txt`) atau 100% OpenCV/OCR lokal, atau gabungan keduanya.
- **Keputusan Rekayasa:** Mengesahkan arsitektur **Cascading Multi-Tier Pipeline**:
  1. _Tier 1 (OpenCV):_ Deteksi blur instan (<5 ms, gratis). Foto rusak langsung disaring di awal.
  2. _Tier 2 (ZBar):_ Deteksi barcode nomor seri meteran (100% akurat secara matematis via checksum, <30 ms, gratis).
  3. _Tier 3 (VLM via NVIDIA API):_ Hanya dipanggil sebagai _fallback_ untuk sisa foto $\pm 20-30\%$ (kasus rintangan pagar, tulisan spidol, barcode rusak).
- **Justifikasi Keuntungan:** Menghemat 70–80% kuota API internet, memangkas waktu pemrosesan ribuan foto dari berjam-jam menjadi hitungan menit, dan mengeliminasi risiko halusinasi angka pada foto ber-barcode.

### [Status: TERTETAPKAN] Penolakan Pelatihan Model dari Nol (No Re-Training Trap) & Klarifikasi Peran YOLO

- **Tanggal & Inisiator:** `[18-09-2026]` - Pascol
- **Konteks & Latar Belakang:** Pertimbangan apakah perlu melatih model Deep Learning sendiri (CNN / ANN / YOLO) untuk 8.000 foto.
- **Keputusan Rekayasa:**
  1. **Tolak Training dari Nol:** Tidak ada dataset berlabel (_ground truth_) di awal. Melakukan anotasi manual ribuan foto hanya untuk training model klasifikasi dasar adalah pemborosan waktu magang yang tidak rasional.
  2. **YOLO Belum Dibutuhkan di Awal:** YOLO adalah model _Object Detection_ (pencari kotak koordinat), bukan pembaca teks/barcode. Barcode scanner ZBar sudah mampu mendeteksi dan membaca barcode di seluruh bidang citra tanpa perlu diajari kotak koordinat oleh YOLO. YOLO hanya akan dipertimbangkan jika di masa depan terdapat kebutuhan lokalisasi mika meteran ekstrem.

### [Status: TERTETAPKAN] Penolakan Stempel Karet Berbasis Kolom Excel (Anti-Fraud Field Validation)

- **Tanggal & Inisiator:** `[18-09-2026]` - Pascol
- **Konteks & Latar Belakang:** Diskusi mengenai apakah foto kelainan rintangan (pagar/pintu tutup) bisa langsung diklasifikasikan sebagai "Sesuai" hanya dengan membaca kolom teks `KODE LBKB` di Excel tanpa memvalidasi fotonya.
- **Keputusan Rekayasa:** DILARANG KERAS. Fungsi audit LBKB di PLN bertujuan membongkar kelalaian/manipulasi oknum petugas catat meter yang mengunggah foto aspal jalan, tanah, jok motor, atau dinding kosong saat melaporkan rumah tutup. Sistem ARGUS wajib memvalidasi citra secara visual (deteksi counter fisik meteran via Stage 1 YOLO atau deteksi ketiadaan objek `FAIL_COUNTER_NOT_FOUND`) untuk mencegah lolosnya foto manipulasi/fraud.

### [Status: TERTETAPKAN] Validasi Akademik Arsitektur Cascading Multi-Tier & Enhancement Preprocessing

- **Tanggal & Inisiator:** `[26-09-2026]` - Pascol
- **Konteks & Latar Belakang:** Meninjau secara ketat validitas keputusan teknis OpenCV + ZBar + VLM di hadapan literatur ilmiah internasional sebelum melangkah ke fase pembuatan.
- **Keputusan Rekayasa:**
  1. **Konfirmasi Ilmiah (MDPI 2023, VFAST 2024, CMC 2023, IEEE 2024, Theseus 2024):** Arsitektur Cascading Multi-Tier terbukti sebagai _pattern_ dominan industri utilitas untuk pemrosesan skala besar di perangkat tanpa GPU khusus. Menghasilkan penghematan biaya API hingga 70-80% dan memangkas waktu batch dari >3 jam menjadi belasan menit.
  2. **ROI-Focused Laplacian:** Laplacian Variance wajib dievaluasi pada Region of Interest (area meteran) agar tekstur kasar background (dinding, tanah, aspal) tidak memicu _false sharpness_ pada foto meteran yang buram.
  3. **CLAHE Preprocessing untuk ZBar:** Mengintegrasikan _Contrast Limited Adaptive Histogram Equalization_ dan binarisasi adaptif guna mendongkrak _hit-rate_ ZBar menghadapi foto meter berdebu atau terpapar silau (_glare_) pantulan mika.
  4. **Dokumen Resmi:** Seluruh sintesis bukti riset dan format sitasi APA diarsipkan di [`Docs/ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md).

### [Status: TERTETAPKAN] Standardisasi Metodologi MLLC & 7 Langkah Penyempurnaan Roadmap

- **Tanggal & Inisiator:** `[26-09-2026]` - Pascol
- **Konteks & Latar Belakang:** Meninjau apakah langkah-langkah kerja proyek ARGUS sudah sesuai standar metodologi rekayasa perangkat lunak dan visi komputer internasional (ISO/IEC/IEEE 12207 & Machine Learning Life Cycle).
- **Keputusan Rekayasa:**
  1. **Konfirmasi Metodologi:** Mengadopsi kerangka kerja _Machine Learning Life Cycle (MLLC)_ dipadukan dengan _Agile-Iterative SDLC_.
  2. **Pengesahan 7 Langkah Penyempurnaan Roadmap:**
     - _Langkah 1.1:_ Organisasi Folder Sampel Terstruktur 5 Skenario (A-E) untuk reproducibility pengujian.
     - _Langkah 1.3:_ Evaluasi Preprocessing ZBar Bertahap (3 Uji: Baseline, CLAHE, Full Otsu/Morph) untuk data komparatif laporan ilmiah.
     - _Langkah 1.4:_ Arsitektur System Prompt VLM 4-Layer (Persona, Task, Chain-of-Thought, JSON Output) + Few-Shot fallback.
     - _Langkah 1.5:_ Dokumentasi Benchmark & Penguncian Threshold Resmi ke RULEBOOK.md dan .env sebelum masuk Fase 2.
     - _Langkah 2.1:_ Desain Kontrak Data Formal (`ImageSignal` & `AuditVerdict`) untuk mencegah inkonsistensi interface antar modul.
     - _Langkah 2.4:_ Evaluasi Metrik Ganda Komprehensif (Precision, Recall, F1-Score, Barcode Hit-Rate, Cost Saving) guna mencegah _accuracy paradox_ pada kasus fraud.
     - _Langkah 4.2:_ Ground Truth Sampling 100 Baris acak terverifikasi manual bersama pengawas PLN sebagai basis pengujian validitas ilmiah laporan akhir.
  3. **Dokumen Roadmap Resmi:** Seluruh tahapan dan justifikasi literatur diarsipkan di [`Docs/ARGUS_Methodology_Roadmap.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Methodology_Roadmap.md).

### [Status: TERTETAPKAN] Arsitektur Hybrid Multi-Tier: Sinergi YOLO-Seg + Warp + PaddleOCR + YOLO-Cls & VLM Fallback

- **Tanggal & Inisiator:** `[05-10-2026]` - Pascol
- **Konteks & Latar Belakang:** Menjawab kebutuhan membaca angka stand kWh 7-segment pada display LCD yang sering diambil dari sudut miring, meredam silau pantulan matahari, serta mengklasifikasikan foto rintangan (pagar, rumah tutup, fraud aspal) tanpa memboroskan kuota VLM dan menghindari halusinasi angka.
- **Keputusan Rekayasa:**
  1. **Tier 1 (Gatekeeper Blur):** OpenCV Laplacian ROI menyaring foto blur/rusak dalam <5 ms secara offline.
  2. **Tier 2A (Nomor Seri):** ZBar Barcode Scanner + CLAHE membaca nomor seri 11 digit secara deterministik (checksum 100%).
  3. **Tier 2B (Stand LCD Sudut Miring):** YOLOv8-Seg (deteksi 4 sudut LCD) $\rightarrow$ `cv2.warpPerspective` (menyetrika gambar miring jadi datar) $\rightarrow$ CLAHE $\rightarrow$ PaddleOCR / CRNN membaca angka kWh secara lokal (offline, 0 token, 30–50 ms).
  4. **Tier 2C (Klasifikasi Rintangan Lokal):** YOLOv8-Cls / MobileNetV3 mengenali 5 kategori rintangan lapangan secara lokal.
  5. **Tier 3 (Jaring Pengaman Anti-Fraud Lokal & YOLO-Cls):** Menggunakan verifikasi ketiadaan dial counter (`FAIL_COUNTER_NOT_FOUND`) sebagai proteksi fraud langsung. Pelatihan model klasifikasi rintangan lokal (YOLO-Cls) di-HOLD menunggu dataset lapangan dari PLN UP3 Mojokerto. Seluruh VLM cloud dieliminasi total.
  6. **Tier 4 (Decision Engine):** Menuliskan hasil ke `STAN_BACA`, mencocokkan vs `STAN_METER`, dan mengeluarkan vonis audit resmi PLN.
- **Dokumen Resmi:** [`Docs/ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md) & [`Docs/ARGUS_Methodology_Roadmap.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Methodology_Roadmap.md).

### [Status: TERTETAPKAN] Two-Stage Local YOLO Digit Reader & Penguncian No-Flip Hyperparameters

- **Tanggal & Inisiator:** `[23-10-2026]` - Pascol
- **Konteks & Latar Belakang:** Pelatihan YOLOv8s pada digit angka meteran melonjak dari baseline ~75% menjadi 96.1% mAP@50 (Precision 94.6%, Recall 92.8%, latensi 4.2 ms) di GPU RTX 4060 lokal.
- **Keputusan Rekayasa:**
  1. Mengunci arsitektur Two-Stage: Stage 1 (`meter_counter_detector.pt`) memotong kotak dial/counter; Stage 2 (`digit_ocr_detector.pt`) membaca digit angka.
  2. DILARANG KERAS menggunakan `fliplr` atau `flipud` pada dataset angka (horizontal flip membalik angka `2, 3, 5, 6, 7`, merusak representasi konvolusi).

### [Status: TERTETAPKAN] Quality & Glare Gatekeeper (Pencegahan Lolosnya Angka Bodong Kasus Sampel #6)

- **Tanggal & Inisiator:** `[23-10-2026]` - Pascol
- **Konteks & Latar Belakang:** Pada Sampel #6, silau matahari ekstrem menutupi 4 digit meteran analog dan hanya menyisakan 1 angka ('6') berkontras tinggi. Pipeline naif langsung meng-output "6" sebagai stand billing PLN dengan confidence tinggi.
- **Keputusan Rekayasa:**
  1. Pasang Glare Masking (HSV: V > 240, S < 30) pada crop counter box. Jika area silau > 20%, proses langsung dihentikan dan divonis `ANOMALI_GLARE_TERHALANG`.
  2. Strict Sequence Validator: Meter analog wajib mendeteksi deretan 4–6 digit kontinu. Dilarang keras meloloskan angka sebatang kara/parsial ke database penagihan.

### [Status: TERTETAPKAN] Penolakan Pembacaan Angka Digital Menggunakan VLM & Arsitektur Unified 11-Class ('dot')

- **Tanggal & Inisiator:** `[23-10-2026]` - Pascol
- **Konteks & Latar Belakang:** Menolak keras melempar pembacaan angka meter digital (Kasus Sampel #8) ke VLM untuk menghemat kuota token API dan mencegah latensi tinggi.
- **Keputusan Rekayasa:**
  1. Pembacaan meter digital sepenuhnya diselesaikan lokal tanpa API eksternal demi zero-token cost dan kecepatan tinggi.
  2. Pembacaan meter digital dituntaskan secara lokal dengan menyatukan kelas angka `0-9` + titik desimal `dot` (11 kelas) dalam 1 model YOLO tunggal (4.2 ms).
  3. Logika desimal PLN: Mengurutkan sumbu X, mengambil angka sebelum `dot` sebagai stand tagih resmi, dan mengabaikan desimal di belakang koma.

### [Status: TERTETAPKAN] Strategi Deployment Dual-Mode (.exe untuk Demo, LAN Server untuk Kantor) & MLOps Active Learning Flywheel

- **Tanggal & Inisiator:** `[31-10-2026]` - Pascol
- **Konteks & Latar Belakang:** Menentukan cara operasional tim PLN menjalankan sistem ARGUS (apakah diinstal per laptop atau terpusat di server kantor), serta memitigasi _data drift_ / penurunan akurasi model seiring masuknya meteran tipe baru.
- **Keputusan Rekayasa:**
  1. **Deployment Fase Demo:** Membungkus backend FastAPI + YOLO menjadi standalone `.exe` agar portabel dan mandiri untuk demonstrasi langsung ke manajemen PLN.
  2. **Deployment Fase Produksi:** Menjalankan ARGUS di 1 PC Server GPU LAN kantor UP3 (`192.168.x.x:8000`). Seluruh laptop petugas cukup memasang Userscript Tampermonkey di Google Chrome tanpa perlu install Python maupun GPU.
  3. **MLOps Active Learning Flywheel:** Menolak _naive unsupervised online learning_ (mencegah _catastrophic forgetting_ & _model poisoning_). Menerapkan _Human-in-the-Loop_: setiap kali petugas mengoreksi kasus kuning (🟡), data otomatis tersimpan di `data/hard_cases/` sebagai dataset fine-tuning model berkala (V4, V5).
  4. **Penolakan Model Generative Super-Resolution:** Menolak model generatif (seperti ESRGAN) demi mencegah halusinasi geometri angka (`6` jadi `8` atau `5` jadi `2`). Mengandalkan CLAHE dan Letterbox Resize native YOLOv8s.
  5. **Format Excel Audit & Penamaan Unik:** Mengunci skema penamaan file berbasis Primary Key `{IDPEL}_{PERIODE}_{STATUS}.jpg` dan relative hyperlink dalam berkas ZIP terpadu.
- **Dokumen Resmi:** [`Docs/STRATEGI_ARSITEKTUR_DAN_DEPLOYMENT.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/STRATEGI_ARSITEKTUR_DAN_DEPLOYMENT.md).

### [Status: TERTETAPKAN] Eliminasi Total Dependensi VLM Cloud & Penetapan Zero-Counter Anti-Fraud Heuristik
- **Tanggal & Inisiator:** `[02-11-2026]` - Pascol
- **Konteks & Latar Belakang:** Ketergantungan pada VLM Cloud (seperti NVIDIA NIM) terbukti rentan terhadap kedaluwarsa API key, latency network, dan endpoint yang tidak stabil untuk kebutuhan operasional harian PLN. Sementara itu, melatih model klasifikasi rintangan lokal (YOLOv8-Cls) membutuhkan ribuan anotasi gambar (*Labeling Trap*) yang bervariasi tinggi di Indonesia (pagar, jok motor, aspal).
- **Keputusan Rekayasa:**
  1. **Eliminasi Total VLM:** Seluruh dependensi API cloud ditiadakan dari arsitektur inti ARGUS. Sistem menjadi 100% *pure local & offline*.
  2. **YOLOv8-Cls di-HOLD:** Klasifikasi rintangan lokal ditangguhkan sampai tersedianya arsip dataset internal rintangan dari PLN UP3 Mojokerto.
  3. **Jaring Pengaman Anti-Fraud Heuristik (Zero-Counter):** Penolakan fraud saat ini ditangani secara deterministik oleh Stage 1 YOLO (`FAIL_COUNTER_NOT_FOUND`). Foto aspal, tanah, atau jok motor secara otomatis tidak memiliki kotak dial meteran, sehingga sistem menolak menerbitkan stand tagih dan me-routing langsung ke antrean review manual. Tagihan PLN 100% aman dari manipulasi tembak stand!

### [Status: TERTETAPKAN] Arsitektur Dashboard Mandiri ARGUS V5 & 5 Solusi Optimasi Skala Enterprise
- **Tanggal & Inisiator:** `[12-11-2026]` - Benedictus Pascal
- **Konteks & Latar Belakang:** Mengaudit 7.470+ foto di browser secara serial & merender seluruh baris DOM sekaligus menyebabkan browser lambat dan rawan duplikasi data, sementara tim PLN juga membutuhkan fleksibilitas audit baik dengan maupun tanpa file rekap ACMT.
- **Keputusan Rekayasa:**
  1. **Dual-Mode Upload + Anti-Duplikasi:** Memisahkan unggah folder/file dari tombol eksekusi `Mulai Audit Batch` dengan dialog konfirmasi duplikat (`Skip` / `Overwrite`).
  2. **Auto-Pairing Rekap ACMT & Mode Mandiri:** Menambahkan parser multi-sheet `/api/parse-acmt-excel` dan sakelar mode `AUTO` / `MANDIRI` / `KOMPARASI`.
  3. **Enterprise Virtual Slicing + Quick Sort:** Membatasi render aktif 25/50/100 baris/halaman menggunakan `URL.createObjectURL(file)`, persistensi sesi (`session_store.js`), serta pengurutan kolom cepat.
  4. **Worker Pool Paralel GPU & Packaging `--onedir`:** Mengalirkan batch inferensi secara paralel sesuai kemampuan GPU/CPU (`/api/system-info`) dan membungkus aplikasi siap pakai lewat `build_exe.py` ke `dist/ARGUS/ARGUS.exe`.

### [Status: TERTETAPKAN] Human-in-the-Loop V5, Smart Baseline Un-Edit & Celengan Feedback AI (Target 1.000 Kasus)
- **Tanggal & Inisiator:** `[13-11-2026]` - Benedictus Pascal
- **Konteks & Latar Belakang:** Auditor membutuhkan stasiun verifikasi cepat tanpa memperlebar tabel 13 kolom, hasil edit yang dikembalikan ke nilai awal tidak boleh terus tercatat sebagai koreksi, dan kasus sulit perlu dikumpulkan bertahap lintas sesi/bulan tanpa membanjiri laporan dinas PLN maupun hilang saat browser di-refresh/reset.
- **Keputusan Rekayasa:**
  1. **Smart Baseline Comparison:** Setiap baris menyimpan snapshot asli (`data-orig-stan-lap`, `data-orig-argus`, `data-orig-status`); label `Dikoreksi` otomatis hilang dan entri dihapus dari staging vault bila nilai dikembalikan persis ke baseline dan Catatan AI kosong.
  2. **Pemisahan Catatan PLN vs Catatan Model AI:** Tabel tetap 13 kolom; `Catatan Evaluasi Model AI` ditempatkan di Modal Pratinjau dengan 3 tombol cepat *toggleable* (`Salah Baca Angka`, `Digit Terpotong`, `Rolling Meleset`), tombol clear (`×`), dan lencana robot ungu `Catatan AI` pada tabel.
  3. **Navigasi Inspector Filter/Sort-Aware & Celengan AI Persisten:** `inspectPhoto` / `navigateInspector` mengikuti baris hasil filter & sortir aktif; koreksi otomatis tersinkron ke `data/feedback_staging/`, terkemas otomatis menjadi 1 berkas ZIP (`.xlsx` Master + `feedback_manifest.csv` + foto + pre-label YOLO) di `data/feedback_releases/` tiap genap 1.000 kasus unik, dan dapat dipantau/dikemas manual lewat `#modal-vault-manager`.

---

## 🩻 Section 3: Audit Plan (The Ruthless Audit)

### 🟢 The Good

- `[18-09-2026]` **Holy Trinity Documentation Ready:** Berkas `README.md`, `RULEBOOK.md`, dan `WHITEBOARD.md` untuk Project ARGUS telah resmi dibentuk dan disinkronkan dengan standar korporat PLN UP3 Mojokerto.
- `[18-09-2026]` **Ketersediaan Data Master Lengkap:** Terdapat 8.127 baris data pada sheet `Detail` Excel dan 7.470 berkas citra asli beresolusi $540 \times 960$ di folder `DOkumentasi LBKB/`.
- `[18-09-2026]` **Infrastruktur API Key Terpasang:** NVIDIA NIM API Key aktif (`API=nvapi-...`) terkonfirmasi di `.env`.
- `[26-09-2026]` **Fondasi Riset Ilmiah Kuat & Tervalidasi:** Arsitektur Cascading Multi-Tier telah divalidasi dan didokumentasikan di [`Docs/ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md) dengan dukungan 6 jurnal akademik internasional terindeks.
- `[23-10-2026]` **Lonjakan Akurasi Digit YOLOv8s ke 96.1% mAP@50:** Pelatihan 30 epoch di GPU RTX 4060 tanpa flip horizontal menghasilkan Precision 94.6% dan Recall 92.8% dengan latensi hanya 4.2 ms/citra.
- `[23-10-2026]` **Two-Stage Pipeline Sukses 100% pada Meter Analog Jelas:** Uji end-to-end pada sampel analog jelas membaca 5 digit sempurna (`00000`, `07501`, `05013`, `14244`, `04790`, `00211`).
- `[12-11-2026]` **Modularisasi Backend & Dashboard Mandiri V5 Operasional:** Seluruh pipeline (`src/vision_ai/`), API (`src/api/`), auto-pairing ACMT, Virtual Pagination, Worker Pool GPU, dan ekspor Excel resmi ber-hyperlink berjalan terpadu, lengkap dengan distribusi standalone `dist/ARGUS/ARGUS.exe`.
- `[13-11-2026]` **Human-in-the-Loop V5 & Celengan Feedback AI 1.000 Kasus Tuntas:** Modal Inspector HD (zoom/pan, hotkey `1..5`, navigasi filter/sort-aware, tema vonis dinamis), Smart Baseline Un-Edit, pemisahan Catatan PLN vs Catatan AI (`Salah Baca Angka`, `Digit Terpotong`, `Rolling Meleset`), serta staging vault persisten + `#modal-vault-manager` lulus verifikasi `TestClient` dan `node --check`.

### 🟡 The Bad

- `[18-09-2026]` **Userscript Eksisting Masih Pascabayar:** Kode pada `Tanpa judul.txt` masih berorientasi pada pembacaan stand kWh meter pascabayar 5 digit dan belum memiliki logika penanganan LBKB prabayar / foto pagar.
- `[26-09-2026]` **Background Clutter Mengelabui Laplacian:** Menghitung blur pada keseluruhan citra berisiko _false negative blur_ akibat tekstur dinding/aspal. Harus dikalibrasi dengan cropping ROI meteran (threshold 80–120).
- `[23-10-2026]` **Sampel #8 (Meter Digital LCD) Belum Mengenali Desimal:** Angka terbaca parsial `2`, `6`, `3` karena dataset lama belum melabeli karakter titik/koma (`dot`) dan segmen angka LCD terpotong refleksi kaca.

### 🔴 The Ugly

- `[18-09-2026]` **Kualitas Citra Lapangan Sangat Beragam:** Adanya pantulan silau matahari (_glare_) pada mika penutup meteran dan debu tebal pada stiker barcode berpotensi menurunkan _hit-rate_ pembacaan barcode jika tidak dilengkapi pra-pemrosesan citra yang tangguh (dimitigasi dengan CLAHE).
- `[23-10-2026]` **Sampel #6 (Silau Ekstrem Meloloskan Angka Tunggal):** Glare matahari menghapus 4 digit analog, namun model mendeteksi 1 digit ('6') dengan confidence 85% dan naif meloloskannya ke billing tanpa gatekeeper urutan digit.

---

## 📋 Issue & Solution Log

> [!NOTE]
> **Prinsip Audit Trail (Immutable Log):**
> Seluruh catatan masalah (*issues*) dan solusinya bersifat abadi dan **tidak pernah dihapus** sekalipun statusnya sudah selesai (`DONE`). Log ini berfungsi sebagai bukti rekam jejak rekayasa (*engineering track record*), transparansi audit, dan referensi pencegahan regresi. Setiap rekan tim yang menemukan atau menyelesaikan masalah wajib mencantumkan namanya pada kolom **PIC**.


| Level | Date Logged  | Masalah (Issue) | Solusi yang Diambil / Rencana Solusi | PIC | Status | Date Resolved |
| :---: | :----------- | :--- | :--- | :---: | :---: | :-----------: |
|  🔴   | `18-09-2026` | **Mismatch Target Model Lama:** Userscript `Tanpa judul.txt` menginstruksikan AI mengabaikan nomor seri meter (_"Ignore the meter serial number"_) dan mencocokkan angka ke `stan_baca`. | Merombak total system prompt VLM dan parser validasi agar mengekstrak nomor seri meteran fisik 11 digit dan IDPEL 12 digit untuk kasus LBKB token/prabayar. | Pascol | `PLANNED` | - |
|  🟢   | `18-09-2026` | **Latensi Tinggi & Kuota Cloud API (8.000 Citra):** Memproses citra via API Cloud memakan waktu lama dan rentan terhadap limit/expired key. | Mengeliminasi total VLM Cloud. Mengadopsi arsitektur 100% Local Pipeline (OpenCV + YOLOv8s) yang berjalan offline di GPU RTX dalam 4.2 ms. | Pascol | `DONE` | `02-11-2026` |
|  🟢   | `18-09-2026` | **Resiko Halusinasi Digit Angka pada Model AI:** AI generatif kerap berhalusinasi atau salah membaca angka mirip. | Angka dibaca 100% lokal oleh YOLOv8s 11-Class + Heuristic Strict Sequence & Gap Validator (mAP50 93.7%, zero hallucination). | Pascol | `DONE` | `02-11-2026` |
|  🟢   | `26-09-2026` | **Background Clutter Mengacaukan Blur Score:** Dinding kasar/aspal memberi skor Laplacian tinggi pada citra meteran yang buram. | Menerapkan evaluasi Laplacian pada Region of Interest (ROI 60% tengah meteran) serta crop dial box. Terintegrasi di `pipeline.py`. | Pascol | `DONE` | `02-11-2026` |
|  🟡   | `26-09-2026` | **Silau Mika & Debu Lapangan pada Barcode:** ZBar gagal mendeteksi garis barcode akibat kontras rendah. | Menambahkan preprocessing citra dengan CLAHE dan binarisasi adaptif Otsu sebelum ZBar. Ditunda sementara menunggu diskusi PLN. | Pascol | `HOLD (PLN)` | - |
|  🟢   | `26-09-2026` | **Ketiadaan Basis Teori & Validasi Ilmiah:** Perlunya justifikasi akademis dan perbandingan model sebelum masuk fase pembuatan. | Melakukan riset komparasi 6 jurnal internasional terindeks dan mendokumentasikan di `Docs/ARGUS_Research_Validation.md`. | Pascol | `DONE` | `26-09-2026` |
|  🟢   | `18-09-2026` | **Inisialisasi Tata Kelola Repositori:** Ketiadaan acuan aturan kerja dan pelacak progres pada folder kerja `ARGUS/`. | Menyusun Holy Trinity: `README.md` (arsitektur), `RULEBOOK.md` (konstitusi hukum), dan `WHITEBOARD.md` (roadmap & audit log). | Pascol | `DONE` | `18-09-2026` |
|  🟢   | `23-10-2026` | **Akurasi Model Digit Rendah (~75% di Teammate):** Pelatihan sebelumnya terjebak flip horizontal default yang merusak geometri angka asimetris (`2, 3, 5, 6, 7`). | Menonaktifkan `fliplr` dan `flipud` di Roboflow & YOLO. Akurasi melonjak ke 96.1% mAP@50 (latensi 4.2 ms). | Pascol | `DONE` | `23-10-2026` |
|  🟢   | `23-10-2026` | **Kasus Sampel #6: Glare Silau Menghasilkan Angka Sebatang Kara ("6"):** Silau matahari menghapus 4 digit analog, tapi 1 digit lolos dengan confidence tinggi dan diteruskan ke billing. | Menerapkan Tier 1 Glare Masking (HSV) + Strict Sequence Validator (minimal 5 digit kontinu untuk analog). Tolak pembacaan parsial. | Pascol | `DONE` | `31-10-2026` |
|  🟢   | `23-10-2026` | **Kasus Sampel #8: Meter Digital Dinamis & Desimal Belum Terbaca:** Angka digital memiliki koma dan panjang dinamis (`20,163` terbaca `2, 6, 3`), berisiko memboroskan token jika dibuang ke VLM. | Memperluas dataset model lokal dengan kelas `dot` (11 kelas) + Inter-Digit Gap Detector. Berhasil menangkap anomali dan me-routing ke 🟡 Triage Manual. | Pascol | `DONE` | `31-10-2026` |
|  🟢   | `31-10-2026` | **Packaging Standalone Demo (.exe) & Integrasi Web Extension:** Kebutuhan demonstrasi mandiri ke manajemen PLN tanpa ketergantungan konfigurasi Python laptop dinas. | Membungkus backend FastAPI + YOLO pipeline menjadi standalone `.exe` (PyInstaller `--onedir`) di `dist/ARGUS/ARGUS.exe` beserta Dashboard Web Mandiri & launcher bebas freeze QuickEdit. | Benedictus Pascal | `DONE` | `13-11-2026` |
|  🟢   | `12-11-2026` | **Skala Ribuan Foto & Duplikasi Antrean di Dashboard Web:** Merender 7.475 baris + Base64 membebani RAM browser dan eksekusi batch serial lambat. | Menerapkan Enterprise Virtual Pagination (25/50/100/ALL), `URL.createObjectURL`, anti-duplikasi foto, auto-pairing ACMT, quick sort, serta Worker Pool paralel GPU/CPU. | Benedictus Pascal | `DONE` | `12-11-2026` |
|  🟢   | `13-11-2026` | **Evaluasi Model AI, Smart Baseline Un-Edit & Risiko Hilangnya Feedback Saat Refresh/Reset:** Mengembalikan nilai edit masih tertanda `Dikoreksi`, catatan AI berisiko mengotori Excel dinas PLN, serta kasus sulit hilang saat tabel di-reset. | Menerapkan Smart Baseline Un-Edit, memisahkan Catatan AI ke modal pratinjau (3 chip toggle + tombol clear), memperbaiki navigasi modal filter/sort-aware + paginasi `goToPage()`, dan membangun Celengan Feedback AI persisten (target 1.000 kasus + `#modal-vault-manager`). | Benedictus Pascal | `DONE` | `13-11-2026` |
