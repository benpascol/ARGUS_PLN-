# 🎯 Section 1: Current Grand Plan
> [!IMPORTANT]
> **Fokus Utama Saat Ini:** Tahap 1: Pengujian Sampel Nyata (Proof of Concept) pada 15-20 Foto Citra Lapangan, Benchmark Algoritma Blur ROI (OpenCV Laplacian), Validasi Barcode Scanner dengan CLAHE (ZBar), dan Pemetaan Prompt Semantik VLM untuk Kasus LBKB PLN.
> **Affected Areas:** Folder Citra `DOkumentasi LBKB/`, File Master `12 LBKB Billing Rek 12 2025 copy+foto.xlsx`, Script Portal `Tanpa judul.txt`, Dokumen Riset [`Docs/ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md), dan Skrip Pengujian Python.
> **Dokumentasi Resmi:** [`README.md`](file:///d:/Hooh_Lah/PLN/ARGUS/README.md), [`RULEBOOK.md`](file:///d:/Hooh_Lah/PLN/ARGUS/RULEBOOK.md), [`ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md).
> **Success Criteria:** 
> 1. Terbuktinya metrik Laplacian Variance pada ROI dalam memisahkan foto buram/rusak dari foto layak audit pada sampel foto lapangan $\pm 20$ citra. *(Status: IN PROGRESS)*
> 2. Terverifikasinya pembacaan nomor meteran 11 digit via Barcode Reader ZBar + CLAHE secara otomatis tanpa halusinasi pada KWH Meter prabayar bertipe stiker barcode. *(Status: IN PROGRESS)*
> 3. Terumuskannya *system prompt* VLM (NVIDIA NIM LLaMA 3.2 11B Vision) yang menghasilkan output JSON deterministik untuk mendeteksi rintangan pagar terkunci, pintu rumah tutup, dan foto manipulasi/fraud. *(Status: PLANNED)*
> 4. Sinkronisasi logika Decision Engine dengan data kolom Excel sheet `Detail` (IDPEL, NAMA, KDBACA, KODE LBKB). *(Status: PLANNED)*
> 5. Eksekusi pengemasan ganda (*dual-mode packaging*): Userscript Browser ACMT (`web_extension/argus_evaluator.user.js`) dan Batch CLI Python (`src/pipeline.py`) untuk audit 8.000 foto. *(Status: PLANNED)*

---

### 🚀 Roadmap Fase Pengembangan ARGUS:

#### 🔹 FASE 0: Validasi Ilmiah & Grounding Arsitektur [SELESAI ✅ — 26-09-2026]
- [x] **Riset Literatur & Komparasi Industri:** Validasi cascading pipeline vs Pure VLM vs Fine-tuned YOLO.
- [x] **Dokumentasi Ilmiah:** Penyusunan laporan validasi di [`Docs/ARGUS_Research_Validation.md`](file:///d:/Hooh_Lah/PLN/ARGUS/Docs/ARGUS_Research_Validation.md) dengan 6 sitasi jurnal terindeks (MDPI, IEEE, CMC).
- [x] **Identifikasi Mitigasi Teknis:** Penambahan strategi ROI cropping untuk Laplacian dan enhancement CLAHE untuk ZBar.

#### 🔹 FASE 1: Pengujian Empiris Sampel & Benchmarking (PoC Lapangan) [AKTIF 🚀]
1. 🔲 **Seleksi 15–20 Foto Sampel Representatif:** Memilih sampel foto dari `DOkumentasi LBKB/` yang mewakili 5 skenario:
   - (a) KWH Meter prabayar stiker barcode jelas
   - (b) KWH Meter dengan silau mika / debu lapangan
   - (c) KWH Meter pascabayar teks spidol / LCD
   - (d) Rintangan fisik lapangan (Pagar gembok / rumah tutup kode E & F)
   - (e) Foto blur ekstrem / manipulasi oknum (aspal, jok motor, dinding kosong).
2. 🔲 **Benchmark Deteksi Blur OpenCV (ROI-Focused):** Menguji varians Laplacian $\sigma^2$ pada crop area meteran dengan range threshold rekomendasi riset (80–120) agar background clutter tidak mengaburkan penilaian.
3. 🔲 **Benchmark Barcode Scanner ZBar + CLAHE:** Menguji hit-rate pembacaan barcode 11 digit pada citra mentah vs citra yang telah ditingkatkan kontrasnya dengan CLAHE.
4. 🔲 **Formulasi Prompt JSON VLM:** Menguji respon LLaMA 3.2 11B Vision via API Key NVIDIA NIM untuk kasus foto non-barcode dan rintangan fisik dengan output pure JSON.

#### 🔹 FASE 2: Perancangan Core Decision Engine & Arbitrase Logika
5. 🔲 **Penyusunan Modul Arbitrase Keputusan:** Membangun engine yang memetakan sinyal visual (Blur, Barcode, VLM) terhadap data baris Excel (IDPEL, NAMA, KODE LBKB) ke dalam 3 kelas resmi (Sesuai, Tidak Sesuai, Blur).
6. 🔲 **Confidence Scoring & Audit Trail Logging:** Menambahkan skor keyakinan dan kolom alasan audit (*Audit Reason*) untuk setiap vonis sistem.
7. 🔲 **Review Routing:** Mengarahkan data dengan confidence rendah (< 0.70) ke antrean verifikasi manual teknisi.

#### 🔹 FASE 3: Dual-Mode Packaging & Integrasi Operasional
8. 🔲 **Userscript Browser Portal ACMT (`argus_evaluator.user.js`):** Implementasi engine di browser menggunakan Tampermonkey untuk inspeksi interaktif langsung oleh petugas saat membuka web portal PLN.
9. 🔲 **Script Batch Processing CLI Python (`src/pipeline.py`):** Skrip pemrosesan massal lokal berkecepatan tinggi dengan multi-threading untuk memproses 7.470 foto sekaligus dan mengekspor hasilnya ke Excel.

#### 🔹 FASE 4: Pilot Test Skala Penuh, Evaluasi Metrik & Serah Terima
10. 🔲 **Audit Penuh Dataset Rek 12 2025:** Menjalankan pipeline pada seluruh 7.470 foto dokumentasi LBKB.
11. 🔲 **Evaluasi Metrik Akurasi & Cost:** Menghitung hit-rate barcode, akurasi klasifikasi, penghematan kuota API (70-80%), dan rata-rata latensi per foto.
12. 🔲 **Dokumentasi Laporan Akhir & Serah Terima Repo:** Penyusunan laporan magang resmi berbasis referensi ilmiah dan transfer knowledge ke tim PLN UP3 Mojokerto.

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
