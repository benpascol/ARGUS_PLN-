# 🗺️ ARGUS — Methodology & Development Roadmap
## Panduan Langkah-Langkah Pengembangan Berbasis Riset Akademik (Hybrid Cascading Architecture)

> **Tujuan Dokumen:** Memetakan langkah-langkah pengembangan proyek ARGUS secara sistematis dan bertahap, menggabungkan standar metodologi penelitian visi komputer (Machine Learning Life Cycle / MLLC) dan rekayasa perangkat lunak (ISO/IEC/IEEE 12207).
>
> **Arsitektur Inti:** *Cascading Multi-Tier Hybrid* — OpenCV Laplacian ROI (Tier 1) → ZBar & (YOLO-Seg + Warp Perspective + PaddleOCR + YOLO-Cls) (Tier 2) → Multimodal VLM LLaMA 3.2 Vision (Tier 3 Fallback) → Deterministic Decision Engine (Tier 4).
>
> **Referensi Ilmiah (terverifikasi):** Laroca et al., IEEE Access (2021); Lin et al., Applied Sciences MDPI (2023); Haseeb et al., VFAST TSE (2024); Imran et al., CMC (2023). Status tiap sumber dan koreksi atas klaim lama ada di [`ARGUS_Technology_Verification.md`](./ARGUS_Technology_Verification.md). Pengenal angka LCD (PaddleOCR vs CRNN vs YOLO digit) diputuskan lewat benchmark, bukan diasumsikan.

---

## 🏛️ PRINSIP METODOLOGI & ARSITEKTUR SISTEM

Sistem ARGUS dirancang untuk menyelesaikan audit massal ±8.000 citra dokumentasi LBKB per bulan di PT PLN (Persero) UP3 Mojokerto pada komputer kantor tanpa GPU dedicated. Untuk mencapai efisiensi maksimal, sistem membagi tugas visual ke dalam 4 Tier hierarkis:

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ 📁 CITRA LAPANGAN MENTAH (7.470+ File JPG, Resolusi 540x960)                            │
└──────────────────────────────────────────┬──────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ 🛡️ TIER 1: GATEKEEPER KUALITAS & SILAU (OpenCV CPU, <5 ms, 0 Token)                     │
│ • Deteksi Blur: Varians Laplacian pada ROI meteran (σ² < threshold -> Foto Blur).       │
│ • Deteksi Glare/Silau: Analisis saturasi & intensitas HSV (V > 240, S < 30).           │
│ • Jika silau menutupi >20% area angka -> Vonis: "ANOMALI_GLARE_TERHALANG" (Stop awal).  │
└──────────────────────────────────────────┬──────────────────────────────────────────────┘
                                           │ (Foto Lolos: Tajam & Tidak Silau Ekstrem)
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚡ TIER 2: JALUR EKSTRAKSI DETERMINISTIK & MODEL LOKAL (Offline, Cepat, 0 Token)         │
│                                                                                         │
│ ├─► Tier 2A: Scanner Barcode Nomor Seri 11 Digit (ZBar + CLAHE)                         │
│ │   • Ekstraksi barcode meteran prabayar ber-checksum pasti 100% (<30 ms).              │
│ │                                                                                       │
│ ├─► Tier 2B: Two-Stage Local YOLO Digit Reader (Dual Local Neural Nets, 4.2 ms/citra)   │
│ │   • Model 1 (meter_counter_detector.pt): Crop area dial roller analog / LCD digital. │
│ │   • Quality Gatekeeper: Validasi kontras & glare pada crop dial box.                  │
│ │   • Model 2 (digit_ocr_detector.pt): Membaca angka 0-9 & titik/koma (dot).            │
│ │   • Strict Sequence Validator:                                                        │
│ │     - Meter Analog: Wajib deretan 4–6 digit kontinu. Tolak jika parsial/terpotong.   │
│ │     - Meter Digital: Parsing dinamis via kelas 'dot' (angka depan koma = stand PLN).  │
│ │                                                                                       │
│ └─► Tier 2C: Pengklasifikasi Rintangan Lapangan Lokal (YOLOv8-Cls / MobileNetV3)        │
│     • Klasifikasi citra tanpa meteran: Pagar (4), Rumah Tutup (E), Kosong (F), Anjing. │
└──────────────────────────────────────────┬──────────────────────────────────────────────┘
                                           │ (Kasus Anomali Semantik / Fraud / Ambigu)
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ 🧠 TIER 3: HAKIM SEMANTIK & FRAUD DETECTOR (NVIDIA NIM LLaMA 3.2 11B Vision)            │
│ • EKSKLUSIF untuk anomali semantik: mendeteksi fraud (aspal/jok/tanah), pagar terkunci, │
│   rumah kosong, meteran dibongkar/rusak parah, atau meteran tidak ada sama sekali.      │
│ • ANTI-PEMBOROSAN TOKEN: DILARANG MEMBEBANI VLM UNTUK PEMBACAAN ANGKA DIGITAL HARIAN!   │
│   (Seluruh pembacaan angka meteran analog & digital wajib dituntaskan di Tier 2 lokal). │
└──────────────────────────────────────────┬──────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│ ⚖️ TIER 4: DETERMINISTIC DECISION & ARBITRATION ENGINE                                   │
│ • Validasi integritas: Tolak pembacaan parsial (misal cuma terbaca 1 digit akibat silau).│
│ • Menuliskan angka hasil bacaan foto secara otomatis ke kolom STAN_BACA.                │
│ • Membandingkan STAN_BACA vs STAN_METER untuk mendeteksi kelainan pembacaan meter.      │
│ • Memetakan status resmi: "Sesuai dengan Data", "Tidak Sesuai dengan Data",             │
│   "Hasil foto blur / Glare", "Perlu Review Manual".                                     │
│ • Mencatat audit_reason dan confidence_score untuk transparansi audit PLN.              │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ PETA LANGKAH PENGEMBANGAN KOMPREHENSIF (FASE 0 – 4)

---

### FASE 0: Validasi Ilmiah & Grounding Arsitektur [SELESAI ✅ — 26-09-2026]

| Langkah | Deskripsi Pekerjaan | Deliverable | Status |
|:---:|---|---|:---:|
| **0.1** | Riset literatur akademik: Komparasi pure VLM vs pure YOLO vs Cascading Hybrid. | Sintesis Jurnal | DONE |
| **0.2** | Penyusunan laporan validasi ilmiah dengan 6 sitasi internasional terindeks. | `Docs/ARGUS_Research_Validation.md` | DONE |
| **0.3** | Identifikasi penyempurnaan teknis (ROI Laplacian, CLAHE, Warp Perspective). | Spesifikasi Teknis | DONE |
| **0.4** | Pembaruan Holy Trinity Dokumen (`README.md`, `RULEBOOK.md`, `WHITEBOARD.md`). | Commit ke `develop` | DONE |

---

### FASE 1: Pengujian Empiris Sampel, Benchmarking & Persiapan Model [AKTIF 🚀]

> **Tujuan:** Memvalidasi setiap komponen visual pada 15–20 sampel foto representatif lapangan sebelum mengintegrasikannya ke dalam engine produksi.

#### 🔹 Langkah 1.1 — Seleksi & Organisasi Sampel Terstruktur (5 Skenario A–E)
Mengambil 15–20 sampel foto nyata dari `Docs/DOkumentasi LBKB/` dan mengorganisasikannya ke subfolder `data/samples/`:
- `A_barcode_jelas/` (3-4 foto): KWH meter prabayar stiker barcode ideal (baseline hit-rate ZBar).
- `B_barcode_terhambat/` (3-4 foto): KWH meter tertutup debu / silau mika (uji ketangguhan CLAHE).
- `C_lcd_sudut_miring/` (3-4 foto): KWH meter dengan layar LCD diambil dari sudut miring (uji Warp Perspective & OCR).
- `D_rintangan_fisik/` (3-4 foto): Pagar terkunci, rumah tutup, anjing galak (uji YOLO-Cls & VLM).
- `E_foto_fraud/` (3-4 foto): Aspal jalan, tanah, jok motor, dinding kosong (uji deteksi manipulasi).

#### 🔹 Langkah 1.2 — Benchmark Tier 1: Deteksi Blur & Silau (OpenCV Laplacian & HSV Glare)
- Implementasi cropping area tengah (ROI 40–60%) untuk mengisolasi meteran dari background kasar.
- Pengujian 3 nilai ambang batas varians Laplacian: `30.0` (baseline lama), `80.0`, dan `120.0`.
- **Implementasi Glare Masking (HSV):** Deteksi piksel saturasi rendah dan intensitas tinggi (V > 240, S < 30). Jika area silau pada counter > 20%, sistem otomatis menghentikan proses baca dan memvonis `ANOMALI_GLARE_TERHALANG`.
- Target: 0% *False Rejection* pada foto yang nomor/stand meternya masih terbaca mata manusia, dan 0% *False Acceptance* pada foto silau ekstrem.

#### 🔹 Langkah 1.3 — Benchmark Tier 2A: ZBar Barcode Reader + Preprocessing Bertahap
- Pengujian hit-rate pembacaan barcode 11 digit nomor seri dalam 3 tahap:
  1. *Tahap 1 (Baseline):* Foto mentah langsung ke ZBar.
  2. *Tahap 2 (CLAHE):* Grayscale → CLAHE (`clipLimit=2.5`) → ZBar.
  3. *Tahap 3 (Full Pipeline):* CLAHE → Binarisasi Otsu adaptif → Morfologi → ZBar.
- Target: Membuktikan peningkatan hit-rate ZBar dari <50% menjadi >80% pada citra berdebu/silau.

#### 🔹 Langkah 1.4 — Benchmark Tier 2B: Two-Stage Local YOLO Digit Reader & Digital Meter Handler
- **Arsitektur Dua Tahap (Two-Stage Local YOLO):**
  1. *Stage 1 (Localizer):* `models/meter_counter_detector.pt` mendeteksi dan memotong (*crop*) kotak counter/layar display meteran dari foto utuh 540x960.
  2. *Stage 2 (Digit OCR):* `models/digit_ocr_detector.pt` mendeteksi bounding boxes angka `0-9` dan titik desimal `dot` secara lokal dalam 4.2 ms (mAP@50 96.1% via anti-flip training).
- **Quality & Glare Gatekeeper pada Crop Dial:**
  - Memeriksa kebersihan crop sebelum dioper ke deteksi angka. Mencegah kasus silau seperti Sampel #6 yang hanya menyisakan 1 angka kontras.
- **Strict Sequence Validator (Anti-Angka Bodong):**
  - *Meter Analog:* Wajib mendeteksi deretan horizontal kontinu 4–6 digit. Jika terdeteksi < 4 digit, vonis `STAND_TIDAK_LENGKAP` (dilarang mengeluarkan angka parsial ke billing).
  - *Meter Digital (Dinamis):* Pengurutan koordinat X (`x_min`). Karakter desimal `dot` digunakan sebagai pemisah: seluruh angka di depan `dot` diambil sebagai stand integer kWh resmi PLN, angka di belakang `dot` diabaikan sesuai SOP penagihan.
- Target: Pembacaan angka meter analog dan digital tuntas 100% offline tanpa menggunakan token API VLM.

#### 🔹 Langkah 1.5 — Benchmark Tier 2C & Tier 3: Klasifikasi Rintangan & VLM Fallback
- Pengujian klasifikasi pemandangan lokal (YOLO-Cls / MobileNetV3) vs penalaran semantik VLM (LLaMA 3.2 Vision).
- **Anti-Pemborosan Token VLM:** VLM **dilarang keras** dibebani tugas OCR pembacaan angka meter digital harian. VLM dieksklusifkan sebagai *Supreme Auditor* untuk:
  1. Mendeteksi foto manipulasi / fraud (aspal jalan, jok motor, tanah, dinding kosong).
  2. Memvalidasi rintangan fisik nyata (pagar digembok, rumah tutup/kosong, anjing galak).
  3. Mengidentifikasi meteran rusak fisik ekstrem, dibongkar, atau hilang.
- Formulasi prompt 4-layer VLM: *(1) Persona Auditor, (2) Task Definition, (3) Chain-of-Thought, (4) Strict JSON Schema*.

#### 🔹 Langkah 1.6 — Dokumentasi Benchmark & Penguncian Threshold Resmi
- Merekam seluruh tabel angka hasil pengujian di Section 3 `WHITEBOARD.md`.
- Mengunci parameter resmi di `RULEBOOK.md` Pilar 6 dan `.env` (`BLUR_THRESHOLD`, `GLARE_THRESHOLD`, `CLAHE_CLIP_LIMIT`).

---

### FASE 2: Perancangan Core Decision Engine & Arbitrase Logika

> **Tujuan:** Membangun modul Python terpusat (`src/decision/engine.py`) yang menerima sinyal visual Tier 1–3, mengisi kolom `STAN_BACA`, mencocokkan ke `STAN_METER`, dan mengeluarkan vonis audit resmi.

#### 🔹 Langkah 2.1 — Desain Kontrak Data Formal (Input/Output Contract)
Mendefinisikan tipe data berstruktur ketat sebelum koding:
```python
class ImageSignal:
    filepath: str
    is_blurry: bool
    blur_score: float
    barcode_serial: str | None     # Nomor seri 11 digit dari ZBar
    lcd_stand_value: int | None    # Angka stand meter dari OCR / VLM
    scene_classification: str      # "meteran" | "pagar" | "rumah_tutup" | "fraud_aspal"
    confidence_score: float
    pipeline_path: str             # "T1_blur" | "T2_local" | "T3_vlm_fallback"

class AuditVerdict:
    status: Literal["Sesuai dengan Data", "Tidak Sesuai dengan Data", "Hasil foto blur"]
    stan_baca_hasil: int | None    # Angka yang otomatis ditulis ke STAN_BACA
    selisih_stand: int | None      # Selisih antara STAN_BACA vs STAN_METER
    kode_lbkb_saran: str           # Kode rintangan resmi jika meter tidak terbaca
    audit_reason: str              # Kalimat pertanggungjawaban audit resmi
    confidence_score: float
    needs_manual_review: bool      # True jika confidence < 0.70
```

#### 🔹 Langkah 2.2 — Implementasi Logika Arbitrase Keputusan
- **Alur Kasus Meteran:**
  Jika LCD terbaca $\rightarrow$ Masukkan angka ke `STAN_BACA`. Bandingkan dengan `STAN_METER`:
  - Jika `STAN_BACA == STAN_METER` $\rightarrow$ Vonis: **"Sesuai dengan Data"**.
  - Jika `STAN_BACA != STAN_METER` $\rightarrow$ Vonis: **"Tidak Sesuai dengan Data (Kelainan Bacaan Terkonfirmasi)"**.
- **Alur Kasus Rintangan:**
  Jika foto terbukti Pagar Terkunci (4) / Rumah Tutup (E) $\rightarrow$ Vonis: **"Sesuai dengan Data (Rintangan Fisik Sah)"**.
- **Alur Kasus Fraud:**
  Jika foto terbukti aspal/tanah/jok $\rightarrow$ Vonis: **"Tidak Sesuai dengan Data (Indikasi Manipulasi Lapangan)"**.

#### 🔹 Langkah 2.3 — Evaluasi Metrik Ganda (Bukan Hanya Akurasi)
Menghitung Confusion Matrix lengkap: **Precision**, **Recall** (terutama penangkapan fraud), **F1-Score**, **Local Processing Ratio** (target 80% offline), dan **API Cost Saving** (target hemat 80–90%).

---

### FASE 3: Dual-Mode Packaging & Integrasi Operasional

> **Tujuan:** Mengemas sistem ke dalam 2 bentuk operasional siap pakai oleh staf PLN.

#### 🔹 Langkah 3.1 — Mode A: Batch CLI Processor (`src/pipeline.py`)
- Skrip Python multi-threading berkecepatan tinggi untuk memproses seluruh 7.470 foto secara massal di komputer lokal.
- Output: File Excel terstruktur di `data/output/` berisi kolom baru: `STAN_BACA_ARGUS`, `STATUS_AUDIT`, `ALASAN_AUDIT`, dan `PERLU_REVIEW_MANUAL`.

#### 🔹 Langkah 3.2 — Mode B: Userscript Browser Tampermonkey (`argus_evaluator.user.js`)
- Berjalan langsung di antarmuka web portal ACMT PLN (`portalapp.iconpln.co.id`).
- Menginspeksi tabel antrean verifikasi secara interaktif: menampilkan status visual instan, mengisi field `STAN_BACA` otomatis, dan menyediakan tombol ekspor rekapitulasi.

---

### FASE 4: Pilot Test Skala Penuh, Evaluasi & Serah Terima

#### 🔹 Langkah 4.1 — Pilot Run Penuh Dataset Rek 12 2025
- Eksekusi pipeline pada seluruh 7.470 foto mentah dokumentasi LBKB.
- Memantau stabilitas memori, latensi per citra, rasio fallback VLM, dan persentase keberhasilan.

#### 🔹 Langkah 4.2 — Ground Truth Sampling (100 Baris Manual bersama PLN)
- Mengambil 100 baris acak dari output ARGUS dan memverifikasinya bersama pengawas catat meter PLN UP3 Mojokerto.
- Menghitung akurasi riil dan batas toleransi kesalahan (*margin of error*) untuk laporan resmi.

#### 🔹 Langkah 4.3 — Laporan Akhir, User Manual & Transfer Knowledge
- Penyusunan laporan magang berstandar IEEE, buku panduan operasional pengguna, dan serah terima repositori ke tim PLN.

---

## 🛡️ IDENTIFIKASI RISIKO TEKNIS & MITIGASI

| ID | Risiko Teknis | Dampak | Mitigasi ARGUS |
|:---:|---|:---:|---|
| **R-01** | Foto LCD miring ekstrem | Tinggi | YOLOv8-Seg poligon 4 titik + `cv2.warpPerspective` menormalkan sudut. |
| **R-02** | Silau matahari (*glare*) pada mika | Tinggi | Preprocessing CLAHE adaptif sebelum OCR. |
| **R-03** | Halusinasi digit pada VLM | Kritis | Digit utama dibaca via OCR lokal / Checksum ZBar; VLM hanya fallback rintangan. |
| **R-04** | Kuota API VLM habis di tengah batch | Tinggi | Tier 1 & 2 menyelesaikan 80% data offline; VLM hanya menangani sisa 20%. |
| **R-05** | Model lokal ragu menentukan rintangan | Sedang | Confidence threshold (<0.70) otomatis mengoper kasus ke VLM. |
| **R-06** | Internet kantor PLN mati | Sedang | Pipeline offline (Tier 1 & Tier 2) tetap berjalan normal untuk 80% foto. |
| **R-07** | Silau matahari parsial menghapus sebagian digit (Kasus Sampel #6) | Kritis | Tier 1 Glare Masking (HSV) + Strict Sequence Validator menolak angka parsial sebatang kara dan memvonis `ANOMALI_GLARE_TERHALANG`. |
| **R-08** | Meter digital panjang dinamis & pemborosan kuota token VLM (Kasus Sampel #8) | Kritis | Deteksi angka 100% lokal via YOLO 11-kelas (`0-9` + `dot`) memisahkan angka integer tagihan PLN vs desimal tanpa membebani kuota API VLM. |
