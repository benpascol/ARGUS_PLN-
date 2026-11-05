import os
import sys
import io
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO

# Fix Windows console UTF-8 encoding
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def calculate_roi_blur(image, roi_factor=0.6, blur_threshold=60.0):
    """
    Tier 1: Laplacian Blur Pre-Check pada ROI Meteran (Area Tengah).
    
    Menghitung varians operator Laplacian (Var(L)) pada area tengah (60% gambar),
    menghindari background dinding/aspal/lingkungan agar tidak memicu false sharpness.
    
    Threshold Indikator:
    - Var(L) >= 80 : Citra Sangat Tajam & Fokus (Optimal untuk OCR)
    - 40 <= Var(L) < 80 : Ketajaman Cukup / Sedikit Buram (Masih Dapat Diproses)
    - Var(L) < 40 : Buram Parah / Goyang (Motion Blur / Out of Focus Ekstrem)
    """
    if image is None or image.size == 0:
        return 0.0, True

    h, w = image.shape[:2]
    cx, cy = w // 2, h // 2
    half_w = int(w * roi_factor / 2)
    half_h = int(h * roi_factor / 2)

    roi = image[max(0, cy - half_h):min(h, cy + half_h),
                max(0, cx - half_w):min(w, cx + half_w)]

    if roi.size == 0:
        roi = image

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = float(laplacian.var())
    is_blurry = blur_score < blur_threshold

    return round(blur_score, 1), is_blurry

def detect_glare(crop_img, v_thresh=240, s_thresh=30, glare_limit=0.20):
    """
    Mendeteksi apakah crop counter box tertutup silau matahari (glare overexposure).
    Glare diidentifikasi dari piksel dengan intensitas Value tinggi (V > v_thresh)
    dan Saturation rendah (S < s_thresh) alias putih murni ter-klip.
    """
    if crop_img is None or crop_img.size == 0:
        return False, 0.0

    hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    glare_mask = (v > v_thresh) & (s < s_thresh)
    glare_pixels = np.sum(glare_mask)
    total_pixels = crop_img.shape[0] * crop_img.shape[1]

    glare_ratio = float(glare_pixels / total_pixels) if total_pixels > 0 else 0.0
    is_glare_severe = glare_ratio > glare_limit
    return is_glare_severe, glare_ratio

def dehaze_crop_clahe(crop_img, clip_limit=3.0, tile_grid=(8, 8)):
    """
    Filter Dehazing / Penyelamat Kabut & Lensa Berminyak (CLAHE Luminance):
    Menggunakan CLAHE pada kanal Luminance (L) dalam ruang warna LAB
    untuk mengangkat gradien tepi angka yang tertutup film kabut / minyak tanpa meledakkan noise warna.
    """
    if crop_img is None or crop_img.size == 0:
        return crop_img
    lab = cv2.cvtColor(crop_img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    l_enhanced = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l_enhanced, a, b]), cv2.COLOR_LAB2BGR)

def enhance_small_crop(crop_img, min_height=55):
    """
    Super-Resolution & Unsharp Contrast untuk Krop Kecil (CANNET & Meter Dial Sempit):
    Secara fisik, meteran CANNET atau pemotretan jarak jauh menghasilkan counter box
    dengan tinggi < 55 piksel (misal 35-40 px). Pada resolusi rendah tersebut, garis horizontal
    bawah angka '2' dan lekukan '5' hanya setebal 1-2 piksel dan rentan tertelan bayangan bingkai bawah.
    
    Langkah:
    1. Jika tinggi crop < min_height:
       Upscaling 2.0x dengan Bicubic Interpolation (cv2.INTER_CUBIC) untuk merekonstruksi gradien sub-piksel.
    2. Adaptive Local Contrast Enhancement (CLAHE) pada kanal Luminance (L) untuk mengangkat kontur angka.
    3. Unsharp Masking halus (weight=1.4, blur=-0.4) untuk mempertegas sudut dan kaki datar angka 2.
    """
    if crop_img is None or crop_img.size == 0:
        return crop_img, 1.0, False

    h, w = crop_img.shape[:2]
    if h >= min_height:
        return crop_img, 1.0, False

    scale = 2.0
    up = cv2.resize(crop_img, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # CLAHE Luminance
    lab = cv2.cvtColor(up, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(4, 4))
    l_clahe = clahe.apply(l)
    bgr_clahe = cv2.cvtColor(cv2.merge([l_clahe, a, b]), cv2.COLOR_LAB2BGR)
    
    # Unsharp Masking
    blurred = cv2.GaussianBlur(bgr_clahe, (0, 0), sigmaX=1.5)
    unsharp = cv2.addWeighted(bgr_clahe, 1.4, blurred, -0.4, 0)
    
    return unsharp, scale, True

def iou_2d(b1, b2):
    """
    Menghitung Intersection over Union (IoU) 2D antara dua bounding box (x1, y1, x2, y2).
    """
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
    a2 = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0

def deduplicate_spatial_2d(detected_digits, iou_thresh=0.40):
    """
    Deduplikasi Spasial 2D Agnostik (Aman untuk Foto Miring / Tilted & Titik Desimal):
    Secara fisik, dua angka hanya dianggap 'kembar bayangan' pada roda/layar yang sama
    jika tumpang tindih secara NYATA pada KEDUA sumbu (X dan Y) via IoU 2D.
    
    Fitur Kunci:
    1. Menggunakan 2D IoU, BUKAN overlap X 1D saja, sehingga angka yang tersusun
       diagonal miring (seperti Kasus 18 dan 20) tidak saling memakan.
    2. Karakter titik desimal ('dots', 'dot') diproteksi agar tidak dimakan oleh angka besar di sekitarnya.
    """
    if len(detected_digits) <= 1:
        return detected_digits

    dot_boxes = [d for d in detected_digits if d.get("digit") in ("dots", "dot", ".", ",")]
    number_boxes = [d for d in detected_digits if d.get("digit") not in ("dots", "dot", ".", ",")]

    # 1. Deduplikasi number boxes via 2D IoU
    by_conf = sorted(number_boxes, key=lambda d: d["conf"], reverse=True)
    kept_numbers = []
    for cand in by_conf:
        cand_box = (cand["x1"], cand["y1"], cand["x2"], cand["y2"])
        overlap = False
        for k in kept_numbers:
            k_box = (k["x1"], k["y1"], k["x2"], k["y2"])
            if iou_2d(cand_box, k_box) > iou_thresh:
                overlap = True
                break
        if not overlap:
            kept_numbers.append(cand)

    # 2. Deduplikasi dots via 2D IoU
    by_conf_dots = sorted(dot_boxes, key=lambda d: d["conf"], reverse=True)
    kept_dots = []
    for cand in by_conf_dots:
        cand_box = (cand["x1"], cand["y1"], cand["x2"], cand["y2"])
        overlap = False
        for k in kept_dots:
            k_box = (k["x1"], k["y1"], k["x2"], k["y2"])
            if iou_2d(cand_box, k_box) > iou_thresh:
                overlap = True
                break
        if not overlap:
            kept_dots.append(cand)

    all_kept = kept_numbers + kept_dots
    return sorted(all_kept, key=lambda d: (d["x1"] + d["x2"]) / 2.0)

def filter_collinear_adaptive(detected_digits, crop_h, max_deviation_ratio=0.70):
    """
    Collinear Spatial Filter Adaptif (Mendukung Teks Datar maupun Miring / Tilted):
    Secara fisik, seluruh roda angka meteran atau layar LCD tersusun pada satu garis lurus.
    Namun jika petugas memotret dengan kamera miring (sudut ~10-40 derajat seperti Kasus 18 & 20),
    garis tersebut menjadi miring linier Y = a*X + b, bukan datar konstan Y = c.
    
    Langkah:
    1. Melakukan regresi linier tren slope pada titik tengah (center X, center Y) seluruh digit.
    2. Menghitung residual jarak vertikal (|Y - Y_trend|).
    3. Kotak noise / sekrup di luar jalur garis dibuang, sementara angka miring tetap utuh.
    """
    if len(detected_digits) < 3:
        return detected_digits

    digit_boxes = [d for d in detected_digits if d.get("digit") not in ("dots", "dot", ".", ",")]
    dot_boxes = [d for d in detected_digits if d.get("digit") in ("dots", "dot", ".", ",")]

    if len(digit_boxes) < 3:
        return detected_digits

    xs = np.array([(d["x1"] + d["x2"]) / 2.0 for d in digit_boxes])
    ys = np.array([(d["y1"] + d["y2"]) / 2.0 for d in digit_boxes])
    heights = np.array([d["y2"] - d["y1"] for d in digit_boxes])
    median_h = float(np.median(heights))
    y_tolerance = max(median_h * max_deviation_ratio, 0.22 * crop_h)

    # Coba linear trendline fit jika sebaran X cukup lebar (> 15 px)
    if len(xs) >= 3 and (np.max(xs) - np.min(xs)) > 15:
        slope, intercept = np.polyfit(xs, ys, 1)
        y_trend = slope * xs + intercept
        residuals = np.abs(ys - y_trend)
        
        # Jika kemiringan wajar (slope < 0.90 alias sudut kemiringan < ~42 derajat)
        if abs(slope) < 0.90:
            valid_digits = [d for i, d in enumerate(digit_boxes) if residuals[i] <= y_tolerance]
        else:
            median_yc = float(np.median(ys))
            valid_digits = [d for d in digit_boxes if abs(((d["y1"] + d["y2"]) / 2.0) - median_yc) <= y_tolerance]
    else:
        median_yc = float(np.median(ys))
        valid_digits = [d for d in digit_boxes if abs(((d["y1"] + d["y2"]) / 2.0) - median_yc) <= y_tolerance]

    # Validasi dots: harus berada dekat baseline tren garis angka
    if valid_digits and dot_boxes:
        valid_xs = np.array([(d["x1"] + d["x2"]) / 2.0 for d in valid_digits])
        valid_ys = np.array([(d["y1"] + d["y2"]) / 2.0 for d in valid_digits])
        slope, intercept = np.polyfit(valid_xs, valid_ys, 1) if len(valid_xs) >= 2 else (0.0, np.median(valid_ys))
        
        for dot in dot_boxes:
            dot_xc = (dot["x1"] + dot["x2"]) / 2.0
            dot_yc = (dot["y1"] + dot["y2"]) / 2.0
            expected_yc = slope * dot_xc + intercept
            if abs(dot_yc - expected_yc) <= (1.3 * median_h):
                valid_digits.append(dot)

    return sorted(valid_digits, key=lambda d: (d["x1"] + d["x2"]) / 2.0)


def validate_reading_sequence(detected_digits, crop_w, crop_h):
    """
    Two-Layer Sequence, Inter-Digit Gap & Spatial Validator (Sistem Triage 3 Warna):
    🟢 HIJAU  : SUKSES_ANALOG (5 digit seragam / 4 digit baru) / SUKSES_DIGITAL (Ada dots terverifikasi)
    🟡 KUNING : PERLU_TRIAGE / AMBIGU (Confidence rendah < 0.50, jeda abnormal, atau digit parsial)
    🔴 MERAH  : STAND_TIDAK_LENGKAP / ANOMALI (Digit < 4 dan span sempit akibat silau)
    """
    if not detected_digits:
        return {
            "is_valid": False,
            "stand_baca": None,
            "raw_display": "-",
            "status": "STAND_KOSONG",
            "tier_color": "RED",
            "meter_type": "unknown",
            "span_ratio": 0.0,
            "reason": "Tidak ada digit yang terdeteksi di kotak counter."
        }

    # Urutkan berdasarkan koordinat center X (kiri ke kanan)
    sorted_digits = sorted(detected_digits, key=lambda d: (d["x1"] + d["x2"]) / 2.0)
    raw_tokens = [d["digit"] for d in sorted_digits]

    # Hitung horizontal span ratio (X_max - X_min) / crop_w
    min_x = min(d["x1"] for d in sorted_digits)
    max_x = max(d["x2"] for d in sorted_digits)
    span_ratio = float((max_x - min_x) / crop_w) if crop_w > 0 else 0.0

    # 1. LAPISAN 1: ANALISIS CONFIDENCE FLOOR
    # Filter keyakinan numerik (angka non-titik): Jika ada digit dengan confidence < 0.50,
    # baik meter analog maupun digital wajib ditriage agar tidak menghasilkan angka tebakan salah.
    digit_confs = [d.get("conf", 0.0) for d in sorted_digits if d.get("digit") not in ("dots", "dot", ".", ",")]
    min_digit_conf = min(digit_confs) if digit_confs else 0.0
    num_tokens = len(sorted_digits)

    if min_digit_conf < 0.50:
        return {
            "is_valid": False,
            "stand_baca": None,
            "raw_display": "".join(raw_tokens),
            "status": "DIGIT_AMBIGU",
            "tier_color": "YELLOW",
            "meter_type": "ambigu_low_conf",
            "span_ratio": span_ratio,
            "reason": f"Terdeteksi digit ambigu dengan keyakinan rendah ({min_digit_conf:.2f} < 0.50). Wajib verifikasi petugas."
        }

    # 2. LAPISAN 2: CEK KARAKTER TITIK / KOMA DESIMAL ('dots', 'dot', '.')
    dot_boxes = [d for d in sorted_digits if d.get("digit") in ("dots", "dot", ".", ",")]
    if dot_boxes:
        # Jika terdeteksi lebih dari satu titik (seperti noise gap), pilih titik dengan confidence tertinggi
        best_dot = max(dot_boxes, key=lambda d: d.get("conf", 0.0))
        dot_idx = sorted_digits.index(best_dot)
        integer_tokens = [d["digit"] for d in sorted_digits[:dot_idx] if d.get("digit") not in ("dots", "dot", ".", ",")]
        decimal_tokens = [d["digit"] for d in sorted_digits[dot_idx+1:] if d.get("digit") not in ("dots", "dot", ".", ",")]
        stand_baca = "".join(integer_tokens) if integer_tokens else "0"
        raw_display = f"{''.join(integer_tokens)}.{''.join(decimal_tokens)}"
        
        return {
            "is_valid": True,
            "stand_baca": stand_baca,
            "raw_display": raw_display,
            "status": "SUKSES_DIGITAL",
            "tier_color": "GREEN",
            "meter_type": "digital",
            "span_ratio": span_ratio,
            "reason": f"Meter digital valid dengan titik desimal (Layar: {raw_display} -> Stand PLN: {stand_baca})."
        }

    has_abnormal_gap = False
    max_gap_val = 0.0

    if num_tokens >= 2:
        gaps = [sorted_digits[i+1]["x1"] - sorted_digits[i]["x2"] for i in range(num_tokens - 1)]
        digit_widths = [sorted_digits[i]["x2"] - sorted_digits[i]["x1"] for i in range(num_tokens)]
        avg_digit_w = np.mean(digit_widths) if digit_widths else 20.0
        avg_gap = np.mean(gaps) if gaps else 5.0
        max_gap_val = max(gaps) if gaps else 0.0

        if max_gap_val > max(1.8 * avg_gap, 0.6 * avg_digit_w):
            has_abnormal_gap = True

    # 3. EVALUASI TRIAGE: HIJAU vs KUNING vs MERAH

    # KASUS MERAH (Silau Ekstrem / Angka Sebatang Kara):
    if num_tokens < 4 and span_ratio < 0.35:
        return {
            "is_valid": False,
            "stand_baca": None,
            "raw_display": "".join(raw_tokens),
            "status": "STAND_TIDAK_LENGKAP",
            "tier_color": "RED",
            "meter_type": "analog_parsial",
            "span_ratio": span_ratio,
            "reason": f"Hanya terdeteksi {num_tokens} digit dengan span coverage {span_ratio*100:.1f}% (<35%). Indikasi silau / angka terpotong."
        }

    # KASUS KUNING (Jeda Renggang Abnormal seperti Layar Koma Samar):
    if has_abnormal_gap:
        return {
            "is_valid": False,
            "stand_baca": None,
            "raw_display": "".join(raw_tokens),
            "status": "PERLU_ANALISIS_MANUAL",
            "tier_color": "YELLOW",
            "meter_type": "digital_ambigu",
            "span_ratio": span_ratio,
            "reason": f"Terdeteksi jeda renggang abnormal ({max_gap_val:.1f}px). Indikasi layar digital dengan koma samar atau angka terpotong."
        }

    # KASUS HIJAU 6-DIGIT (5 Digit Hitam + 1 Digit Merah Desimal PLN):
    if num_tokens == 6 and span_ratio >= 0.55:
        stand_baca = "".join(raw_tokens[:5])
        desimal_digit = raw_tokens[5]
        raw_display = f"{stand_baca}.{desimal_digit}"
        return {
            "is_valid": True,
            "stand_baca": stand_baca,
            "raw_display": raw_display,
            "status": "SUKSES_ANALOG_DESIMAL",
            "tier_color": "GREEN",
            "meter_type": "analog_6d",
            "span_ratio": span_ratio,
            "reason": f"Meter analog 6 digit terverifikasi (5 digit utama: {stand_baca}, digit ke-6 '{desimal_digit}' adalah desimal roda merah)."
        }

    # KASUS HIJAU 4-DIGIT (Meter Baru / Ganti Meter):
    if num_tokens == 4 and span_ratio >= 0.40:
        left_gap_ratio = float(min_x / crop_w) if crop_w > 0 else 0.0
        right_gap_ratio = float((crop_w - max_x) / crop_w) if crop_w > 0 else 0.0

        # Jika ada jeda kosong lebar (>18%) di sisi kiri, indikasi digit pertama tidak terbaca
        if left_gap_ratio > 0.18:
            return {
                "is_valid": False,
                "stand_baca": None,
                "raw_display": "".join(raw_tokens),
                "status": "STAND_TIDAK_LENGKAP",
                "tier_color": "YELLOW",
                "meter_type": "analog_4d_asimetris_kiri",
                "span_ratio": span_ratio,
                "reason": f"Terdeteksi 4 digit dengan jeda kosong lebar di sisi kiri ({left_gap_ratio*100:.1f}%). Indikasi digit pertama tidak terbaca / terpotong."
            }

        # Jika ada jeda kosong lebar (>18%) di sisi kanan, indikasi digit terakhir terhalang
        if right_gap_ratio > 0.18:
            return {
                "is_valid": False,
                "stand_baca": None,
                "raw_display": "".join(raw_tokens),
                "status": "OBSTRUKSI_FISIK",
                "tier_color": "YELLOW",
                "meter_type": "analog_4d_asimetris_kanan",
                "span_ratio": span_ratio,
                "reason": f"Terdeteksi 4 digit dengan jeda kosong lebar di sisi kanan ({right_gap_ratio*100:.1f}%). Indikasi digit terakhir tertutup."
            }

        stand_baca = "".join(raw_tokens)
        return {
            "is_valid": True,
            "stand_baca": stand_baca,
            "raw_display": stand_baca,
            "status": "SUKSES_ANALOG_4D",
            "tier_color": "GREEN",
            "meter_type": "analog_4d",
            "span_ratio": span_ratio,
            "reason": f"Stand analog 4 digit rapat terverifikasi ({stand_baca})."
        }

    # KASUS KUNING (Jumlah Digit Bukan 4, 5, atau 6):
    if num_tokens not in (4, 5, 6):
        return {
            "is_valid": False,
            "stand_baca": None,
            "raw_display": "".join(raw_tokens),
            "status": "OBSTRUKSI_FISIK",
            "tier_color": "YELLOW",
            "meter_type": "jumlah_digit_non_standar",
            "span_ratio": span_ratio,
            "reason": f"Terdeteksi {num_tokens} digit tanpa titik (non-standar). Indikasi obstruksi fisik atau angka terpotong."
        }

    # KASUS HIJAU (Meter Analog 5 Digit Standar PLN, Rapat & Seragam):
    stand_baca = "".join(raw_tokens)
    return {
        "is_valid": True,
        "stand_baca": stand_baca,
        "raw_display": stand_baca,
        "status": "SUKSES_ANALOG",
        "tier_color": "GREEN",
        "meter_type": "analog",
        "span_ratio": span_ratio,
        "reason": f"Stand analog 5 digit resmi PLN terverifikasi akurat (Span: {span_ratio*100:.1f}%)."
    }

class ArgusVisionPipeline:
    def __init__(self, counter_model_path=None, digit_model_path=None):
        base_dir = Path(__file__).resolve().parent.parent.parent
        v4_path = base_dir / "models" / "digit_ocr_detector_v4.pt"
        default_digit = v4_path if v4_path.is_file() else (base_dir / "models" / "digit_ocr_detector.pt")

        self.counter_model_path = counter_model_path or (base_dir / "models" / "meter_counter_detector.pt")
        self.digit_model_path = digit_model_path or default_digit

        if not Path(self.counter_model_path).exists():
            raise FileNotFoundError(f"Model Counter tidak ditemukan di: {self.counter_model_path}")
        if not Path(self.digit_model_path).exists():
            raise FileNotFoundError(f"Model Digit tidak ditemukan di: {self.digit_model_path}")

        print("🔄 Memuat Model AI ARGUS...")
        print(f"   - Model 1 (Counter) : {Path(self.counter_model_path).name}")
        print(f"   - Model 2 (Digit)   : {Path(self.digit_model_path).name}")
        self.counter_model = YOLO(str(self.counter_model_path))
        self.digit_model = YOLO(str(self.digit_model_path))
        print("✅ Kedua Model Siap Digunakan!\n")
        print("✅ Kedua Model Siap Digunakan!")

    def predict_image(self, image_input, output_dir=None, padding_ratio=0.03):
        if isinstance(image_input, (str, Path)):
            image_path = Path(image_input)
            img = cv2.imread(str(image_path))
            image_name = image_path.name
            stem = image_path.stem
        elif isinstance(image_input, np.ndarray):
            img = image_input
            image_name = "in_memory_image.jpg"
            stem = "in_memory_image"
        else:
            return {"status": "ERROR", "tier_color": "RED", "message": f"Tipe input tidak didukung: {type(image_input)}"}

        if img is None or img.size == 0:
            return {"status": "ERROR", "tier_color": "RED", "message": "Gagal membaca matriks citra (None atau 0 piksel)."}

        h_orig, w_orig = img.shape[:2]

        # TIER 1: LAPLACIAN BLUR PRE-CHECK PADA ROI METERAN (Area Tengah)
        blur_score, is_blurry = calculate_roi_blur(img, roi_factor=0.6, blur_threshold=60.0)

        # TAHAP 1: DETEKSI KOTAK COUNTER RODA ANGKA (Model 1)
        counter_results = self.counter_model.predict(img, conf=0.30, verbose=False)
        counter_boxes = counter_results[0].boxes

        if len(counter_boxes) == 0:
            msg = "Kotak roda angka (stan_meter) tidak terdeteksi pada citra."
            if is_blurry:
                msg += f" Citra terindikasi buram/goyang (Skor Blur: {blur_score} < 60)."
            return {
                "status": "FAIL_COUNTER_NOT_FOUND",
                "tier_color": "RED",
                "message": msg,
                "image_name": image_name,
                "stand_baca": None,
                "blur_score": blur_score,
                "is_blurry": is_blurry
            }

        # Ambil kotak counter dengan confidence tertinggi
        best_box_idx = int(counter_boxes.conf.argmax())
        box_coords = counter_boxes.xyxy[best_box_idx].cpu().numpy()
        counter_conf = float(counter_boxes.conf[best_box_idx].cpu().numpy())

        x1, y1, x2, y2 = box_coords
        box_w = x2 - x1
        box_h = y2 - y1

        # Tambahkan sedikit padding agar tepi angka terluar tidak terpotong
        pad_x = int(box_w * padding_ratio)
        pad_y = int(box_h * padding_ratio)
        crop_x1 = max(0, int(x1 - pad_x))
        crop_y1 = max(0, int(y1 - pad_y))
        crop_x2 = min(w_orig, int(x2 + pad_x))
        crop_y2 = min(h_orig, int(y2 + pad_y))

        crop_img = img[crop_y1:crop_y2, crop_x1:crop_x2].copy()
        if crop_img.size == 0:
            return {"status": "ERROR", "tier_color": "RED", "message": "Crop area berukuran 0 piksel."}

        # GUARD: RESOLUSI KROP SANGAT RENDAH (FOTO DARI JARAK TERLALU JAUH)
        if crop_img.shape[0] < 22:
            return {
                "status": "RESOLUSI_TERLALU_RENDAH",
                "tier_color": "YELLOW",
                "is_valid": False,
                "image_name": image_name,
                "reading": None,
                "stand_baca": None,
                "raw_display": "-",
                "meter_type": "resolusi_rendah",
                "num_digits": 0,
                "counter_conf": counter_conf,
                "counter_box": [int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)],
                "crop_shape": [int(crop_img.shape[0]), int(crop_img.shape[1])],
                "avg_digit_conf": 0.0,
                "blur_score": blur_score,
                "is_blurry": is_blurry,
                "dial_blur_score": 0.0,
                "dehazed_blur_score": 0.0,
                "dehaze_rescued": False,
                "small_crop_enhanced": False,
                "glare_percentage": 0.0,
                "span_ratio": 0.0,
                "reason": f"Resolusi krop sangat rendah ({crop_img.shape[0]}px). Foto diambil terlalu jauh.",
                "digits_detail": [],
                "saved_paths": {}
            }

        # TAHAP 1B: BENTENG BLUR (COUNTER ROI BLUR CHECK & DEHAZE CANDIDATE)
        dial_blur_score, dial_is_blurry = calculate_roi_blur(crop_img, roi_factor=1.0, blur_threshold=35.0)
        saved_paths = {}

        # Deteksi kondisi kabut / lensa berminyak
        is_low_blur = dial_is_blurry or dial_blur_score < 35.0
        dehaze_rescued = False
        is_scaled = False

        # TAHAP 2: BENTENG SILAU (GLARE & OVEREXPOSURE GATEKEEPER)
        is_glare_severe, glare_ratio = detect_glare(crop_img, v_thresh=240, s_thresh=30, glare_limit=0.20)

        if is_glare_severe:
            annotated_full = img.copy()
            cv2.rectangle(annotated_full, (crop_x1, crop_y1), (crop_x2, crop_y2), (0, 0, 255), 3)
            alert_text = f"GLARE ANOMALY ({glare_ratio*100:.1f}%)"
            cv2.putText(annotated_full, alert_text, (crop_x1, max(30, crop_y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2, cv2.LINE_AA)

            if output_dir:
                out_path = Path(output_dir)
                out_path.mkdir(parents=True, exist_ok=True)
                full_save_file = out_path / f"result_full_{stem}.jpg"
                crop_save_file = out_path / f"result_crop_{stem}.jpg"
                cv2.imwrite(str(full_save_file), annotated_full)
                cv2.imwrite(str(crop_save_file), crop_img)
                saved_paths["full_result"] = str(full_save_file)
                saved_paths["crop_result"] = str(crop_save_file)

            return {
                "status": "ANOMALI_GLARE_TERHALANG",
                "tier_color": "RED",
                "image_name": image_name,
                "stand_baca": None,
                "reading": None,
                "blur_score": blur_score,
                "is_blurry": is_blurry,
                "dial_blur_score": dial_blur_score,
                "dehazed_blur_score": 0.0,
                "glare_percentage": round(glare_ratio * 100, 2),
                "counter_conf": counter_conf,
                "counter_box": [int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)],
                "crop_shape": [int(crop_img.shape[0]), int(crop_img.shape[1])],
                "num_digits": 0,
                "reason": f"Silau matahari ekstrem menutupi {glare_ratio*100:.1f}% area counter. Tolak untuk billing.",
                "saved_paths": saved_paths
            }

        # Helper internal: Pipeline OCR (TTA Multi-Scale + Spatial Filter + Validator)
        def run_digit_pipeline(target_crop):
            d_res = self.digit_model.predict(
                target_crop, conf=0.08, augment=True, verbose=False
            )
            d_boxes = d_res[0].boxes
            raw_digits = []
            if len(d_boxes) > 0:
                xyxy_list = d_boxes.xyxy.cpu().numpy()
                conf_list = d_boxes.conf.cpu().numpy()
                cls_list = d_boxes.cls.cpu().numpy()

                for i in range(len(d_boxes)):
                    dx1, dy1, dx2, dy2 = xyxy_list[i]
                    d_conf = float(conf_list[i])
                    d_cls = int(cls_list[i])
                    digit_char = self.digit_model.names.get(d_cls, str(d_cls))

                    if digit_char in ("dots", "dot", ".", ","):
                        if d_conf < 0.10:
                            continue
                    else:
                        if d_conf < 0.20:
                            continue

                    raw_digits.append({
                        "x1": dx1,
                        "y1": dy1,
                        "x2": dx2,
                        "y2": dy2,
                        "conf": d_conf,
                        "digit": digit_char
                    })

            dedup = deduplicate_spatial_2d(raw_digits, iou_thresh=0.40)
            collinear = filter_collinear_adaptive(dedup, crop_h=target_crop.shape[0], max_deviation_ratio=0.70)
            val = validate_reading_sequence(
                collinear,
                crop_w=target_crop.shape[1],
                crop_h=target_crop.shape[0]
            )
            avg_conf = np.mean([d["conf"] for d in collinear]) if collinear else 0.0
            return val, collinear, avg_conf

        # TAHAP 3: STRATEGI DUA TAHAP (RAW FIRST, OPPORTUNISTIC DEHAZE FALLBACK)
        # Tahap 3A: Coba citra krop asli (RAW) terlebih dahulu untuk menghindari distorsi kontras
        validation, detected_digits, avg_digit_conf = run_digit_pipeline(crop_img)
        active_crop = crop_img
        dehaze_rescued = False
        dehazed_blur_score = dial_blur_score

        # Tahap 3B: Jika RAW tidak menghasilkan pembacaan valid (HIJAU) dan citra buram/kabut,
        # aktifkan jalur penyelamat kabut (Opportunistic Dehaze CLAHE)
        if not (validation.get("is_valid") and validation.get("tier_color") == "GREEN") and is_low_blur:
            c_dehaze = dehaze_crop_clahe(crop_img, clip_limit=3.0, tile_grid=(8, 8))
            val_dehaze, det_dehaze, conf_dehaze = run_digit_pipeline(c_dehaze)
            dehazed_blur_score, _ = calculate_roi_blur(c_dehaze, roi_factor=1.0, blur_threshold=35.0)

            if val_dehaze.get("is_valid") and val_dehaze.get("tier_color") == "GREEN" and conf_dehaze >= 0.65:
                validation = val_dehaze
                detected_digits = det_dehaze
                avg_digit_conf = conf_dehaze
                active_crop = c_dehaze
                dehaze_rescued = True
                validation["reason"] = (
                    f"Penyelamatan Kabut / Dehaze Sukses (Skor Blur Awal: {dial_blur_score:.1f} -> {dehazed_blur_score:.1f}, "
                    f"Conf: {avg_digit_conf:.2f}). Stand PLN: {validation['stand_baca']}."
                )

        # Jika citra buram dan upaya penyelamatan kabut tidak menghasilkan digit valid
        if is_low_blur and not dehaze_rescued and not (validation.get("is_valid") and validation.get("tier_color") == "GREEN"):
            annotated_full = img.copy()
            cv2.rectangle(annotated_full, (crop_x1, crop_y1), (crop_x2, crop_y2), (0, 0, 255), 3)
            alert_text = f"BLUR REJECTED (Score: {dial_blur_score:.1f} < 35)"
            cv2.putText(annotated_full, alert_text, (crop_x1, max(30, crop_y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2, cv2.LINE_AA)

            if output_dir:
                out_path = Path(output_dir)
                out_path.mkdir(parents=True, exist_ok=True)
                full_save_file = out_path / f"result_full_{stem}.jpg"
                crop_save_file = out_path / f"result_crop_{stem}.jpg"
                cv2.imwrite(str(full_save_file), annotated_full)
                cv2.imwrite(str(crop_save_file), crop_img)
                saved_paths["full_result"] = str(full_save_file)
                saved_paths["crop_result"] = str(crop_save_file)

            return {
                "status": "REJECTED_BLUR",
                "tier_color": "RED",
                "image_name": image_name,
                "stand_baca": None,
                "reading": None,
                "blur_score": blur_score,
                "is_blurry": True,
                "dial_blur_score": dial_blur_score,
                "dehazed_blur_score": round(dehazed_blur_score, 1),
                "glare_percentage": 0.0,
                "counter_conf": counter_conf,
                "counter_box": [int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)],
                "crop_shape": [int(crop_img.shape[0]), int(crop_img.shape[1])],
                "num_digits": len(detected_digits),
                "reason": f"Fokus citra counter buram / goyang (Skor: {dial_blur_score:.1f} < 35.0). Upaya penyelamatan Dehaze tidak menghasilkan digit valid.",
                "saved_paths": saved_paths
            }

        # TAHAP 5: VISUALISASI HASIL ANOTASI
        annotated_crop = crop_img.copy()
        colors = [
            (255, 100, 0), (0, 200, 255), (0, 255, 100), (255, 0, 150),
            (200, 0, 255), (0, 150, 255), (255, 255, 0), (0, 255, 255),
            (255, 150, 150), (150, 255, 150)
        ]

        for i, d in enumerate(detected_digits):
            color = colors[int(d["digit"]) % len(colors)] if d["digit"].isdigit() else (0, 255, 255)
            bx1, by1, bx2, by2 = int(d["x1"]), int(d["y1"]), int(d["x2"]), int(d["y2"])
            cv2.rectangle(annotated_crop, (bx1, by1), (bx2, by2), color, 2)
            label_text = f"{d['digit']} ({d['conf']:.2f})"
            cv2.putText(annotated_crop, label_text, (bx1, max(12, by1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

        # Gambar kotak counter pada foto asli sesuai Warna Triage
        annotated_full = img.copy()
        tier = validation.get("tier_color", "RED")
        if tier == "GREEN":
            status_color = (0, 255, 0)       # Hijau
            if dehaze_rescued:
                header_text = f"STAND: {validation['stand_baca']} [DEHAZE RESCUED]"
            else:
                header_text = f"STAND: {validation['stand_baca']} (Conf: {avg_digit_conf:.2f})"
        elif tier == "YELLOW":
            status_color = (0, 215, 255)     # Kuning / Amber
            header_text = f"[AMBIGU] {validation['status']}"
        else:
            status_color = (0, 0, 255)       # Merah
            header_text = f"[REJECTED] {validation['status']}"

        cv2.rectangle(annotated_full, (crop_x1, crop_y1), (crop_x2, crop_y2), status_color, 3)
        cv2.putText(annotated_full, header_text, (crop_x1, max(30, crop_y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, status_color, 2, cv2.LINE_AA)

        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            crop_save_file = out_path / f"result_crop_{stem}.jpg"
            full_save_file = out_path / f"result_full_{stem}.jpg"

            cv2.imwrite(str(crop_save_file), annotated_crop)
            cv2.imwrite(str(full_save_file), annotated_full)
            saved_paths["crop_result"] = str(crop_save_file)
            saved_paths["full_result"] = str(full_save_file)

        return {
            "status": validation["status"],
            "tier_color": validation["tier_color"],
            "is_valid": validation["is_valid"],
            "image_name": image_name,
            "reading": validation["stand_baca"],
            "stand_baca": validation["stand_baca"],
            "raw_display": validation.get("raw_display", str(validation.get("stand_baca") or "-")),
            "meter_type": validation["meter_type"],
            "num_digits": len(detected_digits),
            "counter_conf": counter_conf,
            "counter_box": [int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)],
            "crop_shape": [int(crop_img.shape[0]), int(crop_img.shape[1])],
            "avg_digit_conf": float(avg_digit_conf),
            "blur_score": blur_score,
            "is_blurry": is_blurry,
            "dial_blur_score": dial_blur_score,
            "dehazed_blur_score": round(dehazed_blur_score, 1),
            "dehaze_rescued": dehaze_rescued,
            "small_crop_enhanced": is_scaled,
            "glare_percentage": round(glare_ratio * 100, 2),
            "span_ratio": round(validation["span_ratio"], 3),
            "reason": validation["reason"],
            "digits_detail": detected_digits,
            "saved_paths": saved_paths
        }

def run_benchmark_on_samples():
    base_dir = Path(__file__).resolve().parent.parent.parent
    samples_dir = base_dir / "data" / "samples"
    output_dir = base_dir / "data" / "output" / "e2e_benchmark"

    pipeline = ArgusVisionPipeline()

    sample_images = sorted(list(samples_dir.glob("*.jpg")))
    if not sample_images:
        print("❌ Tidak ditemukan gambar berekstensi .jpg di data/samples!")
        return

    print("\n" + "=" * 105)
    print(f"🔬 BENCHMARK SISTEM TRIAGE ARGUS (HIJAU / KUNING / MERAH) PADA {len(sample_images)} CITRA LAPANGAN")
    print("=" * 105)
    print(f"{'No':<3} | {'Nama File':<26} | {'Blur':<7} | {'Silau':<6} | {'Digit':<5} | {'Hasil Stand':<12} | {'Span':<6} | {'Status Triage'}")
    print("-" * 105)

    for idx, img_path in enumerate(sample_images, 1):
        res = pipeline.predict_image(img_path, output_dir=output_dir)
        blur_str = f"{res.get('blur_score', 0):.0f}"
        glare_str = f"{res.get('glare_percentage', 0):.1f}%"
        span_str = f"{res.get('span_ratio', 0)*100:.0f}%" if res.get('span_ratio') is not None else "-"
        stand_str = str(res.get('stand_baca')) if res.get('stand_baca') is not None else "[DITOLAK]"
        num_d = str(res.get('num_digits', '-'))

        tier = res.get("tier_color", "RED")
        if tier == "GREEN":
            status_display = f"🟢 {res['status']}"
        elif tier == "YELLOW":
            status_display = f"🟡 ⚠️ {res['status']}"
        else:
            status_display = f"🔴 🛑 {res['status']}"

        print(f"{idx:<3} | {res.get('image_name', img_path.name):<26} | {blur_str:<7} | {glare_str:<6} | {num_d:<5} | {stand_str:<12} | {span_str:<6} | {status_display}")

    print("=" * 105)
    print(f"🎉 Selesai! Seluruh visualisasi kotak warna (Hijau/Kuning/Merah) tersimpan di:")
    print(f"📁 {output_dir}")
    print("=" * 105)

if __name__ == "__main__":
    run_benchmark_on_samples()