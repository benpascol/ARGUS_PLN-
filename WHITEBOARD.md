# 🎯 Section 1: Current Grand Plan
> [!IMPORTANT]
> **Fokus Utama Saat Ini:** Tahap 1: Pengujian Sampel Nyata (Proof of Concept) pada 10-20 Foto Citra Lapangan, Benchmark Algoritma Blur (OpenCV Laplacian), Validasi Barcode Scanner (ZBar), dan Pemetaan Prompt Semantik VLM untuk Kasus LBKB PLN.
> **Affected Areas:** Folder Citra `DOkumentasi LBKB/`, File Master `12 LBKB Billing Rek 12 2025 copy+foto.xlsx`, Script Portal `Tanpa judul.txt`, dan Skrip Pengujian Python.
> **Dokumentasi Resmi:** [`README.md`](file:///d:/Hooh_Lah/PLN/ARGUS/README.md), [`RULEBOOK.md`](file:///d:/Hooh_Lah/PLN/ARGUS/RULEBOOK.md).
> **Success Criteria:** 
> 1. Terbuktinya metrik Laplacian Variance dalam memisahkan foto buram/rusak dari foto layak audit pada sampel foto lapangan $\pm 20$ citra. *(Status: IN PROGRESS)*
> 2. Terverifikasinya pembacaan nomor meteran 11 digit via Barcode Reader ZBar secara otomatis tanpa halusinasi pada KWH Meter prabayar/pascabayar bertipe stiker barcode. *(Status: IN PROGRESS)*
> 3. Terumuskannya *system prompt* VLM (NVIDIA NIM LLaMA 3.2 11B Vision) yang menghasilkan output JSON deterministik untuk mendeteksi rintangan pagar terkunci, pintu rumah tutup, dan foto manipulasi/fraud. *(Status: PLANNED)*
> 4. Sinkronisasi logika Decision Engine dengan data kolom Excel sheet `Detail` (IDPEL, NAMA, KDBACA, KODE LBKB). *(Status: PLANNED)*
> 5. Keputusan arsitektur kemasan (*packaging*): Modifikasi langsung pada Userscript ACMT (`Tanpa judul.txt`) atau pembuatan Skrip Batch Pipeline Python untuk pemrosesan 8.000 data sekaligus. *(Status: PLANNED)*

---

### 🚀 Immediate Action Plan (Fase 1: PoC Sampel, Fase 2: Decision Engine, Fase 3: Packaging):

#### 🔹 FASE 1: Pengujian Empiris Sampel & Benchmarking (PoC Lapangan)
1. 🔲 **Seleksi 15 Foto Sampel Representatif:** Memilih sampel foto dari `DOkumentasi LBKB/` yang mewakili 4 skenario: (1) KWH Meter prabayar stiker barcode jelas, (2) KWH Meter lama dengan teks/spidol, (3) Rintangan lapangan (Pagar gembok / rumah tutup kode E & F), (4) Foto blur/rusak/gelap.
2. 🔲 **Benchmark Deteksi Blur OpenCV:** Menjalankan uji coba perhitungan varians Laplacian $\sigma^2$ untuk menetapkan *threshold* aman yang tidak memotong foto valid.
3. 🔲 **Benchmark Barcode Scanner ZBar:** Mengukur persentase keberhasilan pembacaan nomor seri 11 digit langsung dari citra resolusi $540 \times 960$.
4. 🔲 **Formulasi Prompt JSON VLM:** Menguji respon LLaMA 3.2 11B Vision via API Key NVIDIA NIM untuk kasus foto non-barcode dan rintangan fisik.

#### 🔹 FASE 2: Perancangan Core Decision Engine & Arbitrase Logika
5. 🔲 **Penyusunan Modul Arbitrase Keputusan:** Membangun modul Python/JS yang memetakan sinyal visual (Blur, Barcode, VLM) terhadap data baris Excel (IDPEL, KODE LBKB) ke dalam 3 kelas definitif.
6. 🔲 **Audit Trail & Logging:** Menambahkan kolom alasan klasifikasi (*Audit Reason*) untuk setiap keputusan sistem.

#### 🔹 FASE 3: Packaging & Integrasi Operasional
7. 🔲 **Refactoring Userscript Browser (`Tanpa judul.txt`):** Mengganti prompt stand meter pascabayar lama dengan logika baru ARGUS untuk pemakaian langsung staf PLN di portal ACMT.
8. 🔲 **Script Batch Python (Opsi Skala Besar):** Membuat skrip pemroses batch offline untuk mengklasifikasikan seluruh 8.000 baris data Excel secara paralel dalam hitungan menit.

---

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

---

## 🩻 Section 3: Audit Plan (The Ruthless Audit)

### 🟢 The Good
- `[18-09-2026]` **Holy Trinity Documentation Ready:** Berkas `README.md`, `RULEBOOK.md`, dan `WHITEBOARD.md` untuk Project ARGUS telah resmi dibentuk dan disinkronkan dengan standar korporat PLN UP3 Mojokerto.
- `[18-09-2026]` **Ketersediaan Data Master Lengkap:** Terdapat 8.127 baris data pada sheet `Detail` Excel dan 7.470 berkas citra asli beresolusi $540 \times 960$ di folder `DOkumentasi LBKB/`.
- `[18-09-2026]` **Infrastruktur API Key Terpasang:** NVIDIA NIM API Key aktif (`API=nvapi-...`) terkonfirmasi di `.env`.

### 🟡 The Bad
- `[18-09-2026]` **Userscript Eksisting Masih Pascabayar:** Kode pada `Tanpa judul.txt` masih berorientasi pada pembacaan stand kWh meter pascabayar 5 digit dan belum memiliki logika penanganan LBKB prabayar / foto pagar.
- `[18-09-2026]` **Threshold Blur Belum Terkalibrasi Empiris:** Nilai ambang batas Laplacian Variance untuk citra kamera petugas catat meter ($540 \times 960$) masih harus diuji pada sampel nyata untuk menghindari *False Rejection*.

### 🔴 The Ugly
- `[18-09-2026]` **Kualitas Citra Lapangan Sangat Beragam:** Adanya pantulan silau matahari (*glare*) pada mika penutup meteran dan debu tebal pada stiker barcode berpotensi menurunkan *hit-rate* pembacaan barcode jika tidak dilengkapi pra-pemrosesan citra yang tangguh.

---

## 📋 Issue & Solution Log

| Level | Date Logged | Masalah (Issue) | Solusi yang Diambil / Rencana Solusi | Status | Date Resolved |
| :---: | :--- | :--- | :--- | :---: | :--- |
| 🔴 | `18-09-2026` | **Mismatch Target Model Lama:** Userscript `Tanpa judul.txt` menginstruksikan AI mengabaikan nomor seri meter (*"Ignore the meter serial number"*) dan mencocokkan angka ke `stan_baca`. | Merombak total system prompt VLM dan parser validasi agar mengekstrak nomor seri meteran fisik 11 digit dan IDPEL 12 digit untuk kasus LBKB token/prabayar. | `PLANNED` | - |
| 🟡 | `18-09-2026` | **Latensi Tinggi & Kuota VLM untuk 8.000 Citra:** Memproses seluruh 8.000 citra via API VLM memakan waktu >3 jam dan berisiko terkena *rate limit*. | Menerapkan *Cascading Multi-Tier Pipeline*: OpenCV memfilter foto blur, ZBar membaca barcode nomor meter lokal gratis, dan VLM hanya memproses sisa 20-30% foto sulit. | `PLANNED` | - |
| 🟡 | `18-09-2026` | **Resiko Halusinasi Digit Angka pada VLM:** VLM kerap salah membaca angka mirip (misal `8` menjadi `3`) pada teks angka panjang 11 digit. | Mengutamakan ekstraksi barcode fisik via ZBar (yang memiliki verifikasi *checksum* 100% pasti) sebelum melempar citra ke VLM. | `PLANNED` | - |
| 🟢 | `18-09-2026` | **Inisialisasi Tata Kelola Repositori:** Ketiadaan acuan aturan kerja dan pelacak progres pada folder kerja `ARGUS/`. | Menyusun Holy Trinity: `README.md` (arsitektur), `RULEBOOK.md` (konstitusi hukum), dan `WHITEBOARD.md` (roadmap & audit log). | `DONE` | `18-09-2026` |
