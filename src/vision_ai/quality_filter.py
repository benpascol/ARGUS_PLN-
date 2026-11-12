"""
=============================================================================
PROJECT ARGUS: QUALITY FILTER & PRE-PROCESSING MODULE
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Menangani evaluasi kualitas citra meteran pra-inferensi:
1. Laplacian Blur Pre-Check pada ROI tengah (Area Meteran).
2. HSV Value/Saturation Overexposure Glare Detection (Silau Matahari).
3. LAB-CLAHE Luminance Dehazing (Penyelamat Kabut / Lensa Berminyak).
4. Bicubic 2x Super-Resolution & Unsharp Contrast untuk Krop Sempit (<55px).
=============================================================================
"""

import cv2
import numpy as np


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
    _, s, v = cv2.split(hsv)

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

    h, _ = crop_img.shape[:2]
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
