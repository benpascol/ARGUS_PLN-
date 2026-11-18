# Changelog — Project ARGUS

Seluruh perubahan penting, eksperimen, serta riwayat iterasi pengembangan **Project ARGUS (*Automated Recognition & Grid Utility Surveillance*)** didokumentasikan secara kronologis dalam berkas ini.

Format catatan mengacu pada [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) dan mengikuti standar [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html):
- **Versi Pra-Rilis (`0.y.z`):** Mencatat seluruh siklus *trial-and-error*, riset arsitektur, eksperimen pelatihan dataset YOLO (`Model v1` s.d. `v5`), hingga pembangunan antarmuka operasional.
- **Versi Produksi Resmi (`1.0.0`):** Rilis produksi stabil perdana untuk operasional PT PLN (Persero) UP3 Mojokerto yang ditenagai oleh **Vision Engine Model V5** (`digit_ocr_detector_v5.pt`).

**Lead Engineer:** Benedictus Pascal  
**Institusi:** PT PLN (Persero) UID Jawa Timur — UP3 Mojokerto

---

## [1.0.0] — 2026-11-18 (Official Production Release • AI Model V5)

Rilis produksi resmi perdana **ARGUS Portable Desktop & Web Dashboard** yang siap didistribusikan sebagai paket portabel (`.zip` tanpa instalasi Python) untuk verifikasi dan audit stand KWH Meter LBKB PLN UP3 Mojokerto.

### Added
- **Distribusi Rilis Mandiri Siap Pakai:** Paket kompilasi `--onedir` (`ARGUS.exe`), skrip peluncur cepat (`Mulai_ARGUS.bat` & `Buka_Panduan_ARGUS.bat`), serta aset antarmuka bersih tanpa file prototipe usang.
- **Dokumentasi & Panduan Operasional Terpadu:** Pembaruan [`README.md`](./README.md) bergambar penuh, diagram vektor 6 langkah ([`Docs/assets/alur_kerja_6_langkah.svg`](./Docs/assets/alur_kerja_6_langkah.svg)), serta panduan teks [`PETUNJUK_PENGGUNAAN_ARGUS.txt`](./PETUNJUK_PENGGUNAAN_ARGUS.txt).
- **Kesesuaian Standar Versi Industri:** Pemisahan tegas antara **Versi Aplikasi (`v1.0.0`)** dan **Versi Bobot AI Vision (`Model V5`)**.

---

## [0.8.0] — 2026-11-18 *(Pra-Rilis: Relokasi Vault, Tutorial Offline & Clean Packaging)*
### Added
- **Relokasi Celengan AI ke `%LOCALAPPDATA%`:** Penyimpanan aktif (`staging/` & `releases/`) dipindahkan ke `%LOCALAPPDATA%\ARGUS_PLN\feedback_vault\` (`src/feedback_vault.py`) dilengkapi migrasi otomatis agar **100% kebal** terhadap proses *repack* EXE, pembaruan aplikasi, maupun tombol *Reset Tabel*.
- **Akses Cepat File Manager (`POST /api/feedback/open-folder`):** Penambahan tombol **Buka Folder Celengan** langsung di dalam modal pengelola agar staf non-IT dan tim IT tidak perlu mencari folder tersembunyi secara manual.
- **Halaman Buku Panduan Visual Interaktif (`/tutorial`):** Rute tutorial khusus (`web_extension/dashboard/tutorial.html`) lengkap dengan *sticky full-width navigation bar*, rincian 6 langkah kerja, panduan 7 kartu KPI, tabel hotkey modal, fitur cetak PDF, serta peluncur `Buka_Panduan_ARGUS.bat`.

### Changed
- **Harmonisasi Header Glass-Blue:** Penyelarasan 3 kartu mini di pojok kanan header (`PANDUAN`, `CELENGAN AI`, dan `ENGINE AI AKTIF`) menjadi bilah *glass-blue* 46px yang serasi dengan warna korporat PLN agar tidak menyaingi hirarki visual 7 kartu KPI utama.
- **Penghapusan Artefak Prototipe Lama:** Meniadakan rute `/simulator`, berkas `simulator.html`, `argus_evaluator.user.js`, dan berkas monolitik `dashboard.html` dari paket distribusi sehingga aplikasi hanya terfokus pada **Dashboard** dan **Tutorial**.

---

## [0.7.0] — 2026-11-13 *(Pra-Rilis: Human-in-the-Loop V2 & Celengan Feedback AI)*
### Added
- **Modal Pratinjau HD (`inspectPhoto`):** Fitur zoom/pan presisi, navigasi papan ketik `←` / `→` yang mengikuti filter & urutan sortir tabel aktif, serta pintasan angka `[1..5]` untuk penetapan vonis instan.
- **Smart Baseline Un-Edit:** Penyimpanan *snapshot* baseline (`data-orig-*`); jika koreksi auditor dikembalikan persis ke pembacaan awal dan catatan AI kosong, status `Dikoreksi` serta antrean vault otomatis dibersihkan.
- **Pemisahan Catatan PLN vs Catatan Evaluasi AI:** Catatan operasional resmi masuk ke ekspor Excel PLN, sedangkan catatan kesalahan model (`Salah Baca Angka`, `Digit Terpotong`, `Rolling Meleset`) disimpan khusus untuk perbaikan model AI.
- **Celengan Feedback AI Persisten (Target 1.000 Kasus):** Pengumpulan otomatis foto asli, *crop* dial meteran, pratinjau Excel manifest, CSV, serta *pre-label* format YOLO (`.txt`) yang terkemas otomatis menjadi berkas ZIP saat genap 1.000 kasus unik (`#modal-vault-manager`).

---

## [0.6.0] — 2026-11-12 *(Pra-Rilis: Enterprise Modular Dashboard & GPU Worker Pool)*
### Added
- **Arsitektur Dashboard Modular (`web_extension/dashboard/`):** Pemecahan antarmuka menjadi komponen Jinja2 (`header.html`, `kpi_cards.html`, `toolbar.html`, `table.html`, `modals.html`, `footer.html`) serta modul JavaScript terpisah.
- **7 Kartu Filter KPI & Pencarian Instan:** Filter sekali klik untuk *Total Sampel*, *Sesuai Match*, *Rolling Digit*, *Beda Stand*, *Perlu Tinjau Ulang*, *Bukan KWH / Nihil*, dan *Dikoreksi Auditor*.
- **Auto-Pairing Rekap ACMT (`POST /api/parse-acmt-excel`):** Pembacaan otomatis berkas `.xlsx`/`.csv` ACMT untuk mencocokkan IDPEL, Nama Pelanggan, Tarif/Daya, dan Stan Lapangan ke foto meteran.
- **Skala Ribuan Foto (Virtual Pagination & Worker Pool GPU):** Paginasi virtual DOM (25/50/100/All) dengan `URL.createObjectURL` untuk efisiensi RAM browser, proteksi anti-duplikasi unggahan (`Skip`/`Overwrite`), dan eksekusi batch paralel adaptif (`/api/system-info`: 4 worker GPU / 2 worker CPU).
- **Packaging Portabel PyInstaller (`build_exe.py`):** Skrip pembungkus `--onedir` lengkap dengan banner cepat, proteksi QuickEdit freeze CMD Windows (`launcher.py`), dan auto-launch browser.

---

## [0.5.0] — 2026-11-07 *(Pra-Rilis: Benchmark Skala Penuh & Model V5)*
### Added
- **Multi-Scale Production Benchmark & Model V5:** Evaluasi menyeluruh pada skala 500, 2.500, 5.000, dan 7.470 sampel membandingkan bobot YOLO generasi `v5` terhadap `v4` (`src/train_finetune.py`).
- **Prototipe Awal Dashboard Korporat & Simulator ACMT:** Tema terang korporat PLN (`#007BB5` / `#FDB913`) beserta endpoint awal `/api/export-audit-excel`.

### Changed
- Penyetelan ambang batas *confidence gate* dan *multi-pass enhancement* (RAW $\rightarrow$ Dehaze CLAHE $\rightarrow$ Bicubic Super-Resolution $\rightarrow$ Deskew) untuk menekan pantulan mika LCD.

### Performance
- Mencapai **3.854 Match (51,59% total dataset / 71,24% pada meter fisik valid)** di seluruh 7.470 sampel produksi lapangan.
- Latensi inferensi rata-rata turun 43,1% menjadi **78,3 ms/meter** pada GPU NVIDIA GeForce RTX 4060 Laptop GPU.

---

## [0.4.0] — 2026-11-05 *(Pra-Rilis: Engine Laporan Excel Resmi & Konsensus Digit)*
### Added
- **Official PLN Audit Excel Engine (`src/audit_excel.py`):** Pembuat laporan Excel resmi standar UP3 Mojokerto berisi 4 baris header legenda eksekutif, pewarnaan baris status, dan rumus aktif `=HYPERLINK(...)` menuju bukti foto.
- **Multi-Candidate Digit Consensus:** Konsensus antar kandidat *bounding box* untuk mencegah pembacaan keliru pada dial mekanis yang memudar.
- **Strict Rolling Digit Guard:** Penanganan deterministik angka drum mekanis setengah berputar (*rolling digit*) dengan toleransi selisih $\pm 1$ s.d. $\pm 2$ kWh.

---

## [0.3.0] — 2026-11-02 *(Pra-Rilis: Kedaulatan Lokal 100% Offline & Anti-Fraud)*
### Added
- **Eliminasi Total Cloud VLM:** Memutus seluruh ketergantungan API pihak ketiga (NVIDIA NIM VLM) demi keamanan data pelanggan PLN, operasional *offline* 100%, dan latensi cepat.
- **Local FastAPI REST Engine (`src/api/server.py`):** Menyediakan endpoint lokal `/predict` (Multipart) dan `/predict-base64` (JSON).
- **Heuristik Anti-Fraud Zero-Counter:** Penolakan otomatis oleh Stage 1 YOLO (`FAIL_COUNTER_NOT_FOUND`) terhadap foto non-meteran (aspal, tanah, jok motor, pagar tertutup) tanpa halusinasi angka tagihan.

---

## [0.2.0] — 2026-10-28 *(Pra-Rilis: Two-Stage YOLO & Penemuan Aturan Anti-Flip)*
### Added
- **Two-Stage YOLO Vision Pipeline:**
  - *Stage 1:* `meter_counter_detector.pt` melokalisasi dan memotong kotak dial/LCD meteran.
  - *Stage 2:* `digit_ocr_detector.pt` mendeteksi kelas digit `0–9` serta titik desimal `dot` (11 kelas) dengan capaian **96,1% mAP@50** setelah menonaktifkan augmentasi flip horizontal/vertikal (*anti-flip discovery* guna menjaga geometri angka asimetris `2, 3, 5, 6, 7`).
- **Spatial Sequence Validator & Decimal Dot Splitter (`src/vision_ai/sequence_arbiter.py`):** Penolakan deretan angka sebatang kara akibat silau dan pemisahan angka bulat kWh di depan tanda desimal sesuai SOP penagihan PLN.

---

## [0.1.0] — 2026-09-26 *(Pra-Rilis: Fondasi Riset & Gatekeeper Kualitas)*
### Added
- **Fondasi Riset Ilmiah & Roadmap MLLC:** Validasi literatur arsitektur *Cascading Multi-Tier* dan roadmap rekayasa 5 fase berstandar IEEE.
- **Gatekeeper Kualitas Citra (`src/vision_ai/quality_filter.py`):** Filter fokus Laplacian Variance pada ROI tengah meteran serta deteksi saturasi silau matahari berbasis ruang warna HSV (`V > 240, S < 30`).
- **Eksperimen Awal Barcode Engine:** Uji awal ekstraksi nomor seri meteran prabayar dengan peningkatan kontras adaptif CLAHE.
