# 🗺️ ARGUS — Methodology & Development Roadmap
## Panduan Langkah-Langkah Pengembangan Berbasis Riset Akademik

> **Tujuan Dokumen:** Memetakan langkah-langkah pengembangan ARGUS secara sistematis, memvalidasikan urutan fase berdasarkan standar metodologi penelitian terapan (IEEE, MDPI, ResearchGate), serta mengidentifikasi risiko teknis dan potensi mitigasi di setiap tahap.
>
> **Referensi Utama:** Literatur AMR (*Automated Meter Reading*), IQA (*Image Quality Assessment*), Cascading CV Pipeline, VLM Field Audit, dan ISO/IEC/IEEE 12207 Software Development Lifecycle Standard.

---

## 🏛️ PRINSIP METODOLOGI YANG DIGUNAKAN

Berdasarkan penelusuran literatur akademik, proyek ARGUS mengikuti dua metodologi utama secara paralel:

1. **Machine Learning Life Cycle (MLLC):** Kerangka standar untuk sistem berbasis visi komputer (dikonfirmasi oleh literatur IEEE dan MDPI Applied Sciences, 2023). Fase-fasenya: *Data Acquisition → Preprocessing → Modeling → Evaluation → Deployment*.
2. **Software Development Life Cycle (SDLC) — Hybrid Agile-Iterative:** Karena sistem ini terdiri dari beberapa komponen independen (Python pipeline, userscript browser, decision engine) yang dapat dikembangkan dan diuji secara iteratif.

> [!IMPORTANT]
> Urutan fase yang kita miliki saat ini (Fase 0-4 di WHITEBOARD.md) **sudah sesuai** dengan standar MLLC akademik internasional. Namun riset ini mengidentifikasi **beberapa langkah penting yang perlu ditambahkan** ke dalam urutan, khususnya di Fase 1 dan Fase 2.

---

## VERDICT: APAKAH LANGKAH KITA SUDAH BENAR?

| Aspek | Status | Catatan |
|---|---|---|
| Urutan Fase (0 - 4) | BENAR | Sesuai standar MLLC & SDLC-Agile |
| Arsitektur Cascading (T1->T2->T3) | BENAR | Konfirmasi literatur IEEE, MDPI, CMC |
| Pemilihan Tools (OpenCV/ZBar/VLM) | BENAR | Terbukti optimal untuk constraint ARGUS |
| **Threshold Laplacian saat ini (30.0)** | **PERLU DIREVISI** | Literatur: threshold 80-120 untuk resolusi 540x960 |
| **Preprocessing ZBar** | **BELUM ADA** | Wajib tambah CLAHE + Otsu sebelum ZBar |
| Evaluasi hanya akurasi tunggal | **KURANG** | Wajib tambah Precision, Recall, F1-Score |
| Kontrak data antar modul | **BELUM DIDEFINISIKAN** | Harus formal sebelum coding Fase 2 |
| Ground truth evaluation | **BELUM DIRENCANAKAN** | Wajib sampling 100 baris verifikasi manual |

---

## PETA LANGKAH PENGEMBANGAN KOMPREHENSIF

---

### FASE 0: Validasi Ilmiah & Grounding Arsitektur [SELESAI - 26-09-2026]

| Langkah | Deskripsi | Status |
|---|---|---|
| 0.1 | Riset literatur: Komparasi cascading pipeline vs Pure VLM vs Fine-tuned YOLO | DONE |
| 0.2 | Penyusunan dokumen validasi ilmiah (Docs/ARGUS_Research_Validation.md) dengan 6 sitasi jurnal terindeks | DONE |
| 0.3 | Identifikasi penyempurnaan teknis: ROI-focused Laplacian, CLAHE preprocessing, checksum precedence | DONE |
| 0.4 | Pembaruan Holy Trinity (README, RULEBOOK, WHITEBOARD) dan commit ke main | DONE |

**Justifikasi Akademik:**
> IEEE Computer Society dan ISO/IEC/IEEE 12207 menekankan bahwa **validasi arsitektur berbasis literatur adalah langkah pertama wajib** sebelum implementasi teknis, terutama pada proyek yang akan dipertanggungjawabkan secara institusional/akademik.

---

### FASE 1: Pengujian Empiris Sampel & Benchmarking (PoC Lapangan) [AKTIF]

> **Tujuan Fase 1:** Membuktikan bahwa komponen teknis yang dipilih (OpenCV, ZBar, VLM) dapat bekerja secara nyata pada data lapangan ARGUS sebelum investasi waktu penuh ke Fase 2.

#### Langkah 1.1 — Seleksi & Organisasi Sampel Representatif

**Justifikasi:** MLLC standar (IEEE AMR Literature, MDPI 2023) mewajibkan bahwa dataset pengujian harus mencakup **semua skenario edge case** yang mungkin ditemui di kondisi lapangan nyata, bukan hanya kasus ideal.

Pilih **15-20 foto** dari folder `data/raw_images/DOkumentasi LBKB/` yang mewakili **5 skenario wajib**:

| No | Skenario | Contoh Kondisi | Alasan Wajib Diuji |
|:---:|---|---|---|
| A | KWH Meter prabayar barcode jelas | Foto ideal, barcode terlihat penuh | Baseline hit-rate ZBar terbaik |
| B | KWH Meter dengan hambatan optis | Silau mika, pantulan sinar, debu tebal | Uji robustness CLAHE preprocessing |
| C | KWH Meter pascabayar / teks spidol | Angka ditulis tangan di kertas/stiker | Uji kemampuan VLM OCR semantik |
| D | Rintangan fisik lapangan | Pagar gembok, pintu tutup, anjing, papan peringatan | Uji kemampuan VLM scene classification |
| E | Foto manipulasi / fraud oknum | Aspal jalan, tanah, jok motor, dinding kosong | Uji kemampuan VLM fraud detection |

**Organisasi folder sampel:**

```
data/samples/
├── A_barcode_jelas/        # 3-4 foto
├── B_barcode_terhambat/    # 3-4 foto
├── C_teks_spidol/          # 3-4 foto
├── D_rintangan_fisik/      # 3-4 foto
└── E_foto_fraud/           # 3-4 foto
```

---

#### Langkah 1.2 — Benchmark Tier 1: OpenCV Laplacian Blur (ROI-Focused)

**Justifikasi:** Literatur *Computers, Materials & Continua* (Imran et al., 2023) dan *IQA deployment research* (2024) menegaskan bahwa preprocessing ketajaman wajib difokuskan pada ROI objek target, bukan keseluruhan gambar. Background clutter (dinding, aspal) bisa memberi skor variance tinggi palsu.

**Langkah-langkah implementasi:**
1. Load gambar dengan OpenCV, konversi ke grayscale.
2. **Crop ROI:** Ambil area tengah (40-60% area gambar) yang paling mungkin berisi meteran — tanpa memerlukan object detection kompleks di tahap awal.
3. Hitung `variance of Laplacian` pada ROI tersebut.
4. Uji setidaknya **3 nilai threshold** berbeda (30, 80, 120) pada seluruh 15-20 sampel.
5. Catat **False Rejection** (foto valid diklasifikasikan blur) dan **False Acceptance** (foto blur lolos).
6. Tetapkan threshold konservatif yang menghasilkan zero atau minimal False Rejection.

**Metrik Output Fase 1.2:**
- `threshold_optimal` (nilai threshold yang menghasilkan keseimbangan terbaik)
- `false_rejection_rate` per threshold
- `false_acceptance_rate` per threshold

> [!WARNING]
> **Jebakan Utama dari Riset:** ZBar memiliki native success rate di bawah 50% dalam kondisi lapangan tidak terkontrol (unconstrained field images). Ini bukan kegagalan arsitektur, melainkan memerlukan preprocessing wajib sebelum ZBar.

---

#### Langkah 1.3 — Benchmark Tier 2: ZBar Barcode Scanner + CLAHE Pipeline

**Justifikasi:** ResearchGate dan MDPI (2023-2024) mengidentifikasi pipeline preprocessing optimal untuk meningkatkan hit-rate ZBar pada citra lapangan: CLAHE - Otsu Binarization - Morphological Operation - ZBar decode.

**Pipeline preprocessing yang wajib diuji secara bertahap:**

```
Uji 1 (Baseline): Citra mentah langsung ke ZBar
Uji 2 (CLAHE):    Citra -> Grayscale -> CLAHE -> ZBar
Uji 3 (Full):     Citra -> Grayscale -> CLAHE -> Otsu Binarize -> Morph. Clean -> ZBar
```

**Parameter CLAHE yang direkomendasikan literatur:**
- `clipLimit`: 2.0-3.0 (coba 2.0 dulu, naikkan jika kurang kontras)
- `tileGridSize`: (8, 8) untuk citra 540x960

**Metrik Output Fase 1.3:**
- `hit_rate_baseline` (ZBar tanpa preprocessing)
- `hit_rate_clahe` (ZBar + CLAHE)
- `hit_rate_full_pipeline` (ZBar + CLAHE + Otsu + Morph)
- `rata_rata_waktu_proses_ms` (dalam milidetik per gambar)

---

#### Langkah 1.4 — Formulasi & Pengujian System Prompt VLM (Tier 3)

**Justifikasi:** Riset 2024 tentang VLM Field Audit Classification (ResearchGate, Hyperscience AI) mengidentifikasi bahwa efektivitas VLM untuk tugas klasifikasi audit sangat bergantung pada **struktur prompt 4-layer** dan **constrained JSON output**. Model yang sama bisa memberikan akurasi berbeda drastis tergantung kualitas prompt.

**Struktur Prompt 4-Layer yang Direkomendasikan Literatur:**
1. **Persona Layer:** Tentukan peran VLM sebagai auditor PLN profesional.
2. **Task Layer:** Definisikan tugas spesifik yang harus dilakukan.
3. **Chain-of-Thought Layer:** Instruksikan model untuk memeriksa secara berurutan.
4. **Output Layer:** Paksa output JSON-only dengan schema yang ketat.

**Draft System Prompt ARGUS v1:**

```
Kamu adalah ARGUS, sistem audit foto bukti lapangan PLN. Tugasmu adalah menganalisis
foto dan mengeluarkan penilaian dalam format JSON yang ketat.

PROSEDUR ANALISIS (ikuti berurutan):
1. Periksa apakah objek utama dalam foto adalah KWH Meter listrik.
2. Jika KWH Meter terlihat: coba baca nomor seri di bawah barcode atau nomor tertulis.
3. Jika bukan KWH Meter: identifikasi scene_type (pagar, pintu tutup, dll).
4. Nilai kejujuran foto: apakah ini foto rintangan nyata atau manipulasi?

OUTPUT: Kembalikan HANYA JSON valid berikut, tanpa teks lain:
{
  "scene_type": "meteran_listrik|pagar_terkunci|rumah_tutup|anjing_galak|fraud_anomali|tidak_dikenal",
  "meter_serial_number": "string 11 digit atau null",
  "idpel_candidate": "string 12 digit atau null",
  "is_blurry": true/false,
  "fraud_indicators": [],
  "confidence_score": 0.0 sampai 1.0,
  "audit_reason": "satu kalimat alasan singkat"
}
```

**Pengujian:**
- Uji prompt terhadap seluruh 15-20 sampel.
- Catat kasus VLM menghasilkan output non-JSON (tangani dengan regex fallback parser).
- Catat kasus `confidence_score < 0.70` (kandidat review manual).

> [!NOTE]
> **Few-Shot Prompting:** Jika VLM kurang akurat pada skenario tertentu, pertimbangkan menambahkan 1-2 contoh gambar (foto + expected JSON) sebagai referensi dalam prompt. Riset 2024 menunjukkan peningkatan akurasi hingga 15-20% dengan pendekatan ini.

---

#### Langkah 1.5 — Dokumentasi Hasil Benchmarking & Penetapan Threshold Resmi

Setelah semua uji di 1.2-1.4 selesai, **wajib mendokumentasikan hasilnya** sebelum lanjut ke Fase 2:
- Rekap hasil di `WHITEBOARD.md` (Section 3 Audit Plan & Issue Log).
- Update threshold resmi ke `RULEBOOK.md` (Pilar 6) dan variabel `.env` (`BLUR_THRESHOLD`).
- Commit hasil: `chore(benchmark): record PoC benchmark results for threshold calibration`

---

### FASE 2: Perancangan Core Decision Engine & Arbitrase Logika

> **Tujuan Fase 2:** Membangun modul Python yang menerima sinyal dari Tier 1-3 dan menghasilkan vonis resmi + audit reason per baris data.

#### Langkah 2.1 — Desain Skema Data (Input/Output Contract)

Sebelum menulis kode, **definisikan kontrak data antar modul terlebih dahulu**:

```python
# Input per-gambar ke Decision Engine
class ImageSignal:
    filepath: str
    is_blurry: bool
    blur_score: float
    barcode_number: str | None   # None jika ZBar gagal
    vlm_result: dict | None      # None jika tidak perlu VLM
    excel_row: dict              # Data baris Excel: IDPEL, NAMA, KODE_LBKB

# Output Decision Engine
class AuditVerdict:
    status: Literal["Sesuai", "Tidak Sesuai", "Blur"]
    audit_reason: str
    confidence_score: float
    pipeline_path: str           # "T1_blur" | "T2_barcode" | "T3_vlm"
    needs_manual_review: bool    # True jika confidence < 0.70
```

#### Langkah 2.2 — Implementasi Modul Arbitrase

Urutan logika keputusan berdasarkan presedensi checksum matematis (Pilar 6 RULEBOOK.md):

```
IF is_blurry == True:
    verdict = "Blur" (Tier 1 terminus)

ELIF barcode_number is not None:
    IF barcode_number == excel_row["NOMOR_METER"]:
        verdict = "Sesuai" (T2 match - checksum verified)
    ELSE:
        verdict = "Tidak Sesuai" (T2 mismatch)

ELSE (no barcode -> call VLM):
    IF vlm.scene_type in ["pagar_terkunci", "rumah_tutup", "anjing_galak"]:
        IF excel_row["KODE_LBKB"] matches scene:
            verdict = "Sesuai" (T3 validated obstacle)
        ELSE:
            verdict = "Tidak Sesuai" (T3 obstacle-code mismatch)
    ELIF vlm.scene_type == "fraud_anomali":
        verdict = "Tidak Sesuai" (T3 fraud detected)
    ELSE:
        verdict = "Blur" OR needs_manual_review (T3 uncertain)
```

#### Langkah 2.3 — Implementasi Audit Trail & Confidence Scoring

**Justifikasi:** Penelitian tentang audit classification systems (Camunda, 2024) menegaskan bahwa setiap keputusan harus dapat di-trace balik ke aturan spesifik yang memicunya. Ini syarat wajib untuk sistem yang dipertanggungjawabkan ke manajemen PLN.

- Setiap `AuditVerdict` wajib menyertakan `audit_reason` dalam bahasa yang bisa dijelaskan ke manajemen PLN (bukan istilah teknis).
- Data dengan `confidence_score < 0.70` dirouting ke kolom `PERLU_REVIEW_MANUAL = True`.

#### Langkah 2.4 — Evaluasi Decision Engine dengan Metrik Standar

**Justifikasi:** Literatur tentang decision engine evaluation (IEEE, Splunk Research 2024) menegaskan bahwa akurasi tunggal adalah metrik yang menyesatkan untuk sistem klasifikasi tidak seimbang seperti fraud detection.

Metrik wajib yang harus dihitung:

| Metrik | Formula | Konteks ARGUS |
|---|---|---|
| **Precision** | TP / (TP + FP) | Dari semua yang divonis "Sesuai", berapa yang benar-benar sesuai? |
| **Recall** | TP / (TP + FN) | Dari semua kasus fraud nyata, berapa yang berhasil ARGUS tangkap? |
| **F1-Score** | 2 x (P x R) / (P+R) | Keseimbangan antara dua metrik di atas |
| **Barcode Hit Rate** | Barcode read / Total | Persentase foto yang diselesaikan tanpa perlu VLM |
| **VLM Fallback Rate** | VLM called / Total | Target: 20-30% |
| **API Cost Saving** | 1 - VLM Rate | Penghematan kuota API dibanding pure VLM |

---

### FASE 3: Dual-Mode Packaging & Integrasi Operasional

> **Tujuan Fase 3:** Membungkus engine ARGUS dalam dua mode pakai yang sesuai kebutuhan operasional PLN.

#### Langkah 3.1 — Mode A: Script Batch Python (CLI Offline)

- File: `src/pipeline.py`
- Fitur:
  - Membaca folder `data/raw_images/DOkumentasi LBKB/` secara rekursif
  - Multi-threading (concurrent processing) untuk batch ribuan foto
  - Output: File Excel di `data/output/` dengan kolom: `STATUS_ARGUS`, `AUDIT_REASON`, `CONFIDENCE_SCORE`, `PIPELINE_PATH`, `PERLU_REVIEW_MANUAL`
  - Progress bar dengan `tqdm` untuk monitoring real-time

#### Langkah 3.2 — Mode B: Userscript Browser Tampermonkey (Portal ACMT PLN)

- File: `web_extension/argus_evaluator.user.js`
- Fitur: Membaca data dari tabel HTML portal ACMT PLN, analisis foto inline per-baris, tombol ekspor ke Excel

> [!WARNING]
> **Risiko Teknis Mode B:** Browser userscript tidak memiliki akses langsung ke filesystem lokal atau OpenCV. Tier 1 (blur) dan Tier 2 (ZBar) mungkin perlu diemulasikan atau di-delegate penuh ke VLM API. Putuskan strategi arsitektur browser extension setelah Fase 1 dan 2 selesai.

---

### FASE 4: Pilot Test Skala Penuh, Evaluasi & Serah Terima

#### Langkah 4.1 — Pilot Run Dataset Rek 12 2025
- Jalankan `src/pipeline.py` pada seluruh 7.470 foto.
- Monitor: waktu total eksekusi, error rate, distribusi status klasifikasi.

#### Langkah 4.2 — Evaluasi Akurasi Skala Penuh (Ground Truth Sampling)

Karena tidak ada 100% ground truth berlabel:
1. Ambil **100 baris secara acak** dari hasil output ARGUS.
2. Lakukan verifikasi manual oleh petugas PLN yang paham LBKB.
3. Hitung `accuracy`, `precision`, `recall`, `F1-score` pada 100 sampel tersebut.
4. Bandingkan dengan baseline akurasi audit manual PLN (jika ada data historis).

#### Langkah 4.3 — Laporan Akhir & Serah Terima

Dokumen yang harus disiapkan:
1. **Laporan Teknis ARGUS** (berbasis dokumen ini dan `ARGUS_Research_Validation.md`).
2. **User Manual Operasional** (cara menggunakan script batch / userscript browser).
3. **Panduan Maintenance** (cara mengupdate threshold atau VLM prompt di masa depan).

---

## IDENTIFIKASI RISIKO TEKNIS & MITIGASI

Berdasarkan riset literatur (ResearchGate, MDPI, IEEE 2023-2024):

| No | Risiko | Probabilitas | Dampak | Mitigasi |
|:---:|---|:---:|:---:|---|
| R-01 | ZBar gagal pada foto debu/silau parah | Tinggi | Tinggi | Pipeline CLAHE + Otsu sebelum ZBar (Fase 1.3) |
| R-02 | VLM menghasilkan non-JSON output | Sedang | Sedang | Regex fallback parser + retry logic |
| R-03 | False Blur Rejection pada foto sedikit temaram | Sedang | Tinggi | ROI-focused Laplacian + threshold konservatif |
| R-04 | VLM rate limit pada batch 7.470 foto | Rendah | Tinggi | Concurrent limit di .env (CONCURRENCY_LIMIT=5) + exponential backoff |
| R-05 | KODE LBKB di Excel tidak selaras dengan scene VLM | Sedang | Tinggi | Pemetaan kode PLN resmi di Pilar 6 RULEBOOK.md |
| R-06 | Foto duplikat / nama file berulang di dataset | Sedang | Sedang | Hashing MD5 file sebelum proses |
| R-07 | Kolom Excel berbeda format di bulan berbeda | Rendah | Tinggi | Schema validation sebelum pipeline dijalankan |

---

## 7 LANGKAH TAMBAHAN BARU (Belum Ada di Roadmap Sebelumnya)

Berdasarkan hasil riset metodologi ini, berikut langkah yang perlu ditambahkan ke WHITEBOARD.md:

1. **[Fase 1.1] Organisasi Folder Sampel Terstruktur per Skenario:** Membuat subfolder A-E sebelum benchmarking agar hasil benchmark terorganisir dan reproducible untuk laporan ilmiah.
2. **[Fase 1.3] Pipeline Preprocessing Bertahap (3 Uji):** Uji ZBar dalam 3 tahap (baseline, CLAHE, full pipeline) agar ada data perbandingan empiris yang bisa dilaporkan ke laporan magang.
3. **[Fase 1.4] System Prompt 4-Layer + Few-Shot Prompting:** Menggunakan template prompt terstruktur yang direkomendasikan riset 2024, bukan prompt ad-hoc yang tidak terdokumentasi.
4. **[Fase 1.5] Commit Benchmark Resmi Sebelum Fase 2:** Mendokumentasikan dan mengunci threshold empiris ke RULEBOOK.md dan .env sebagai Single Source of Truth sebelum coding Decision Engine.
5. **[Fase 2.1] Kontrak Data Formal (Input/Output Schema):** Mendefinisikan skema data antar modul sebelum coding untuk mencegah interface mismatch.
6. **[Fase 2.4] Evaluasi Metrik Ganda (Precision + Recall + F1):** Jangan hanya menghitung akurasi tunggal — sistem fraud detection memerlukan evaluasi recall yang tinggi agar tidak ada kasus fraud yang lolos.
7. **[Fase 4.2] Ground Truth Sampling 100 Baris:** Evaluasi pada 100 sampel acak yang diverifikasi manual adalah pendekatan akademis valid dan praktis untuk sistem tanpa full ground truth.

---

*Dokumen ini disusun berdasarkan web search terhadap literatur IEEE, MDPI, ResearchGate, dan IEEE Computer Society ISO/IEC/IEEE 12207 standard.*
*Tanggal riset: 26 September 2026. Proyek: ARGUS — PLN UP3 Mojokerto.*
