"""
=============================================================================
PROJECT ARGUS: DIGIT OCR DETECTOR (STAGE 2 YOLO & SPATIAL CONSENSUS)
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Deteksi karakter angka individual dan titik desimal:
1. Stage 2 YOLO Inference (TTA Multi-Scale, conf=0.08).
2. 2D IoU & 2D IoA-Min Deduplication + Multi-Candidate Recording.
3. Adaptive High-Contrast Ghost Filtering & Cramped Pitch Resolver.
4. Decimal Dot Normalizer & Internal Dot Bounding.
5. Collinear Adaptive Spatial Trendline (Datar maupun Miring Tilted).
=============================================================================
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from ultralytics import YOLO


def iou_2d(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> float:
    """Menghitung Intersection over Union (IoU) 2D antara dua bounding box (x1, y1, x2, y2)."""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
    a2 = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


def ioa_min_2d(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> float:
    """Menghitung Intersection over Minimum Area (IoA) 2D untuk mendeteksi kotak kecil yang bersarang."""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    a1 = max(1.0, (b1[2] - b1[0]) * (b1[3] - b1[1]))
    a2 = max(1.0, (b2[2] - b2[0]) * (b2[3] - b2[1]))
    return inter / min(a1, a2) if min(a1, a2) > 0 else 0.0


def deduplicate_spatial_2d(detected_digits: List[Dict[str, Any]], iou_thresh: float = 0.40) -> List[Dict[str, Any]]:
    """
    Deduplikasi Spasial 2D Agnostik, Filter Ghost Sempit / Bercak Cat, & Pembatas Multi-Dot:
    1. Menggunakan 2D IoU & 2D IoA-Min sehingga angka miring aman.
    2. Menormalisasi seluruh token titik ('dots', 'dot', ',') menjadi '.' dan membatasi
       maksimal 1 titik desimal terbaik per layar.
    3. Membuang bercak cat sempit atau bayangan bingkai ber-confidence rendah.
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

    # 1. Deduplikasi number boxes via 2D IoU & 2D IoA-Min + Multi-Candidate Recording
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

    # 2. Filter Adaptive High-Contrast Ghost & Cramped Wheel Pitch
    kept_numbers = sorted(kept_numbers, key=lambda d: (d["x1"] + d["x2"]) / 2.0)

    # 2A. Jika sudah ada >=4 digit kuat (conf >= 0.65) pada layar ber-titik desimal (LCD),
    # atau >=5 digit kuat pada meteran analog (>5 total), buang ghost tepi yang lemah (conf < 0.50)
    strong_count = sum(1 for d in kept_numbers if d["conf"] >= 0.65)
    if (dot_boxes and strong_count >= 4 and len(kept_numbers) >= 5) or (not dot_boxes and strong_count >= 5 and len(kept_numbers) > 5):
        kept_numbers = [d for d in kept_numbers if d["conf"] >= 0.50]

    # 2B. Filter Bercak Cat Sempit & Jarak Antar-Roda Terlalu Rapat
    if len(kept_numbers) > 5:
        widths = [d["x2"] - d["x1"] for d in kept_numbers]
        median_w = float(np.median(widths)) if widths else 20.0
        filtered_w = [
            d for d in kept_numbers
            if not (d["digit"] != "1" and (d["x2"] - d["x1"]) < 0.56 * median_w)
        ]
        if len(filtered_w) >= 5:
            kept_numbers = filtered_w

    # 2C. Cek pasangan bersebelahan yang terlalu berhimpitan (< 0.65 * median_w)
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

    # 3. Deduplikasi dots & Batasi Maksimal 1 Titik Desimal Terbaik
    kept_dots = []
    if dot_boxes and kept_numbers:
        min_num_xc = min((d["x1"] + d["x2"]) / 2.0 for d in kept_numbers)
        max_num_xc = max((d["x1"] + d["x2"]) / 2.0 for d in kept_numbers)
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


def filter_collinear_adaptive(detected_digits: List[Dict[str, Any]], crop_h: int, max_deviation_ratio: float = 0.70) -> List[Dict[str, Any]]:
    """
    Collinear Spatial Filter Adaptif (Mendukung Teks Datar maupun Miring / Tilted):
    Melakukan regresi linier tren slope pada titik tengah seluruh digit.
    Kotak noise / sekrup di luar jalur dibuang, sementara angka miring tetap utuh.
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


class DigitOCR:
    def __init__(self, model_path: Optional[Path] = None):
        if model_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            v5_path = base_dir / "models" / "digit_ocr_detector_v5.pt"
            v4_path = base_dir / "models" / "digit_ocr_detector_v4.pt"
            default_path = v5_path if v5_path.is_file() else (v4_path if v4_path.is_file() else (base_dir / "models" / "digit_ocr_detector.pt"))
            model_path = default_path

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model Digit tidak ditemukan di: {self.model_path}")

        self.model = YOLO(str(self.model_path))

    def detect_digits(self, crop_img: np.ndarray) -> Tuple[List[Dict[str, Any]], float]:
        """
        Menjalankan deteksi digit Stage 2 dengan TTA augmentasi,
        deduplikasi spasial, dan collinear filtering.
        Mengembalikan tuple: (clean_digits, avg_confidence)
        """
        d_res = self.model.predict(
            crop_img, conf=0.08, augment=True, verbose=False
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
                digit_char = self.model.names.get(d_cls, str(d_cls))

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
        collinear = filter_collinear_adaptive(dedup, crop_h=crop_img.shape[0], max_deviation_ratio=0.70)
        avg_conf = float(np.mean([d["conf"] for d in collinear])) if collinear else 0.0
        return collinear, avg_conf
