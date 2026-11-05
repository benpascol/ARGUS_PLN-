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

def ioa_min_2d(b1, b2):
    """
    Menghitung Intersection over Minimum Area (IoA) 2D untuk mendeteksi kotak kecil
    yang bersarang di dalam kotak angka utama pada roda yang sama.
    """
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
    a2 = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))
    return inter / min(a1, a2) if min(a1, a2) > 0 else 0.0

def deduplicate_spatial_2d(detected_digits, iou_thresh=0.40):
    """
    Deduplikasi Spasial 2D Agnostik, Filter Ghost Sempit / Bercak Cat, & Pembatas Multi-Dot:
    1. Menggunakan 2D IoU & 2D IoA-Min sehingga angka miring (tilted) aman, namun kotak
       pecahan di dalam roda yang sama (seperti Kasus 325/331) tereliminasi.
    2. Menormalisasi seluruh token titik ('dots', 'dot', ',') menjadi '.' dan membatasi
       maksimal 1 titik desimal terbaik per layar.
    3. Membuang bercak cat sempit (seperti angka '4' semu pada Kasus 170) atau bayangan
       bingkai ber-confidence rendah ketika digit utama sudah lengkap.
    """
    if not detected_digits:
        return []

    dot_boxes = []
    number_boxes = []
    for d in detected_digits:
        d_copy = dict(d)
        if d_copy.get("digit") in ("dots", "dot", ".", ","):
            d_copy["digit"] = "."
            dot_boxes.append(d_copy)
        else:
            number_boxes.append(d_copy)

    # 1. Deduplikasi number boxes via 2D IoU & 2D IoA-Min + Rekam Kandidat Alternatif (Multi-Candidate)
    by_conf = sorted(number_boxes, key=lambda d: d["conf"], reverse=True)
    kept_numbers = []
    for cand in by_conf:
        cand_box = (cand["x1"], cand["y1"], cand["x2"], cand["y2"])
        overlap = False
        for k in kept_numbers:
            k_box = (k["x1"], k["y1"], k["x2"], k["y2"])
            if iou_2d(cand_box, k_box) > iou_thresh or ioa_min_2d(cand_box, k_box) > 0.65:
                overlap = True
                if "alt_candidates" not in k:
                    k["alt_candidates"] = []
                if cand["digit"] != k["digit"] and cand["conf"] >= 0.25:
                    k["alt_candidates"].append({"digit": cand["digit"], "conf": cand["conf"]})
                break
        if not overlap:
            cand_copy = dict(cand)
            cand_copy["alt_candidates"] = []
            kept_numbers.append(cand_copy)

    # 2. Filter Adaptive High-Contrast Ghost & Cramped Wheel Pitch (Kasus 32, 170, 195, 312, 325, 326)
    kept_numbers = sorted(kept_numbers, key=lambda d: (d["x1"] + d["x2"]) / 2.0)

    # 2A. Jika sudah ada >=4 digit kuat (conf >= 0.65) pada layar ber-titik desimal (LCD),
    # atau >=5 digit kuat pada meteran analog (>5 total), buang ghost tepi yang lemah (conf < 0.50)
    strong_count = sum(1 for d in kept_numbers if d["conf"] >= 0.65)
    if (dot_boxes and strong_count >= 4 and len(kept_numbers) >= 5) or (not dot_boxes and strong_count >= 5 and len(kept_numbers) > 5):
        kept_numbers = [d for d in kept_numbers if d["conf"] >= 0.50]

    # 2B. Filter Bercak Cat Sempit & Jarak Antar-Roda Terlalu Rapat (Kasus 170 '24720.5' -> '27205')
    if len(kept_numbers) > 5:
        widths = [d["x2"] - d["x1"] for d in kept_numbers]
        median_w = float(np.median(widths)) if widths else 20.0
        filtered_w = [
            d for d in kept_numbers
            if not (d["digit"] != "1" and (d["x2"] - d["x1"]) < 0.56 * median_w)
        ]
        if len(filtered_w) >= 5:
            kept_numbers = filtered_w

    # 2C. Jika masih > 5 digit, cek pasangan bersebelahan yang terlalu berhimpitan (< 0.65 * median_w)
    while len(kept_numbers) > 5:
        widths = [d["x2"] - d["x1"] for d in kept_numbers]
        median_w = float(np.median(widths)) if widths else 20.0
        cramped_idx = None
        for i in range(len(kept_numbers) - 1):
            d1, d2 = kept_numbers[i], kept_numbers[i + 1]
            xc1 = (d1["x1"] + d1["x2"]) / 2.0
            xc2 = (d2["x1"] + d2["x2"]) / 2.0
            if (xc2 - xc1) < 0.65 * median_w:
                w1, w2 = (d1["x2"] - d1["x1"]), (d2["x2"] - d2["x1"])
                if w1 < 0.62 * median_w and w2 >= 0.75 * median_w:
                    cramped_idx = i
                elif w2 < 0.62 * median_w and w1 >= 0.75 * median_w:
                    cramped_idx = i + 1
                else:
                    cramped_idx = i if d1["conf"] < d2["conf"] else (i + 1)
                break
        if cramped_idx is not None:
            kept_numbers.pop(cramped_idx)
        else:
            break

    # 3. Deduplikasi dots & Batasi Maksimal 1 Titik Desimal Terbaik (Kasus 312, 326, & 147)
    kept_dots = []
    if dot_boxes and kept_numbers:
        min_num_xc = min((d["x1"] + d["x2"]) / 2.0 for d in kept_numbers)
        max_num_xc = max((d["x1"] + d["x2"]) / 2.0 for d in kept_numbers)
        # Izinkan titik di antara angka, atau titik di depan angka jika hanya <= 2 digit tersisa akibat silau (seperti '.11' Kasus 147)
        internal_dots = [
            d for d in dot_boxes
            if (min_num_xc < ((d["x1"] + d["x2"]) / 2.0) < max_num_xc)
            or (len(kept_numbers) <= 2 and ((d["x1"] + d["x2"]) / 2.0) < max_num_xc and d["conf"] >= 0.35)
        ]
        is_analog_5d_leading_zero = (
            len(kept_numbers) == 5 and kept_numbers[0]["digit"] == "0"
        )
        if internal_dots and not is_analog_5d_leading_zero:
            best_dot = max(internal_dots, key=lambda d: d["conf"])
            kept_dots = [best_dot]

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
        best_dot = max(dot_boxes, key=lambda d: d.get("conf", 0.0))
        dot_idx = sorted_digits.index(best_dot)
        integer_tokens = [d["digit"] for d in sorted_digits[:dot_idx] if d.get("digit") not in ("dots", "dot", ".", ",")]
        decimal_tokens = [d["digit"] for d in sorted_digits[dot_idx+1:] if d.get("digit") not in ("dots", "dot", ".", ",")]
        raw_display = f"{''.join(integer_tokens)}.{''.join(decimal_tokens)}"

        # Jika bagian depan sebelum titik kosong (seperti '.11' pada Kasus 147 akibat silau menutupi sisi kiri),
        # jangan vonis stand 0 (SUKSES_DIGITAL), melainkan ANOMALI_GLARE_TERHALANG / OBSTRUKSI
        if not integer_tokens:
            return {
                "is_valid": False,
                "stand_baca": None,
                "raw_display": raw_display,
                "status": "ANOMALI_GLARE_TERHALANG",
                "tier_color": "RED",
                "meter_type": "digital_glare_parsial",
                "span_ratio": span_ratio,
                "reason": f"Angka utama sebelum titik desimal tidak terbaca ({raw_display}) akibat silau pada layar."
            }

        stand_baca = "".join(integer_tokens)
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

        # TAHAP 1: DETEKSI KOTAK COUNTER RODA ANGKA (Model 1 + Fallback Confidence)
        counter_results = self.counter_model.predict(img, conf=0.30, verbose=False)
        counter_boxes = counter_results[0].boxes
        is_fallback_counter = False

        # Fallback Confidence 0.06 dengan TTA jika deteksi awal nihil (Penyelamat Kasus 106 & 108)
        if len(counter_boxes) == 0:
            counter_results_fb = self.counter_model.predict(img, conf=0.06, augment=True, verbose=False)
            counter_boxes = counter_results_fb[0].boxes
            if len(counter_boxes) > 0:
                is_fallback_counter = True

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

        # Ekstraksi Kotak Counter
        boxes_list = []
        for i in range(len(counter_boxes)):
            b_coords = counter_boxes.xyxy[i].cpu().numpy()
            b_conf = float(counter_boxes.conf[i].cpu().numpy())
            boxes_list.append({
                "box": [float(b_coords[0]), float(b_coords[1]), float(b_coords[2]), float(b_coords[3])],
                "conf": b_conf
            })

        if not boxes_list:
            boxes_list = [{
                "box": [float(v) for v in counter_boxes.xyxy[0].cpu().numpy()],
                "conf": float(counter_boxes.conf[0].cpu().numpy())
            }]

        # HORIZONTAL COUNTER STITCHING / MERGING (Kasus 133 - Krop Terbelah Separuh oleh Ranting/Tali)
        merged_boxes = []
        used_idx = set()
        for i in range(len(boxes_list)):
            if i in used_idx:
                continue
            b1 = boxes_list[i]["box"]
            c1 = boxes_list[i]["conf"]
            w1, h1 = b1[2] - b1[0], b1[3] - b1[1]
            yc1 = (b1[1] + b1[3]) / 2.0
            m_box = list(b1)
            m_conf = c1
            for j in range(i + 1, len(boxes_list)):
                if j in used_idx:
                    continue
                b2 = boxes_list[j]["box"]
                c2 = boxes_list[j]["conf"]
                w2, h2 = b2[2] - b2[0], b2[3] - b2[1]
                yc2 = (b2[1] + b2[3]) / 2.0

                is_same_row = abs(yc1 - yc2) <= max(12.0, 0.40 * min(h1, h2))
                h_ratio = min(h1, h2) / max(h1, h2) if max(h1, h2) > 0 else 0
                left_box = b1 if b1[0] < b2[0] else b2
                right_box = b2 if b1[0] < b2[0] else b1
                h_gap = right_box[0] - left_box[2]

                if is_same_row and h_ratio > 0.55 and -15.0 <= h_gap <= max(35.0, 0.60 * max(w1, w2)):
                    comb_w = max(b1[2], b2[2]) - min(b1[0], b2[0])
                    comb_h = max(b1[3], b2[3]) - min(b1[1], b2[1])
                    comb_aspect = comb_w / comb_h if comb_h > 0 else 0
                    if comb_aspect <= 6.5:
                        m_box[0] = min(m_box[0], b2[0])
                        m_box[1] = min(m_box[1], b2[1])
                        m_box[2] = max(m_box[2], b2[2])
                        m_box[3] = max(m_box[3], b2[3])
                        m_conf = max(m_conf, c2)
                        used_idx.add(j)
            used_idx.add(i)
            merged_boxes.append({"box": m_box, "conf": m_conf})

        # Ambil kotak counter terbaik setelah penggabungan
        best_cand = max(merged_boxes, key=lambda b: b["conf"])
        x1, y1, x2, y2 = best_cand["box"]
        counter_conf = float(best_cand["conf"])
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

        # GUARD: RESOLUSI KROP EKSTREM RENDAH (< 12px) (Kasus 165, 195, 281 di 16-21px diselamatkan!)
        if crop_img.shape[0] < 12:
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

        # TAHAP 1B: BENTENG BLUR & SILAU (COUNTER ROI CHECK)
        dial_blur_score, dial_is_blurry = calculate_roi_blur(crop_img, roi_factor=1.0, blur_threshold=35.0)
        saved_paths = {}

        is_low_blur = dial_is_blurry or dial_blur_score < 35.0
        dehaze_rescued = False
        is_scaled = False

        # TAHAP 2: EVALUASI SILAU (Smart Glare Gatekeeper vs LCD Backlight - Kasus 310 & 147)
        # Batas glare dinaikkan dan diuji terhadap keterbacaan OCR terlebih dahulu agar cahaya
        # latar layar LCD digital (seperti Kasus 310) tidak salah divonis sebagai silau matahari.
        is_glare_severe, glare_ratio = detect_glare(crop_img, v_thresh=240, s_thresh=30, glare_limit=0.22)

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
                        digit_char = "."
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

        # TAHAP 3: STRATEGI MULTI-PASS (RAW -> DEHAZE CLAHE -> BICUBIC 2X SUPER-RESOLUTION)
        # Pass 3A: Coba citra krop asli (RAW) terlebih dahulu (Menyelamatkan Kasus 165, 281, 310, 312, 326)
        validation, detected_digits, avg_digit_conf = run_digit_pipeline(crop_img)
        active_crop = crop_img
        dehaze_rescued = False
        dehazed_blur_score = dial_blur_score

        def count_num_tokens(d_list):
            return sum(1 for d in d_list if str(d.get("digit", "")).isdigit())

        # Pass 3B: Jika RAW belum HIJAU dan krop buram/kabut, coba Dehaze CLAHE
        if not (validation.get("is_valid") and validation.get("tier_color") == "GREEN") and is_low_blur:
            c_dehaze = dehaze_crop_clahe(crop_img, clip_limit=3.0, tile_grid=(8, 8))
            val_dehaze, det_dehaze, conf_dehaze = run_digit_pipeline(c_dehaze)
            dehazed_blur_score, _ = calculate_roi_blur(c_dehaze, roi_factor=1.0, blur_threshold=35.0)

            if val_dehaze.get("is_valid") and val_dehaze.get("tier_color") == "GREEN" and conf_dehaze >= 0.62:
                validation = val_dehaze
                detected_digits = det_dehaze
                avg_digit_conf = conf_dehaze
                active_crop = c_dehaze
                dehaze_rescued = True
                validation["reason"] = (
                    f"Penyelamatan Kabut / Dehaze Sukses (Skor Blur Awal: {dial_blur_score:.1f} -> {dehazed_blur_score:.1f}, "
                    f"Conf: {avg_digit_conf:.2f}). Stand PLN: {validation['stand_baca']}."
                )

        # Pass 3C: Jika masih belum HIJAU dan tinggi krop < 50px, jalankan Bicubic 2x Upscaling (Kasus 195, 217, 245)
        # Hindari upscaling jika RAW sudah membaca >=3 digit tajam (seperti Smartmeter 3-digit '515' Kasus 186)
        raw_strong_3d = count_num_tokens(detected_digits) >= 3 and avg_digit_conf >= 0.80
        if not (validation.get("is_valid") and validation.get("tier_color") == "GREEN") and crop_img.shape[0] < 50 and not raw_strong_3d:
            c_up, scale_up, was_up = enhance_small_crop(crop_img, min_height=50)
            if was_up:
                val_up, det_up, conf_up = run_digit_pipeline(c_up)
                # Kembalikan skala koordinat bounding box ke dimensi crop_img asli
                for d in det_up:
                    d["x1"] /= scale_up
                    d["y1"] /= scale_up
                    d["x2"] /= scale_up
                    d["y2"] /= scale_up

                if val_up.get("is_valid") and val_up.get("tier_color") == "GREEN" and conf_up >= 0.58:
                    validation = val_up
                    detected_digits = det_up
                    avg_digit_conf = conf_up
                    is_scaled = True
                elif not validation.get("is_valid") and count_num_tokens(det_up) > count_num_tokens(detected_digits) and count_num_tokens(det_up) in (4, 5):
                    validation = val_up
                    detected_digits = det_up
                    avg_digit_conf = conf_up
                    is_scaled = True

                # Pass 3D: Jika Upscaling belum HIJAU, kombinasikan Upscaling + Dehaze CLAHE (Kasus 195 & 217)
                if not (validation.get("is_valid") and validation.get("tier_color") == "GREEN"):
                    c_up_dh = dehaze_crop_clahe(c_up, clip_limit=3.0, tile_grid=(8, 8))
                    val_up_dh, det_up_dh, conf_up_dh = run_digit_pipeline(c_up_dh)
                    for d in det_up_dh:
                        d["x1"] /= scale_up
                        d["y1"] /= scale_up
                        d["x2"] /= scale_up
                        d["y2"] /= scale_up
                    if val_up_dh.get("is_valid") and val_up_dh.get("tier_color") == "GREEN" and conf_up_dh >= 0.62:
                        validation = val_up_dh
                        detected_digits = det_up_dh
                        avg_digit_conf = conf_up_dh
                        is_scaled = True
                        dehaze_rescued = True

        # Pass 3E: SMARTMETER DESKEWING PASS (Kasus 397 - Meter Miring Tajam)
        if (validation.get("status") in ("STAND_KOSONG", "RESOLUSI_TERLALU_RENDAH") or count_num_tokens(detected_digits) == 0):
            for test_angle in (-38, 38):
                M_rot = cv2.getRotationMatrix2D((w_orig / 2.0, h_orig / 2.0), test_angle, 1.0)
                rot_img = cv2.warpAffine(img, M_rot, (w_orig, h_orig))
                c_rot_res = self.counter_model.predict(rot_img, conf=0.25, verbose=False)[0].boxes
                if len(c_rot_res) > 0:
                    rot_idx = int(c_rot_res.conf.argmax())
                    rx1, ry1, rx2, ry2 = [int(v) for v in c_rot_res.xyxy[rot_idx].cpu().numpy()]
                    r_crop = rot_img[ry1:ry2, rx1:rx2]
                    if r_crop.size > 0:
                        r_val, r_det, r_conf = run_digit_pipeline(r_crop)
                        if count_num_tokens(r_det) >= 3:
                            img = rot_img
                            crop_img = r_crop
                            crop_x1, crop_y1, crop_x2, crop_y2 = rx1, ry1, rx2, ry2
                            validation = r_val
                            detected_digits = r_det
                            avg_digit_conf = r_conf
                            counter_conf = float(c_rot_res.conf[rot_idx])
                            is_fallback_counter = False
                            validation["reason"] = f"Smartmeter miring berhasil diluruskan (Rotasi {test_angle}°). " + validation.get("reason", "")
                            break

        # Evaluasi Akhir Benteng Silau: Tolak sebagai silau HANYA jika silau tinggi (atau bagian depan hilang seperti '.11' Kasus 147)
        # DAN OCR tidak menghasilkan pembacaan valid (LCD seperti Kasus 310 tetap lolos!)
        if validation.get("status") == "ANOMALI_GLARE_TERHALANG" or (
            is_glare_severe
            and not (validation.get("is_valid") and validation.get("tier_color") == "GREEN")
            and count_num_tokens(detected_digits) < 4
        ):
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
                "raw_display": validation.get("raw_display", "-"),
                "blur_score": blur_score,
                "is_blurry": is_blurry,
                "dial_blur_score": dial_blur_score,
                "dehazed_blur_score": 0.0,
                "glare_percentage": round(glare_ratio * 100, 2),
                "counter_conf": counter_conf,
                "counter_box": [int(crop_x1), int(crop_y1), int(crop_x2), int(crop_y2)],
                "crop_shape": [int(crop_img.shape[0]), int(crop_img.shape[1])],
                "num_digits": len(detected_digits),
                "reason": f"Silau matahari ekstrem menutupi area counter ({glare_ratio*100:.1f}%). Tolak untuk billing.",
                "saved_paths": saved_paths
            }

        # Evaluasi Akhir Benteng Blur: Hanya vonis REJECTED_BLUR jika foto secara keseluruhan memang goyang/buram (blur_score < 48)
        # DAN digit yang terbaca < 3. Jika foto tajam tapi mika kusam (seperti Kasus 86 & 161), teruskan ke PERLU_TINJAU_ULANG!
        if (
            is_low_blur
            and not dehaze_rescued
            and not (validation.get("is_valid") and validation.get("tier_color") == "GREEN")
            and blur_score < 48.0
            and count_num_tokens(detected_digits) < 3
        ):
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

        # STRICT FALLBACK GATEKEEPER (Kasus 155, 191, 406):
        # Jika kotak counter berasal dari jalur fallback spekulatif (conf < 0.25),
        # kotak ini HANYA diselamatkan jika OCR membuktikan ini meteran nyata (valid GREEN dan digit >= 4).
        # Jika hanya berisi semen/genteng kosong atau <= 2 digit acak, batalkan kotak palsu ini
        # dan kembalikan status sejati: FAIL_COUNTER_NOT_FOUND (TIDAK_TERDETEKSI_KWH)!
        if is_fallback_counter and not (validation.get("is_valid") and validation.get("tier_color") == "GREEN" and count_num_tokens(detected_digits) >= 4):
            return {
                "status": "FAIL_COUNTER_NOT_FOUND",
                "tier_color": "RED",
                "message": "Kotak roda angka (stan_meter) tidak terdeteksi pada citra.",
                "image_name": image_name,
                "stand_baca": None,
                "blur_score": blur_score,
                "is_blurry": is_blurry
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