# 🏛️ STRATEGI ARSITEKTUR, DEPLOYMENT & MLOPS ARGUS
**Proyek:** ARGUS (Automated Recognition & Grid Utility Surveillance)  
**Unit:** PT PLN (Persero) UP3 Mojokerto  
**Dokumen:** Analisis Opsi Arsitektur, Integrasi Web Extension, dan Rencana MLOps  
**Penyusun:** Pascol (Developer Lead) & Tim Teknis ARGUS  
**Tanggal:** Oktober 2026  

---

## 📌 1. Ringkasan Eksekutif & Latar Belakang
Sistem ARGUS dirancang sebagai mesin Quality Control (QC) dan audit otomatis untuk pembacaan meteran listrik (KWh Meter) di lingkungan kerja PT PLN UP3 Mojokerto. Sistem ini mengeliminasi risiko kesalahan penagihan (*fat-finger typo* oleh petugas) serta mendeteksi indikasi anomali/fraud (*tembak stand*).

Dokumen ini disusun untuk memberikan opsi arsitektur teknis dan strategi deployment yang fleksibel untuk didiskusikan bersama pemangku kepentingan (stakeholder) dan tim teknis PLN.

---

## 🖥️ 2. Komparasi Opsi Deployment Backend

Untuk tahap demonstrasi awal, disepakati bahwa sistem dibungkus menjadi **Standalone `.exe`** agar portabel dan mudah diuji coba. Namun, untuk implementasi skala penuh di kantor PLN, terdapat dua opsi utama:

| Parameter Evaluasi | Opsi A: Standalone Windows App (`.exe`) | Opsi B: Central LAN GPU Server (Rekomendasi Skala Penuh) |
| :--- | :--- | :--- |
| **Arsitektur** | Tiap laptop petugas menginstal file `ARGUS_Engine.exe` (Localhost:8000). | 1 Unit PC/Server dengan GPU RTX di kantor UP3; 50 laptop petugas mengakses via IP lokal (`192.168.x.x:8000`). |
| **Kebutuhan Hardware Petugas** | Membutuhkan laptop dengan RAM cukup (8–16 GB) dan idealnya GPU diskrit jika ingin inferensi cepat. | **Sangat Ringan.** Laptop petugas tidak butuh GPU sama sekali (hanya menjalankan Google Chrome). |
| **Beban Instalasi & Pemeliharaan** | Harus meng-copy file `.exe` besar (~1.5 GB berisi runtime PyTorch/CUDA) ke puluhan laptop. Update model harus di-copy manual ke tiap laptop. | **Sangat Mudah & Terpusat.** Instalasi cukup 1 kali di server kantor. Jika ada model baru (V4, V5), cukup update 1 file di server. |
| **Konektivitas Jaringan** | Bisa bekerja offline 100% tanpa internet maupun LAN. | Membutuhkan koneksi ke jaringan Wi-Fi/LAN kantor PLN. |
| **Kecepatan Inferensi** | Tergantung spesifikasi masing-masing laptop (CPU biasa: 200–500 ms). | Sangat Cepat (GPU Server: ~4–10 ms per gambar). |

> 💡 **Rekomendasi Transisi:**
> 1. **Fase Demonstrasi / Pilot:** Gunakan **Opsi A (`.exe`)** agar tim pengembang dapat mendemonstrasikan sistem secara mandiri langsung di depan jajaran manajemen PLN tanpa bergantung pada jaringan kantor.
> 2. **Fase Operasional Penuh:** Beralih ke **Opsi B (LAN Server)** agar puluhan pegawai penagihan dapat bekerja serentak tanpa memberatkan laptop dinas mereka.

---

## 🌐 3. Integrasi dengan Web Extension PLN

Petugas verifikasi billing harian di PLN bekerja menggunakan peramban web (Google Chrome) pada portal ACM/AP2T. Sistem ARGUS diintegrasikan secara non-intrusif:

```text
[Browser Chrome Petugas] (Portal Web ACM)
          │
    (1) Web Extension (argus_evaluator.user.js) membaca elemen <img> foto meter
          │
    (2) Kirim payload foto ke: POST http://[ARGUS_HOST]:8000/predict
          ▼
[ARGUS Backend Engine (FastAPI)]
    - Tier 1: Diagnosa Blur (Laplacian Variance) & Glare (HSV V>240)
    - Stage 1: Deteksi Counter/Dial Box (YOLOv8s)
    - Stage 2: Deteksi Digit & Titik Desimal (YOLOv8s 11-Class)
    - Triage Rules: 🟢 Auto-Approve / 🟡 Manual Review / 🔴 Reject
          │
    (3) Mengembalikan JSON hasil bacaan (Stand, Status, Confidence) dalam <50ms
          ▼
[Browser Chrome Petugas]
    (4) Extension merender visual overlay / badge status di samping foto meter
```

---

## 📊 4. Format Audit Batch & Penanganan File Dinamis (Excel LBKB)

Selain integrasi peramban real-time, sistem melayani audit batch bulanan menggunakan file master LBKB (`.xlsx`):

### A. Penamaan File Unik (Anti-Tabrakan / Anti-Collision)
* Menghindari penggunaan nama file statis (`foto1.jpg`, `bukti.jpg`).
* Sistem menerapkan aturan penamaan berbasis Primary Key database PLN:
  $$\text{Format:} \quad \mathbf{\{IDPEL\}\_\{PERIODE\_BILLING\}\_\{STATUS\}.jpg}$$
  *Contoh:* `513010482910_202512_ANOMALI.jpg`
* Format ini menjamin tidak akan terjadi tumpang tindih data meskipun sistem memproses ratusan ribu foto antar-bulan.

### B. Arsitektur Laporan Excel Audit
* **Baris Data:** Tetap mempertahankan 1 baris per IDPEL pelanggan (tidak mengubah urutan baris data asli PLN).
* **Kolom Baru:** Menambahkan kolom evaluasi AI di sisi kanan data asli:
  * `STAN_ARGUS` (Nilai stand hasil bacaan visi komputer)
  * `STATUS_AUDIT` (🟢 MATCH, 🚨 MISMATCH / TYPO, 🟡 PERLU_CEK, 🔴 REJECT)
  * `CONFIDENCE_SCORE` (Tingkat keyakinan deteksi digit)
  * `CATATAN_DIAGNOSA` (Alasan kegagalan, misal: *Glare pada digit ke-3*, *Stand mundur*, dsb.)
* **Penanganan Gambar di Excel:**
  * Menggunakan **Relative Hyperlink** dalam 1 paket ZIP folder agar tautan bukti foto tidak rusak (*broken link*) saat file Excel dipindahkan ke laptop lain.
  * Opsi penyematan thumbnail mini khusus untuk baris anomali (🚨) agar tim auditor dapat melakukan verifikasi visual seketika tanpa membuka berkas foto satu per satu.

---

## 🔄 5. Strategi Akurasi & MLOps: Active Learning Flywheel

### A. Mengapa Menolak Naive Unsupervised Learning?
Membiarkan model memperbarui bobot (*weights*) secara otomatis tanpa pengawasan pada data baru dapat menimbulkan dua risiko kritis:
1. **Catastrophic Forgetting:** Penurunan akurasi drastis pada model meteran lama akibat adaptasi berlebih terhadap model baru.
2. **Model Poisoning (Feedback Loop):** AI yang salah membaca angka buram akan menganggap halusinasinya benar, merusak akurasi model di masa depan.

### B. Siklus Active Learning dengan Human-in-the-Loop
Sebagai gantinya, ARGUS menerapkan siklus pembelajaran terawasi (*Supervised Continual Learning*):

```text
                       [Foto Meteran Baru]
                                │
                                ▼
                         [ARGUS Vision]
                                │
             ┌──────────────────┴──────────────────┐
     (Keyakinan >= 90%)                     (Keyakinan < 90% / Ambigu)
             │                                     │
             ▼                                     ▼
     🟢 Auto-Approve                     🟡 Triage: Review Petugas
                                                   │
                                                   ▼
                                        [Koreksi Manual Petugas]
                                        (Label Terverifikasi 100%)
                                                   │
                                                   ▼
                                        📁 data/hard_cases/
                                                   │
                                                   ▼
                                   [Fine-Tuning Berkala (10 Epoch)]
                                                   │
                                                   ▼
                                       🚀 Model V4, V5 Terbit!
```

* **Keunggulan:** Dataset pelatihan berikutnya hanya berisi kasus-kasus tersulit (*edge cases* nyata lapangan), membuat model semakin adaptif dan tangguh terhadap berbagai merk meteran baru di Mojokerto.

---

## 🔍 6. Mitigasi Risiko Manipulasi Citra (Anti-Halusinasi)

* **Penolakan Model Generative Super-Resolution:** 
  Model pembesar gambar berbasis Generatif (seperti Real-ESRGAN) **secara tegas tidak digunakan** karena memiliki risiko memanipulasi piksel angka (mengubah angka 6 menjadi 8 atau 5 menjadi 2).
* **Solusi Deterministik:** 
  Sistem hanya menggunakan peningkatan kontras matematis murni (**CLAHE**) dan **Letterbox Resize bawaan YOLOv8** untuk menjaga proporsi geometri angka asli tanpa mengubah data fisis citra.

---

## 📋 7. Agenda Diskusi untuk Rapat Koordinasi PLN
Beberapa poin kunci yang perlu dimintakan masukan dari pihak PLN UP3 Mojokerto:
1. **Preferensi Infrastruktur:** Apakah pihak kantor menyediakan 1 unit PC Server ber-GPU untuk dipakai bersama (Opsi B), ataukah lebih memilih distribusi file `.exe` per laptop (Opsi A)?
2. **Standar Penamaan Foto Lapangan:** Apakah aplikasi mobile pencatat meter (ACM) saat ini sudah menyimpan foto dengan format nama IDPEL, atau masih menggunakan penamaan timestamp/acak dari kamera?
3. **Threshold Tindakan Toleransi:** Untuk kasus pembacaan meteran analog lama yang rol angkanya berada di posisi setengah putaran (transisi angka), berapa batas toleransi pembulatan stand yang berlaku di SOP PLN Mojokerto?

