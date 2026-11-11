# Panduan Kesiapan Portofolio Repositori ARGUS
**PT PLN (Persero) UP3 Mojokerto**  
*Lead Engineer: Pascol*  
*Dokumen Standar Repositori Kelas Enterprise / Tier-1 Portfolio*  
*Tanggal: 11 November 2026*

---

## 🎯 Tujuan Dokumen
Dokumen ini merangkum seluruh standar, berkas, dan elemen kunci yang diperlukan untuk mengubah repositori **ARGUS (Automated Recognition & Grid Utility Surveillance)** menjadi portofolio rekayasa perangkat lunak dan kecerdasan buatan (*AI & Software Engineering*) berstandar industri kelas atas (*Tier-1 Enterprise Grade*).

Portofolio ini dirancang untuk memberikan impresi kuat dan akuntabel di mata:
1. **Pimpinan & Stakeholder PT PLN (Persero):** Bukti kesiapan operasional, efisiensi anggaran, dan reliabilitas sistem.
2. **Dewan Juri / Evaluator Inovasi:** Bukti orisinalitas riset, metodologi MLLC + IEEE, dan dampak terukur.
3. **Eksekutif & Rekruter Teknologi Global:** Bukti penguasaan *Defensive Engineering*, *Production Machine Learning*, *Clean Architecture*, dan *System Design*.

---

## 📁 7 Komponen Wajib Repositori Portofolio

### 1. Riwayat Versi Standar Dunia (`CHANGELOG.md`) - [STATUS: SELESAI ✅]
- **Standar:** Mengikuti konvensi internasional **Keep a Changelog** dan **Semantic Versioning (SemVer)**.
- **Penerapan:** Menggunakan penomoran versi pra-rilis (`0.y.z`) selama masa riset aktif:
  - `[0.1.0]` (Fase Grounding & Laplacian Filter)
  - `[0.2.0]` (Two-Stage YOLO & Sequence Validator)
  - `[0.3.0]` (FastAPI REST Engine & Userscript ACMT)
  - `[0.4.0]` (Mesin Ekspor Excel Resmi & Consensus Voting)
  - `[0.5.0]` (Benchmark 7.470 Sampel & Standalone Corporate Dashboard)
  - `[Unreleased]` (Pemasangan Excel-Photo Pairing, Paginasi Virtual DOM, & Worker Pool).

### 2. Showcase Visual & Media Interaktif (`Docs/assets/`) - [STATUS: PLANNED 🔲]
*Rekomendasi:* 3–4 berkas visual beresolusi tinggi yang disematkan langsung di `README.md`:
- **Demo Dashboard Korporat:** Screenshot / animasi GIF dashboard bertema terang resmi PLN dengan interaksi filter kartu KPI.
- **Demo Web Extension ACMT:** Pratinjau integrasi Tampermonkey pada portal web dengan kecepatan inferensi 78 ms.
- **Hasil Laporan Excel Resmi:** Screenshot file Excel hasil audit lengkap dengan 4-baris legenda eksekutif dan hyperlink aktif.

### 3. Tabel Benchmark Kuantitatif Multi-Skala - [STATUS: DRAFTED IN README 🔲]
Menyajikan pembuktian matematis performa Model V5 dibanding baseline pada data riil:
- **Tabel 4 Skala:** 500 sampel $\rightarrow$ 2.500 $\rightarrow$ 5.000 $\rightarrow$ **7.470 data riil**.
- **Hasil Evaluasi Skala Penuh:**
  - **3.854 Match** (51,59% total populasi / **71,24% pada meteran fisik valid**).
  - Peningkatan bersih **+123 meter otomatis terbaca** dibanding Model V4.
  - Latensi terpangkas **43,1% menjadi 78,3 ms/meter** pada GPU RTX 4060.
  - Menghemat $\pm 160$ jam kerja verifikasi manual bulanan petugas PLN UP3 Mojokerto.

### 4. Pedoman Tata Kelola & Kontribusi (`CONTRIBUTING.md`) - [STATUS: PLANNED 🔲]
Membuktikan kemampuan kepemimpinan teknis (*Lead Engineer*) dalam mengarahkan standar kolaborasi:
- **Konvensi Pesan Commit:** Wajib menggunakan format *Conventional Commits*:
  - `feat:` (penambahan fitur baru)
  - `fix:` (perbaikan bug)
  - `docs:` (pembaruan dokumentasi)
  - `perf:` (optimasi kecepatan atau memori)
  - `refactor:` (restrukturisasi kode tanpa mengubah perilaku)
- **Model Percabangan Git:** Standar alur percabangan (`main` $\rightarrow$ `develop` $\rightarrow$ `feature/*`).
- **Standar Kode Python:** Kepatuhan terhadap *PEP 8*, *Type Annotations*, dan *Docstrings* terstruktur.

### 5. Kebijakan Privasi & Keamanan Data (`SECURITY.md`) - [STATUS: PLANNED 🔲]
Dokumen krusial untuk proyek utilitas publik BUMN yang mengelola data pelanggan:
- **Air-Gapped & Zero-Leakage Architecture:** Penegasan bahwa seluruh pemrosesan citra dan data IDPEL berjalan 100% lokal *offline* tanpa ketergantungan API pihak ketiga (bebas risiko kebocoran data).
- **Kepatuhan Regulasi:** Selaras dengan prinsip UU Perlindungan Data Pribadi (UU PDP) Indonesia.
- **Protokol Penanganan Kerentanan:** Tata cara pelaporan bug keamanan secara etis (*Responsible Disclosure*).

### 6. Lisensi & Hak Kepemilikan (`LICENSE`) - [STATUS: PLANNED 🔲]
- Menegaskan status hukum kekayaan intelektual perangkat lunak:
  *Hak Cipta © 2026 PT PLN (Persero) UP3 Mojokerto & Lead Engineer: Pascol.*
- Mengatur klausul penggunaan internal korporat (*Proprietary / Enterprise Closed-Source*).

### 7. Ringkasan Desain Sistem Terintegrasi (`ARCHITECTURE.md`) - [STATUS: PLANNED 🔲]
- Diagram arsitektur sistem dari hulu ke hilir (*End-to-End Pipeline*).
- Dokumentasi skema kontrak data formal:
  - `ImageSignal`: Atribut kualitas citra (blur score, glare ratio, status barcode, deteksi counter).
  - `AuditVerdict`: Skema keputusan audit (vonis, selisih kWh, confidence, diagnosa detail).

