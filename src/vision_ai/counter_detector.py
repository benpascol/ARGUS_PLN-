"""
=============================================================================
PROJECT ARGUS: COUNTER DIAL DETECTOR (STAGE 1 YOLO)
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Lokalisasi kotak roda angka (counter dial) meteran listrik:
1. Stage 1 YOLO Inference dengan Fallback TTA Ambang Rendah (0.06).
2. Sub-Box Suppression / Container Preference (Anti-serpihan mika).
3. Horizontal Counter Stitching (Penyambung krop terpotong ranting/kabel).
4. Aspect-Ratio Scoring & Padded Bounding Box Extraction.
5. Smartmeter Perspective Rotation Deskewing (+/- 38°).
=============================================================================
"""

import cv2
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from ultralytics import YOLO


class CounterDetector:
    def __init__(self, model_path: Optional[Path] = None):
        if model_path is None:
            base_dir = Path(__file__).resolve().parent.parent.parent
            model_path = base_dir / "models" / "meter_counter_detector.pt"

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model Counter tidak ditemukan di: {self.model_path}")

        self.model = YOLO(str(self.model_path))

    def detect_counter(
        self,
        img: Any,
        padding_ratio: float = 0.03
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Mendeteksi area counter dial pada citra input.
        Mengembalikan tuple: (is_fallback, best_box_data)
        """
        h_orig, w_orig = img.shape[:2]

        # 1. Inferensi Standar (Conf 0.30)
        counter_results = self.model.predict(img, conf=0.30, verbose=False)
        counter_boxes = counter_results[0].boxes
        is_fallback = False

        # 2. Fallback Confidence 0.06 dengan TTA jika hasil awal nihil
        if len(counter_boxes) == 0:
            counter_results_fb = self.model.predict(img, conf=0.06, augment=True, verbose=False)
            counter_boxes = counter_results_fb[0].boxes
            if len(counter_boxes) > 0:
                is_fallback = True

        if len(counter_boxes) == 0:
            return False, None

        # 3. Ekstraksi koordinat kotak
        boxes_list = []
        for i in range(len(counter_boxes)):
            b_coords = counter_boxes.xyxy[i].cpu().numpy()
            b_conf = float(counter_boxes.conf[i].cpu().numpy())
            boxes_list.append({
                "box": [float(b_coords[0]), float(b_coords[1]), float(b_coords[2]), float(b_coords[3])],
                "conf": b_conf
            })

        # 4. Container Preference / Sub-Box Suppression
        suppressed_sub_idx = set()
        for i, b_sub in enumerate(boxes_list):
            box_a = b_sub["box"]
            w_a = box_a[2] - box_a[0]
            h_a = box_a[3] - box_a[1]
            aspect_a = w_a / h_a if h_a > 0 else 0
            for j, b_parent in enumerate(boxes_list):
                if i == j:
                    continue
                box_b = b_parent["box"]
                w_b = box_b[2] - box_b[0]
                h_b = box_b[3] - box_b[1]
                aspect_b = w_b / h_b if h_b > 0 else 0

                if aspect_b >= 3.0 and aspect_a < 3.2:
                    inter_x1 = max(box_a[0], box_b[0])
                    inter_x2 = min(box_a[2], box_b[2])
                    overlap_w = max(0.0, inter_x2 - inter_x1)
                    if (overlap_w / max(1.0, w_a) >= 0.75) and (b_parent["conf"] >= b_sub["conf"] - 0.15):
                        suppressed_sub_idx.add(i)
                        break

        clean_boxes = [b for idx, b in enumerate(boxes_list) if idx not in suppressed_sub_idx]
        if not clean_boxes:
            clean_boxes = boxes_list

        # 5. Horizontal Counter Stitching / Merging
        merged_boxes = []
        used_idx = set()
        for i in range(len(clean_boxes)):
            if i in used_idx:
                continue
            b1 = clean_boxes[i]["box"]
            c1 = clean_boxes[i]["conf"]
            w1, h1 = b1[2] - b1[0], b1[3] - b1[1]
            yc1 = (b1[1] + b1[3]) / 2.0
            m_box = list(b1)
            m_conf = c1
            for j in range(i + 1, len(clean_boxes)):
                if j in used_idx:
                    continue
                b2 = clean_boxes[j]["box"]
                c2 = clean_boxes[j]["conf"]
                w2, h2 = b2[2] - b2[0], b2[3] - b2[1]
                yc2 = (b2[1] + b2[3]) / 2.0

                is_same_row = abs(yc1 - yc2) <= max(12.0, 0.40 * min(h1, h2))
                h_ratio = min(h1, h2) / max(h1, h2) if max(h1, h2) > 0 else 0
                left_box = b1 if b1[0] < b2[0] else b2
                right_box = b2 if b1[0] < b2[0] else b1
                h_gap = right_box[0] - left_box[2]

                if is_same_row and h_ratio > 0.55 and -25.0 <= h_gap <= max(35.0, 0.60 * max(w1, w2)):
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

        # 6. Scoring Kandidat Terbaik
        def score_cand(cand):
            cw = cand["box"][2] - cand["box"][0]
            ch = cand["box"][3] - cand["box"][1]
            caspect = cw / ch if ch > 0 else 0
            bonus = 0.08 if (3.0 <= caspect <= 6.5) else 0.0
            return cand["conf"] + bonus

        best_cand = max(merged_boxes, key=score_cand)
        x1, y1, x2, y2 = best_cand["box"]
        counter_conf = float(best_cand["conf"])
        box_w = x2 - x1
        box_h = y2 - y1

        # 7. Penambahan Padding Presisi
        pad_x = int(box_w * padding_ratio)
        pad_y = int(box_h * padding_ratio)
        crop_x1 = max(0, int(x1 - pad_x))
        crop_y1 = max(0, int(y1 - pad_y))
        crop_x2 = min(w_orig, int(x2 + pad_x))
        crop_y2 = min(h_orig, int(y2 + pad_y))

        crop_img = img[crop_y1:crop_y2, crop_x1:crop_x2].copy()

        return is_fallback, {
            "crop_img": crop_img,
            "crop_box": [crop_x1, crop_y1, crop_x2, crop_y2],
            "counter_conf": counter_conf,
            "is_fallback": is_fallback
        }
