# 🎯 Section 1: Current Grand Plan
> [!IMPORTANT]
> **Fokus Utama Saat Ini:** Tahap 1: Pengujian Sampel Nyata (Proof of Concept) pada 15-20 Foto Citra Lapangan, Benchmark Algoritma Blur ROI (OpenCV Laplacian), Validasi Barcode Scanner dengan CLAHE (ZBar), dan Pemetaan Prompt Semantik VLM untuk Kasus LBKB PLN.
> **Affected Areas:** Folder Citra `DOkumentasi LBKB/`, File Master `12 LBKB Billing Rek 12 2025 copy+foto.xlsx`, Script Portal `Tanpa judul.txt`, Dokumen Riset [`Docs/ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md), Roadmap Metodologi [`Docs/ARGUS_Methodology_Roadmap.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Methodology_Roadmap.md), dan Skrip Pengujian Python.
> **Dokumentasi Resmi:** [`README.md`](file:///d:/Hooh_Lah/PLN/ARGUS/README.md), [`RULEBOOK.md`](file:///d:/Hooh_Lah/PLN/ARGUS/RULEBOOK.md), [`ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md), [`ARGUS_Methodology_Roadmap.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Methodology_Roadmap.md).
> **Success Criteria:** 
> 1. Terbuktinya metrik Laplacian Variance pada ROI dalam memisahkan foto buram/rusak dari foto layak audit pada sampel foto lapangan $\pm 20$ citra. *(Status: IN PROGRESS)*
> 2. Terverifikasinya pembacaan nomor meteran 11 digit via Barcode Reader ZBar + CLAHE secara otomatis tanpa halusinasi pada KWH Meter prabayar bertipe stiker barcode. *(Status: IN PROGRESS)*
> 3. Terumuskannya *system prompt* VLM (NVIDIA NIM LLaMA 3.2 11B Vision) berbasis 4-layer architecture yang menghasilkan output JSON deterministik untuk mendeteksi rintangan pagar terkunci, pintu rumah tutup, dan foto manipulasi/fraud. *(Status: PLANNED)*
> 4. Sinkronisasi logika Decision Engine dengan data kolom Excel sheet `Detail` (IDPEL, NAMA, KDBACA, KODE LBKB) menggunakan kontrak data formal (`ImageSignal` & `AuditVerdict`). *(Status: PLANNED)*
> 5. Evaluasi performa sistem berbasis metrik komprehensif (Precision, Recall, F1-Score, Barcode Hit-Rate, Cost Saving) dan validasi Ground Truth 100 sampel manual bersama PLN. *(Status: PLANNED)*
> 6. Eksekusi pengemasan ganda (*dual-mode packaging*): Userscript Browser ACMT (`web_extension/argus_evaluator.user.js`) dan Batch CLI Python (`src/pipeline.py`) untuk audit 8.000 foto. *(Status: PLANNED)*

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
     - `data/samples/A_barcode_jelas/` (KWH Meter prabayar stiker barcode ideal - baseline hit-rate)
     - `data/samples/B_barcode_terhambat/` (Silau mika, pantulan matahari, debu tebal - uji ketangguhan CLAHE)
     - `data/samples/C_teks_spidol/` (Pascabayar spidol / angka LCD - uji OCR semantik VLM)
     - `data/samples/D_rintangan_fisik/` (Pagar gembok, pintu tutup kode E & F - uji klasifikasi scene VLM)
     - `data/samples/E_foto_fraud/` (Aspal, jok motor, dinding kosong, blur ekstrem - uji deteksi anomali/fraud)
2. 🔲 **Langkah 1.2 — Benchmark Tier 1: Deteksi Blur OpenCV Laplacian (ROI-Focused):**
   - Menghitung $\text{Var}(L)$ pada area tengah ROI meteran (menghindari background clutter dinding/aspal).
   - Menguji perbandingan 3 threshold: 30, 80, 120.
   - Mengukur *False Rejection Rate* vs *False Acceptance Rate* untuk menentukan threshold optimal.
3. 🔲 **Langkah 1.3 — Benchmark Tier 2: Barcode Scanner ZBar + Preprocessing Bertahap (3 Tahap):**
   - Uji 1 (Baseline): Citra mentah langsung ke ZBar.
   - Uji 2 (CLAHE): Citra $\rightarrow$ Grayscale $\rightarrow$ CLAHE (`clipLimit=2.0-3.0`) $\rightarrow$ ZBar.
   - Uji 3 (Full Pipeline): Citra $\rightarrow$ Grayscale $\rightarrow$ CLAHE $\rightarrow$ Otsu Binarize $\rightarrow$ Morphological Clean $\rightarrow$ ZBar.
   - Mencatat kuantitatif peningkatan hit-rate & waktu komputasi (ms) untuk laporan ilmiah.
4. 🔲 **Langkah 1.4 — Formulasi System Prompt VLM 4-Layer (NVIDIA NIM LLaMA 3.2 Vision):**
   - Menyusun prompt dengan struktur 4-layer: (1) Persona PLN Auditor, (2) Task definition, (3) Chain-of-Thought reasoning, (4) Strict JSON-only output schema.
   - Menguji zero-shot vs few-shot (1-2 gambar referensi) pada kasus sulit non-barcode & fraud.
   - Mengintegrasikan regex fallback parser jika terjadi respon non-JSON.
5. 🔲 **Langkah 1.5 — Dokumentasi Benchmark & Penguncian Threshold Resmi:**
   - Merekam seluruh angka hasil benchmark di `WHITEBOARD.md` (Section 3).
   - Mengunci nilai `BLUR_THRESHOLD` optimal dan parameter CLAHE ke `RULEBOOK.md` dan `.env` sebagai Single Source of Truth sebelum melangkah ke Fase 2.

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

#### 🔹 FASE 3: Dual-Mode Packaging & Integrasi Operasional
10. 🔲 **Langkah 3.1 — Mode A: Script Batch Processing CLI Python (`src/pipeline.py`):**
    - Multi-threading untuk pemrosesan massal 7.470 foto secara cepat dan efisien di komputer kantor.
    - Ekspor output Excel terstruktur dengan kolom status audit, confidence, dan audit reason.
11. 🔲 **Langkah 3.2 — Mode B: Userscript Browser Tampermonkey (`argus_evaluator.user.js`):**
    - Integrasi langsung ke antarmuka web portal ACMT PLN (`portalapp.iconpln.co.id`).
    - Evaluasi inline per baris tabel foto kelainan dan sinkronisasi hasil audit.

#### 🔹 FASE 4: Pilot Test Skala Penuh, Evaluasi & Serah Terima
12. 🔲 **Langkah 4.1 — Pilot Run Penuh Dataset Rek 12 2025:**
    - Eksekusi pipeline pada seluruh 7.470 foto dokumentasi LBKB, memantau stabilitas latensi dan error rate.
13. 🔲 **Langkah 4.2 — Evaluasi Akurasi Ilmiah via Ground Truth Sampling (100 Baris Manual):**
    - Mengambil 100 sampel baris acak dari output ARGUS dan memverifikasinya secara manual bersama petugas PLN.
    - Menghitung akurasi riil, false positive, dan false negative untuk pertanggungjawaban akademis/laporan magang.
14. 🔲 **Langkah 4.3 — Penyusunan Laporan Teknis, User Manual & Serah Terima Repo:**
    - Penulisan laporan akhir berstandar IEEE, panduan operasional pengguna, dan transfer knowledge ke tim PLN UP3 Mojokerto.

## 💡 Section 2: Ideas to Discuss (Log Ide & Keputusan Rekayasa)
*Log ide abadi. Jangan pernah menghapus ide di section ini. Gunakan sebagai arsip evolusi pemikiran tim.*

### [Status: TERTETAPKAN] Pemilihan Nama & Identitas Proyek "ARGUS"
- **Tanggal & Inisiator:** `[18-09-2026]` - Pascol & Agent
- **Konteks & Latar Belakang:** Proyek audit foto kelainan bacaan LBKB PLN membutuhkan identitas dan nama sandi (*codename*) yang berwibawa, mencerminkan akurasi tinggi, serta selevel dengan proyek GAPIN.
- **Keputusan Rekayasa:** Dipilih nama **ARGUS** *(Automated Recognition & Grid Utility Surveillance)*, terinspirasi dari Argus Panoptes—raksasa bermata seratus dalam mitologi Yunani yang tidak pernah tidur dan bertugas mengawasi bukti dengan kewaspadaan penuh.

### [Status: TERTETAPKAN] Pemilihan Arsitektur Cascading Multi-Tier Pipeline vs Single-Model VLM
- **Tanggal & Inisiator:** `[18-09-2026]` - Pascol & Agent
- **Konteks & Latar Belakang:** Menimbang apakah sistem harus 100% menggunakan VLM (seperti skrip lama `Tanpa judul.txt`) atau 100% OpenCV/OCR lokal, atau gabungan keduanya.
- **Keputusan Rekayasa:** Mengesahkan arsitektur **Cascading Multi-Tier Pipeline**:
  1. *Tier 1 (OpenCV):* Deteksi blur instan (<5 ms, gratis). Foto rusak langsung disaring di awal.
  2. *Tier 2 (ZBar):* Deteksi barcode nomor seri meteran (100% akurat secara matematis via checksum, <30 ms, gratis).
  3. *Tier 3 (VLM via NVIDIA API):* Hanya dipanggil sebagai *fallback* untuk sisa foto $\pm 20-30\%$ (kasus rintangan pagar, tulisan spidol, barcode rusak).
- **Justifikasi Keuntungan:** Menghemat 70–80% kuota API internet, memangkas waktu pemrosesan ribuan foto dari berjam-jam menjadi hitungan menit, dan mengeliminasi risiko halusinasi angka pada foto ber-barcode.

### [Status: TERTETAPKAN] Penolakan Pelatihan Model dari Nol (No Re-Training Trap) & Klarifikasi Peran YOLO
- **Tanggal & Inisiator:** `[18-09-2026]` - Pascol & Agent
- **Konteks & Latar Belakang:** Pertimbangan apakah perlu melatih model Deep Learning sendiri (CNN / ANN / YOLO) untuk 8.000 foto.
- **Keputusan Rekayasa:**
  1. **Tolak Training dari Nol:** Tidak ada dataset berlabel (*ground truth*) di awal. Melakukan anotasi manual ribuan foto hanya untuk training model klasifikasi dasar adalah pemborosan waktu magang yang tidak rasional.
  2. **YOLO Belum Dibutuhkan di Awal:** YOLO adalah model *Object Detection* (pencari kotak koordinat), bukan pembaca teks/barcode. Barcode scanner ZBar sudah mampu mendeteksi dan membaca barcode di seluruh bidang citra tanpa perlu diajari kotak koordinat oleh YOLO. YOLO hanya akan dipertimbangkan jika di masa depan terdapat kebutuhan lokalisasi mika meteran ekstrem.

### [Status: TERTETAPKAN] Penolakan Stempel Karet Berbasis Kolom Excel (Anti-Fraud Field Validation)
- **Tanggal & Inisiator:** `[18-09-2026]` - Pascol & Agent
- **Konteks & Latar Belakang:** Diskusi mengenai apakah foto kelainan rintangan (pagar/pintu tutup) bisa langsung diklasifikasikan sebagai "Sesuai" hanya dengan membaca kolom teks `KODE LBKB` di Excel tanpa memvalidasi fotonya.
- **Keputusan Rekayasa:** DILARANG KERAS. Fungsi audit LBKB di PLN bertujuan membongkar kelalaian/manipulasi oknum petugas catat meter yang mengunggah foto aspal jalan, tanah, jok motor, atau dinding kosong saat melaporkan rumah tutup. VLM wajib memverifikasi bahwa citra yang diunggah benar-benar menampilkan pagar terkunci / rintangan fisik nyata.

### [Status: TERTETAPKAN] Validasi Akademik Arsitektur Cascading Multi-Tier & Enhancement Preprocessing
- **Tanggal & Inisiator:** `[26-09-2026]` - Pascol & Agent
- **Konteks & Latar Belakang:** Meninjau secara ketat validitas keputusan teknis OpenCV + ZBar + VLM di hadapan literatur ilmiah internasional sebelum melangkah ke fase pembuatan.
- **Keputusan Rekayasa:**
  1. **Konfirmasi Ilmiah (MDPI 2023, VFAST 2024, CMC 2023, IEEE 2024, Theseus 2024):** Arsitektur Cascading Multi-Tier terbukti sebagai *pattern* dominan industri utilitas untuk pemrosesan skala besar di perangkat tanpa GPU khusus. Menghasilkan penghematan biaya API hingga 70-80% dan memangkas waktu batch dari >3 jam menjadi belasan menit.
  2. **ROI-Focused Laplacian:** Laplacian Variance wajib dievaluasi pada Region of Interest (area meteran) agar tekstur kasar background (dinding, tanah, aspal) tidak memicu *false sharpness* pada foto meteran yang buram.
  3. **CLAHE Preprocessing untuk ZBar:** Mengintegrasikan *Contrast Limited Adaptive Histogram Equalization* dan binarisasi adaptif guna mendongkrak *hit-rate* ZBar menghadapi foto meter berdebu atau terpapar silau (*glare*) pantulan mika.
  4. **Dokumen Resmi:** Seluruh sintesis bukti riset dan format sitasi APA diarsipkan di [`Docs/ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md).

### [Status: TERTETAPKAN] Standardisasi Metodologi MLLC & 7 Langkah Penyempurnaan Roadmap
- **Tanggal & Inisiator:** `[26-09-2026]` - Pascol & Agent
- **Konteks & Latar Belakang:** Meninjau apakah langkah-langkah kerja proyek ARGUS sudah sesuai standar metodologi rekayasa perangkat lunak dan visi komputer internasional (ISO/IEC/IEEE 12207 & Machine Learning Life Cycle).
- **Keputusan Rekayasa:**
  1. **Konfirmasi Metodologi:** Mengadopsi kerangka kerja *Machine Learning Life Cycle (MLLC)* dipadukan dengan *Agile-Iterative SDLC*.
  2. **Pengesahan 7 Langkah Penyempurnaan Roadmap:**
     - *Langkah 1.1:* Organisasi Folder Sampel Terstruktur 5 Skenario (A-E) untuk reproducibility pengujian.
     - *Langkah 1.3:* Evaluasi Preprocessing ZBar Bertahap (3 Uji: Baseline, CLAHE, Full Otsu/Morph) untuk data komparatif laporan ilmiah.
     - *Langkah 1.4:* Arsitektur System Prompt VLM 4-Layer (Persona, Task, Chain-of-Thought, JSON Output) + Few-Shot fallback.
     - *Langkah 1.5:* Dokumentasi Benchmark & Penguncian Threshold Resmi ke RULEBOOK.md dan .env sebelum masuk Fase 2.
     - *Langkah 2.1:* Desain Kontrak Data Formal (`ImageSignal` & `AuditVerdict`) untuk mencegah inkonsistensi interface antar modul.
     - *Langkah 2.4:* Evaluasi Metrik Ganda Komprehensif (Precision, Recall, F1-Score, Barcode Hit-Rate, Cost Saving) guna mencegah *accuracy paradox* pada kasus fraud.
     - *Langkah 4.2:* Ground Truth Sampling 100 Baris acak terverifikasi manual bersama pengawas PLN sebagai basis pengujian validitas ilmiah laporan akhir.
  3. **Dokumen Roadmap Resmi:** Seluruh tahapan dan justifikasi literatur diarsipkan di [`Docs/ARGUS_Methodology_Roadmap.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Methodology_Roadmap.md).

---

## 🩻 Section 3: Audit Plan (The Ruthless Audit)

### 🟢 The Good
- `[18-09-2026]` **Holy Trinity Documentation Ready:** Berkas `README.md`, `RULEBOOK.md`, dan `WHITEBOARD.md` untuk Project ARGUS telah resmi dibentuk dan disinkronkan dengan standar korporat PLN UP3 Mojokerto.
- `[18-09-2026]` **Ketersediaan Data Master Lengkap:** Terdapat 8.127 baris data pada sheet `Detail` Excel dan 7.470 berkas citra asli beresolusi $540 \times 960$ di folder `DOkumentasi LBKB/`.
- `[18-09-2026]` **Infrastruktur API Key Terpasang:** NVIDIA NIM API Key aktif (`API=nvapi-...`) terkonfirmasi di `.env`.
- `[26-09-2026]` **Fondasi Riset Ilmiah Kuat & Tervalidasi:** Arsitektur Cascading Multi-Tier telah divalidasi dan didokumentasikan di [`Docs/ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md) dengan dukungan 6 jurnal akademik internasional terindeks.

### 🟡 The Bad
- `[18-09-2026]` **Userscript Eksisting Masih Pascabayar:** Kode pada `Tanpa judul.txt` masih berorientasi pada pembacaan stand kWh meter pascabayar 5 digit dan belum memiliki logika penanganan LBKB prabayar / foto pagar.
- `[26-09-2026]` **Background Clutter Mengelabui Laplacian:** Menghitung blur pada keseluruhan citra berisiko *false negative blur* akibat tekstur dinding/aspal. Harus dikalibrasi dengan cropping ROI meteran (threshold 80–120).

### 🔴 The Ugly
- `[18-09-2026]` **Kualitas Citra Lapangan Sangat Beragam:** Adanya pantulan silau matahari (*glare*) pada mika penutup meteran dan debu tebal pada stiker barcode berpotensi menurunkan *hit-rate* pembacaan barcode jika tidak dilengkapi pra-pemrosesan citra yang tangguh (dimitigasi dengan CLAHE).

---

## 📋 Issue & Solution Log

| Level | Date Logged | Masalah (Issue) | Solusi yang Diambil / Rencana Solusi | Status | Date Resolved |
| :---: | :--- | :--- | :--- | :--- | :---: |
| 🔴 | `18-09-2026` | **Mismatch Target Model Lama:** Userscript `Tanpa judul.txt` menginstruksikan AI mengabaikan nomor seri meter (*"Ignore the meter serial number"*) dan mencocokkan angka ke `stan_baca`. | Merombak total system prompt VLM dan parser validasi agar mengekstrak nomor seri meteran fisik 11 digit dan IDPEL 12 digit untuk kasus LBKB token/prabayar. | `PLANNED` | - |
| 🟡 | `18-09-2026` | **Latensi Tinggi & Kuota VLM untuk 8.000 Citra:** Memproses seluruh 8.000 citra via API VLM memakan waktu >3 jam dan berisiko terkena *rate limit*. | Menerapkan *Cascading Multi-Tier Pipeline*: OpenCV memfilter foto blur, ZBar membaca barcode nomor meter lokal gratis, dan VLM hanya memproses sisa 20-30% foto sulit. | `PLANNED` | - |
| 🟡 | `18-09-2026` | **Resiko Halusinasi Digit Angka pada VLM:** VLM kerap salah membaca angka mirip (misal `8` menjadi `3`) pada teks angka panjang 11 digit. | Mengutamakan ekstraksi barcode fisik via ZBar (yang memiliki verifikasi *checksum* 100% pasti) sebelum melempar citra ke VLM. | `PLANNED` | - |
| 🟡 | `26-09-2026` | **Background Clutter Mengacaukan Blur Score:** Dinding kasar/aspal memberi skor Laplacian tinggi pada citra meteran yang buram. | Menerapkan evaluasi Laplacian pada Region of Interest (ROI) tengah meteran, bukan full image. | `PLANNED` | - |
| 🟡 | `26-09-2026` | **Silau Mika & Debu Lapangan pada Barcode:** ZBar gagal mendeteksi garis barcode akibat kontras rendah. | Menambahkan preprocessing citra dengan CLAHE dan binarisasi adaptif Otsu sebelum ZBar. | `PLANNED` | - |
| 🟢 | `26-09-2026` | **Ketiadaan Basis Teori & Validasi Ilmiah:** Perlunya justifikasi akademis dan perbandingan model sebelum masuk fase pembuatan. | Melakukan riset komparasi 6 jurnal internasional terindeks dan mendokumentasikan di `Docs/ARGUS_Research_Validation.md`. | `DONE` | `26-09-2026` |
| 🟢 | `18-09-2026` | **Inisialisasi Tata Kelola Repositori:** Ketiadaan acuan aturan kerja dan pelacak progres pada folder kerja `ARGUS/`. | Menyusun Holy Trinity: `README.md` (arsitektur), `RULEBOOK.md` (konstitusi hukum), dan `WHITEBOARD.md` (roadmap & audit log). | `DONE` | `18-09-2026` |
