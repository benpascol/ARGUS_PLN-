# 🔎 ARGUS — Technology & Decision Verification Report
## Audit Independen atas Keputusan Arsitektur Hybrid Multi-Tier

> **Tanggal riset:** 05 Oktober 2026
> **Tujuan:** Memeriksa secara kritis apakah keputusan teknologi ARGUS (OpenCV Laplacian → ZBar / YOLO-Seg + Warp + OCR → YOLO-Cls → VLM Fallback) benar-benar didukung literatur, apakah ada alternatif yang lebih baik, dan apakah ada kasus serupa dengan teknologi berbeda.
> **Sikap dokumen ini:** Jujur, bukan pembenaran. Klaim yang tidak punya bukti ditandai apa adanya.

---

## 1. Tingkat Verifikasi Sumber

Setiap sumber di dokumen ini diberi tingkat verifikasi supaya jelas mana yang boleh dikutip di laporan resmi.

| Kode | Arti |
|:---:|---|
| ✅ **V1** | Halaman sumber dibuka langsung dan isinya diperiksa (judul, penulis, abstrak, DOI cocok). |
| 🔎 **V2** | Keberadaan dan ringkasan isi dikonfirmasi lewat pencarian, tetapi halaman sumber belum dibuka langsung. **Buka sendiri sebelum dikutip di laporan.** |
| ❓ **V3** | Tidak dapat diverifikasi pada sesi ini (akses diblokir 403 atau sitasi terlalu umum). **Jangan dikutip sebelum diperiksa manual.** |

---

## 2. Verdict Ringkas

| # | Keputusan ARGUS | Status | Ringkasan Bukti |
|:---:|---|:---:|---|
| 1 | Pipeline bertahap: deteksi → rektifikasi → pengenalan | ✅ **Didukung kuat** | Laroca et al. (2021) dan Lin et al. (2023) memakai pola yang sama. |
| 2 | Perspective rectification sebelum membaca angka | ✅ **Didukung kuat** | Laroca (2021): *corner detection* untuk merektifikasi area counter. Lin (2023): polygon-YOLOv5 + perspective transformation. |
| 3 | Menolak bacaan *confidence* rendah ke review manual | ✅ **Didukung kuat** | Laroca (2021): recognition rate **> 99%** ketika bacaan berkeyakinan rendah ditolak. |
| 4 | Deteksi blur di tahap awal | 🔶 **Sebagian** | Prinsipnya didukung (Lin 2023 memakai **FFT**). Laplacian dan threshold 80–120 **tidak ditemukan sumbernya**. |
| 5 | YOLO untuk melokalisasi layar LCD | ✅ **Didukung** | Banyak studi memakai YOLOv5/v7/v8/v10 untuk lokalisasi meter digital. |
| 6 | **PaddleOCR bawaan untuk angka 7-segment** | ⚠️ **Belum terbukti** | OCR generik sering bermasalah pada 7-segment. Studi yang berhasil memakai CRNN/CNN/YOLO yang **dilatih khusus**. |
| 7 | ZBar untuk barcode | 🔶 **Sebagian** | Prinsip checksum benar. Klaim "hit-rate < 50%" tidak bersumber. Target pencocokan perlu dikonfirmasi (lihat §7). |
| 8 | VLM sebagai fallback | 🔶 **Sebagian** | Pola cascade didukung. Performa LLaMA 3.2 Vision pada klasifikasi LBKB **belum ada bukti**. |
| 9 | YOLO-Cls / MobileNetV3 untuk rintangan lapangan | ❓ **Hipotesis** | Tidak ditemukan studi domain-spesifik. Klasifikasi citra standar, tetapi butuh data berlabel. |
| 10 | Klaim "hemat token 70–80% / 80–90%" | ❌ **Tidak terverifikasi** | Angka itu estimasi kita sendiri. Harus diukur di Fase 4. |

> [!IMPORTANT]
> **Kesimpulan:** Kerangka besar (cascade + rektifikasi + confidence rejection) **terverifikasi**. Tetapi ada **satu keputusan teknologi yang belum terbukti (PaddleOCR bawaan)**, **tiga angka yang tidak punya sumber**, dan **dua sitasi di dokumen lama yang salah atribusi** (lihat §6).

---

## 3. Kasus Serupa dengan Teknologi Berbeda

Ini jawaban untuk pertanyaan "apakah ada orang dengan kasus berbeda tapi metode sama, dengan teknologi berbeda?".

### 3.1 Laroca et al. (2021) — Kasus paling mirip operasionalnya ✅ V1
- **Judul:** *Towards Image-based Automatic Meter Reading in Unconstrained Scenarios: A Robust and Efficient Approach*
- **Publikasi:** IEEE Access, vol. 9, pp. 67569–67584, 2021. DOI: 10.1109/ACCESS.2021.3077415 (DOI dari hasil pencarian, 🔎 V2). Abstrak dan arXiv [2009.10181](https://arxiv.org/abs/2009.10181) dibuka langsung (✅ V1).
- **Kemiripan dengan ARGUS:**
  - Foto diambil **oleh pegawai perusahaan listrik sendiri di lapangan** (Copel, Brasil), sama seperti petugas catat meter PLN.
  - Kondisi tidak terkontrol: kotoran, pencahayaan beragam, variasi skala, rotasi *in-plane* dan *out-of-plane*.
  - Dataset **Copel-AMR: 12.500 gambar, termasuk 2.500 gambar meter rusak atau tidak terbaca**.
- **Teknologi yang dipakai:** **Tiga jaringan bekerja cascaded**, dengan tahap baru *corner detection and counter classification* yang merektifikasi area counter dan **menolak meter yang tidak terbaca** sebelum tahap pengenalan.
- **Hasil:** Mengungguli semua baseline; recognition rate **> 99%** ketika bacaan berkeyakinan rendah ditolak.
- **Pelajaran untuk ARGUS:**
  1. Arsitektur cascade + rektifikasi + penolakan sudah terbukti pada kasus nyata skala besar.
  2. Kelas "tidak terbaca / rusak" diperlakukan sebagai kelas resmi, mirip kelas `Blur` dan rintangan kita.
  3. **Catatan kehati-hatian:** tipe meter di dataset Brasil belum dipastikan sama dengan LCD 7-segment PLN. Pakai sebagai referensi metodologi, bukan sebagai data latih langsung.

### 3.2 Lin et al. (2023) — Pipeline paling mirip Tier 1 + 2B 🔎 V2
- **Judul:** *Research on Digital Meter Reading Method of Inspection Robot Based on Deep Learning*
- **Publikasi:** Applied Sciences (MDPI), 13(12), 7146, 2023. Penulis: Wenwei Lin, Ziyang Zhao, Jin Tao, Chaoming Lian, Chentao Zhang. (Pengambilan DOI langsung ditolak 403, tetapi keberadaan dan isi dikonfirmasi via pencarian.)
- **Teknologi yang dipakai (urutan pipeline):**
  1. **Deteksi blur dengan FFT**
  2. Restorasi citra buram dengan **jaringan adversarial** (varian DeblurGAN dengan spatial attention)
  3. Ekstraksi area meter dengan **polygon-YOLOv5**, lalu koreksi **perspective transformation**
  4. Pengenalan digit dengan **CRNN**
- **Hasil:** Akurasi **98%**, missing rate **1%**.
- **Pelajaran untuk ARGUS:**
  1. Urutan *blur → lokalisasi poligon → perspective → CRNN* **hampir identik** dengan Tier 1 + Tier 2B kita. Ini validasi terkuat.
  2. Mereka memakai **CRNN yang dilatih**, bukan OCR bawaan.
  3. Mereka memakai **FFT** untuk blur. Di dokumen kita FFT hanya "opsi sekunder". Perlu dibenchmark berdampingan dengan Laplacian.

### 3.3 Haseeb et al. (2024) — Kasus paling mirip konteks bisnisnya ✅ V1
- **Judul:** *Automated Detection and Recognition of Seven-Segment Digits from Electric Meters Utilizing Digital Image Processing and Machine Learning*
- **Publikasi:** VFAST Transactions on Software Engineering, 12(4), 87–98, 2024. DOI: 10.21015/vtse.v12i4.1923 (halaman dibuka langsung).
- **Konteks:** Meter digital 7-segment di Pakistan. Petugas mengambil foto dengan kamera atau smartphone, lalu bacaan dicatat manual untuk penagihan. **Ini persis konteks PLN.**
- **Teknologi yang dipakai:** Lima model dibandingkan: **KNN, Decision Tree, SVM, Random Forest, CNN**, diuji pada data meter nyata. Akurasi sampai **98%**.
- **Pelajaran untuk ARGUS:** Pengenalan digit 7-segment dikerjakan dengan **model yang dilatih pada data 7-segment**, bukan OCR umum.

### 3.4 Imran et al. (2023) — YOLO vs fitur handcrafted 🔎 V2
- **Judul:** *Image-Based Automatic Energy Meter Reading Using Deep Learning*
- **Publikasi:** Computers, Materials & Continua, 74(1), 203–216, 2023. DOI: 10.32604/cmc.2023.029834.
- **Isi:** Membandingkan **YOLO** dengan metode handcrafted untuk ekstraksi teks dan pengenalan digit; dataset 10.000 gambar dengan augmentasi rotasi dan skala; terhubung ke IoT dan GUI untuk penagihan otomatis.
- **Pelajaran untuk ARGUS:** Mendukung pemakaian YOLO dan augmentasi rotasi/skala. **Paper ini tidak membahas Laplacian blur**, sehingga klaim lama di dokumen kita salah (lihat §6).

### 3.5 Laroca et al. (2019) — Dataset dan baseline klasik 🔎 V2
- **Judul:** *Convolutional Neural Networks for Automatic Meter Reading*, Journal of Electronic Imaging, 2019.
- **Isi:** Pipeline dua tahap: **Fast-YOLO** mendeteksi counter, lalu tiga pendekatan CNN mengenali digit. Merilis dataset UFPR-AMR (2.000 gambar beranotasi).
- **Pelajaran untuk ARGUS:** Dua tahap *deteksi → pengenalan* adalah pola dasar bidang ini sejak 2019.

### 3.6 Prinsip cascade biaya: Chen et al. (FrugalGPT) 🔎 V2
- **Judul:** *FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance*, arXiv:2305.05176.
- **Isi:** Model murah dipanggil dulu; jika keyakinan tinggi hasil diterima, jika rendah dieskalasi ke model lebih kuat. Pada eksperimen mereka, biaya turun sampai **98%** dengan performa setara model terbaik.
- **Batasan penting:** Ini studi **LLM teks**, bukan pembacaan meter. Ia mendukung **prinsip** cascade berbasis confidence, **bukan** angka penghematan ARGUS.

### 3.7 Fondasi teknis rektifikasi dan pengenalan 🔎 V2
- **CRNN** (Shi et al., IEEE TPAMI 2017): arsitektur CNN + RNN + CTC yang dapat dilatih end-to-end **tanpa segmentasi per karakter**.
- **ASTER** (Shi et al., IEEE TPAMI 2019): pengenalan teks dengan jaringan rektifikasi (Spatial Transformer) untuk teks miring atau terdistorsi.
- Keduanya menggantikan sitasi "TPAMI 2022/2023" yang terlalu umum di dokumen lama.

---

## 4. Perbandingan Alternatif per Tier

### 4.1 Tier 1 — Deteksi blur
| Opsi | Kelebihan | Kekurangan | Bukti |
|---|---|---|---|
| Laplacian variance (rencana kita) | Sangat cepat, tanpa training | Sensitif ke tekstur background. **Threshold 80–120 tidak bersumber.** | Tidak ditemukan sumber spesifik |
| **FFT** (dipakai Lin 2023) | Terbukti dalam pipeline meter 98% | Lebih mahal dari Laplacian, perlu penentuan ambang | 🔎 V2 |
| Restorasi blur (DeblurGAN) | Menyelamatkan foto buram | Butuh model dan GPU, kompleks | 🔎 V2 (Lin 2023) |

**Rekomendasi:** Benchmark **Laplacian vs FFT** berdampingan di Fase 1.2. Threshold diperlakukan sebagai **hasil kalibrasi**, bukan angka literatur.

### 4.2 Tier 2B — Lokalisasi LCD
| Opsi | Catatan |
|---|---|
| YOLOv8-Seg / polygon-YOLO (rencana kita) | Setara pendekatan Lin 2023 (polygon-YOLOv5). Didukung. |
| *Corner detection* (Laroca 2021) | Pendekatan alternatif yang terbukti untuk rektifikasi. |
| Segmentasi semantik (TransUNet, SwinUnet) | Lebih presisi tetapi lebih berat. Tidak cocok untuk PC kantor tanpa GPU. |

**Rekomendasi:** YOLOv8-Seg tetap layak. Corner detection layak dicoba bila segmentasi terlalu berat.

### 4.3 Tier 2B — Pengenalan angka (keputusan paling kritis)
| Opsi | Kelebihan | Kekurangan | Bukti |
|---|---|---|---|
| **PaddleOCR bawaan** (rencana kita) | Siap pakai, tanpa labeling | **Tidak terbukti** untuk 7-segment. Hasil pencarian menyebut OCR generik sering kesulitan pada font segmen. | ⚠️ Perlu benchmark |
| **CRNN + CTC dilatih khusus** | Dipakai Lin 2023 (98%). Tidak butuh label per digit. | Perlu data latih dan GPU untuk training | 🔎 V2 |
| **YOLO untuk deteksi digit** | Dipakai di rangkaian studi Laroca | Perlu anotasi per digit | 🔎 V2 |
| CNN/SVM/RF klasik | Dipakai Haseeb 2024 (sampai 98%) | Butuh segmentasi digit lebih dulu | ✅ V1 |
| `ssocr` (rule-based 7-segment) | Dibuat khusus untuk 7-segment, sangat ringan | Rapuh pada silau dan blur. Bukan paper jurnal. | Dari hasil pencarian umum |

> [!WARNING]
> Pada dokumen sebelumnya, PaddleOCR digambarkan "tanpa halusinasi" dan "30–50 ms, ±4 MB". **Klaim itu tidak bersumber.** OCR neural tetap bisa salah baca digit. Pengenal angka harus diputuskan lewat **benchmark pada foto PLN sendiri**.

### 4.4 Tier 3 — VLM fallback
- **Risiko halusinasi angka pada VLM** konsisten dengan hasil pencarian: VLM cenderung menghasilkan angka yang "masuk akal" saat tidak bisa membaca jelas. Itu alasan VLM tidak dipakai sebagai pembaca utama.
- **Pola cascade** (model ringan dulu, eskalasi berdasarkan confidence, manusia sebagai pilihan terakhir) sesuai praktik umum dan prinsip FrugalGPT.
- **Yang belum terbukti:** akurasi **LLaMA 3.2 11B Vision** untuk membedakan pagar terkunci, rumah tutup, dan foto fraud pada foto PLN. Ini **hipotesis yang harus diuji di Fase 1.5**, bukan fakta.
- Alternatif: model VLM lain (Gemini, Qwen-VL) atau langsung human-in-the-loop. Pilihan model sebaiknya dibandingkan pada sampel yang sama.

### 4.5 Tier 2C — Klasifikasi rintangan lokal
- Tidak ditemukan studi domain-spesifik untuk klasifikasi pagar/rumah tutup/fraud pada foto catat meter.
- Pendekatan klasifikasi citra dengan model ringan secara teknis standar, tetapi butuh **data berlabel per kelas**.
- Status: **hipotesis**. Strategi aman: mulai dari VLM zero-shot sebagai baseline, kumpulkan hasilnya sebagai label awal, baru latih YOLO-Cls bila VLM terbukti memadai sebagai "guru".

---

## 5. Usulan Desain (Inferensi, Bukan Hasil Literatur)

> [!NOTE]
> Bagian ini adalah **usulan teknis dari analisis**, bukan temuan jurnal. Statusnya hipotesis yang harus diuji.

**Masalah:** CRNN dilatih khusus butuh data berlabel, dan labeling manual mahal.

**Ide:** CRNN dengan CTC loss hanya membutuhkan **gambar crop + string label**, tanpa label per karakter (sifat dasar CRNN, 🔎 V2). Kolom `STAN_BACA` di Excel PLN yang sudah diverifikasi manusia berpotensi menjadi **label string gratis**.

**Yang masih harus dilabeli manual:** hanya **poligon 4 sudut LCD** untuk melatih YOLO-Seg, yaitu jumlah yang jauh lebih kecil daripada anotasi per digit.

**Risiko yang harus diperiksa sebelum dipakai:**
1. `STAN_BACA` hanya bilangan bulat, sedangkan LCD menampilkan desimal (misal `26.84` → `26`). Aturan pemotongan harus eksplisit.
2. *Leading zero* (misal `09.7` → `9`).
3. Kemungkinan salah ketik manusia pada Excel. Perlu pengecekan sampel dulu.
4. Foto di Excel tertanam di kolom `PHOTO` dan di folder `DOkumentasi LBKB/`. Pemetaan `NAMA FILE` ↔ foto harus dipastikan.

---

## 6. Koreksi atas Dokumen Sebelumnya

Pemeriksaan ini menemukan kekeliruan pada dokumen yang kita tulis sendiri. Semua dikoreksi, bukan disembunyikan.

| Klaim lama | Masalah | Koreksi |
|---|---|---|
| CMC 2023 "memvalidasi varians Laplacian ROI" | Paper membahas YOLO vs handcrafted untuk meter digital, bukan Laplacian | Atribusi diganti ke fungsi yang benar (§3.4) |
| "IEEE TPAMI 2022/2023 — Perspective Rectification" | Tanpa judul dan penulis, tidak bisa diverifikasi | Diganti Laroca (2021), Lin (2023), CRNN/ASTER (§3) |
| Threshold Laplacian 80–120 untuk 540×960 "dari literatur" | Tidak ditemukan sumber | Dinyatakan heuristik, wajib dikalibrasi |
| PaddleOCR "tanpa halusinasi, 30–50 ms, ±4 MB" | Tidak bersumber, dan OCR neural bisa salah baca | Dinyatakan perlu benchmark |
| "Hemat token 70–80% / 80–90%" | Estimasi internal | Wajib diukur di Fase 4 |
| ZBar "hit-rate < 50% tanpa preprocessing" | Tidak bersumber | Wajib diukur di Fase 1.3 |
| Few-shot "naik 15–20%" | Tidak bersumber | Dihapus sebagai klaim, diuji di Fase 1.5 |
| REF-04 ICASSP "Synthetic Image Detection" untuk deteksi fraud | Paper tentang citra buatan AI, bukan foto lapangan yang salah objek | Relevansi diturunkan menjadi analogi lemah |
| REF-05 "AI-based visual inspection systems for utility field audits" | Tanpa penulis atau judul pasti | ❓ V3, jangan dikutip |
| REF-06 Barkat (Theseus 2024) | Akses 403, belum terverifikasi | ❓ V3, buka manual sebelum dikutip |

---

## 7. Status Pertanyaan Terbuka & Temuan Empiris Dataset (05 Oktober 2026)

Analisis langsung terhadap 8.126 baris dan ribuan foto pada dataset `12 LBKB Billing Rek 12 2025 copy+foto.xlsx` (277 MB) memberikan jawaban definitif:

1. **Barcode Meter vs IDPEL & Penambahan Kolom Output:**
   - **Fakta:** Barcode yang tercetak pada Smart Meter AMI / SMI-710 / Prabayar adalah **11 Digit Nomor Seri Meter (MSN)**, contohnya `86293576168` (Code 128) dan QR Code `PLN0219000050202586293576168`. Sedangkan di Excel PLN, entitasnya adalah **12 Digit IDPEL** (contoh: `514500420174`). Seringkali petugas menulis manual IDPEL dengan spidol putih di cover mika meteran.
   - **Keputusan Solusi:** Kita menambahkan kolom verifikasi baru pada file output Excel ARGUS:
     - `BARCODE_METER_TERBACA`: Hasil pemindaian ZBar / ZXing-C++ (11 digit).
     - `TIPE_BARCODE`: `Code 128` / `QR Code` / `None`.
     - `STAN_BACA_ARGUS`: Digit stand hasil ekstraksi AI (bilangan bulat).
     - `SELISIH_STAND`: `STAN_BACA_ARGUS - STAN_METER`.
     - `STATUS_AUDIT_ARGUS`: `SESUAI` / `ANOMALI_STAND` / `RUMAH_TUTUP` / `RUMAH_KOSONG` / `PERLU_REVIEW_MANUAL`.
     - `ALASAN_AUDIT`: Penjelasan rinci keputusan AI.
     - Pembacaan barcode 11 digit berfungsi sebagai **Digital Watermark & Bukti Otentik Fisik** bahwa foto yang diunggah benar-benar meteran PLN asli di lapangan, mencegah fraud foto palsu/duplikat.

2. **Logika Pencocokan Stan:**
   - Sistem mengekstrak angka stan dari foto (LCD / Odometer), menuliskannya ke `STAN_BACA_ARGUS`, lalu memvalidasi:
     - Untuk meter normal: `STAN_BACA_ARGUS >= STAN_METER` (stand lalu). Selisih harus bernilai wajar sesuai rata-rata pemakaian historis (`PEMKWH`).
     - Untuk kasus LBKB `KDBACA`:
       - `F` (RUMAH KOSONG): Stand tidak berubah (`STAN_BACA == STAN_METER`, `PEMKWH == 0`), objek foto adalah rumah/pagar.
       - `E` (RUMAH TUTUP): Petugas menaksir stand, objek foto adalah pintu/pagar digembok.
       - `2` (GANTI KWH METER): Stand meter baru dimulai dari angka kecil (misal `32`), `PEMKWH` dihitung dengan formula pergantian khusus PLN.

3. **Aturan Desimal (Kaidah Bisnis PLN Terbukti):**
   - Terverifikasi empiris pada sampel baris 52 (`image73.jpg`): Layar meter menampilkan `32.10 kWh`, namun pada Excel PLN tercatat murni **`32`**.
   - Pada meter analog/mekanik: digit terakhir berbingkai merah adalah desimal (0.1 kWh) dan diabaikan.
   - **Kaidah AI:** Sistem ARGUS wajib membuang digit desimal dan hanya mengambil bilangan bulat (*integer truncation*), serta membuang *leading zero*.

4. **Komposisi Riil 8.126 Baris LBKB:**
   - **80.4% adalah rintangan fisik:** `RUMAH KOSONG` (57.1% / 4.642 baris) dan `RUMAH TUTUP` (23.3% / 1.896 baris). Sebagian besar foto adalah rumah, pagar terkunci, jalan, atau dinding.
   - **19.6% adalah kasus meter fisik:** `GANTI KWH METER` (10.7%), `KWH METER MACET` (4.5%), `DIDALAM BANGUNAN` (2.1%), `METER TINGGI` (1.3%), `METER BURAM/PECAH` (0.8%).
   - Tipe meter: Didominasi pelanggan R1 450 VA (49.1%) & 900 VA (28.4%) yang mayoritas menggunakan **KWH Meter Analog / Mekanik (Roller Drum Odometer)**, dan sebagian Smart Meter digital dengan barcode.

5. **Integritas Resolusi File Mentah:**
   - File `12 LBKB Billing Rek 12 2025 copy+foto.xlsx` (277 MB) menyimpan citra asli resolusi **540×960 JPEG**. Pada resolusi ini, ZXing-C++ berhasil membaca Barcode Code 128 dan QR Code dengan sempurna.
   - File salinan (96 MB) telah mengalami downsampling otomatis oleh Excel menjadi 220×254 PNG sehingga barcode hancur. Seluruh ekstraksi sampel wajib bersumber dari file 277 MB.

---

## 8. Rekomendasi Perubahan Roadmap

1. **Fase 1.4:** ubah dari "uji PaddleOCR" menjadi **benchmark pengenal angka**: PaddleOCR bawaan vs CRNN-CTC (jika data tersedia) vs YOLO digit. Pemenang ditentukan dari data PLN.
2. **Fase 1.2:** tambah **FFT** sebagai pembanding Laplacian.
3. **Fase 1.5:** perlakukan VLM sebagai **baseline yang harus dibuktikan**, bukan solusi final. Ukur akurasi pada kelas pagar, rumah tutup, dan fraud.
4. **Fase 4:** ukur sendiri rasio fallback VLM dan penghematan token. Jangan memakai angka 70–90% sebagai klaim.
5. **Laporan akhir:** kutip hanya sumber berlevel ✅ V1 dan 🔎 V2 yang sudah dibuka manual.

---

## 9. Daftar Referensi

1. Laroca, R., Araujo, A. B., Zanlorensi, L. A., de Almeida, E. C., & Menotti, D. (2021). Towards Image-based Automatic Meter Reading in Unconstrained Scenarios: A Robust and Efficient Approach. *IEEE Access*, 9, 67569–67584. https://doi.org/10.1109/ACCESS.2021.3077415 — arXiv: https://arxiv.org/abs/2009.10181 *(✅ V1 abstrak; DOI 🔎 V2)*
2. Lin, W., Zhao, Z., Tao, J., Lian, C., & Zhang, C. (2023). Research on Digital Meter Reading Method of Inspection Robot Based on Deep Learning. *Applied Sciences*, 13(12), 7146. https://doi.org/10.3390/app13127146 *(🔎 V2; resolve DOI diblokir 403)*
3. Haseeb, H., Hassan, M. T., Iftikhar, A., & Asmat, A. (2024). Automated Detection and Recognition of Seven-Segment Digits from Electric Meters Utilizing Digital Image Processing and Machine Learning. *VFAST Transactions on Software Engineering*, 12(4), 87–98. https://doi.org/10.21015/vtse.v12i4.1923 *(✅ V1)*
4. Imran, M., Anwar, H., Tufail, M., Khan, A., Khan, M., & Ramli, D. A. (2023). Image-Based Automatic Energy Meter Reading Using Deep Learning. *Computers, Materials & Continua*, 74(1), 203–216. https://doi.org/10.32604/cmc.2023.029834 *(🔎 V2)*
5. Laroca, R., et al. (2019). Convolutional Neural Networks for Automatic Meter Reading. *Journal of Electronic Imaging*. *(🔎 V2; volume dan halaman belum dicek)*
6. Chen, L., Zaharia, M., & Zou, J. (2023). FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance. arXiv:2305.05176. *(🔎 V2)*
7. Shi, B., Bai, X., & Yao, C. (2017). An End-to-End Trainable Neural Network for Image-Based Sequence Recognition and Its Application to Scene Text Recognition. *IEEE TPAMI*. *(🔎 V2; volume dan halaman belum dicek)*
8. Shi, B., et al. (2019). ASTER: An Attentional Scene Text Recognizer with Flexible Rectification. *IEEE TPAMI*. *(🔎 V2; volume dan halaman belum dicek)*

> Daftar penulis dan halaman yang ditandai 🔎 V2 berasal dari hasil pencarian. Cocokkan dengan halaman penerbit sebelum masuk daftar pustaka laporan resmi.
