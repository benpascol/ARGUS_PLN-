"""
=============================================================================
PROJECT ARGUS: VISION AI ORCHESTRATOR PIPELINE (V5 ENTERPRISE EDITION)
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Orkestrator utama inferensi Two-Stage YOLO Vision AI:
1. Quality Filter (Laplacian Blur & HSV Glare Guard)
2. Barcode & QR IDPEL Engine
3. Stage 1 YOLO Counter Dial Detector (Adaptive Fallback & Stitching)
4. Multi-Pass Enhancement (RAW -> Dehaze CLAHE -> Bicubic Super-Res -> Deskew)
5. Stage 2 YOLO Digit Detector & Spatial Consensus
6. Sequence & Reading Arbiter (Sistem Triage 3 Warna: Hijau / Kuning / Merah)
=============================================================================
"""

import io
import sys
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Fix Windows console UTF-8 encoding tanpa menutup stream
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Import Modul Terkapsulasi
from src.vision_ai.quality_filter import (
    calculate_roi_blur,
    detect_glare,
    dehaze_crop_clahe,
    enhance_small_crop
)
from src.vision_ai.barcode_engine import BarcodeEngine
from src.vision_ai.counter_detector import CounterDetector
from src.vision_ai.digit_ocr import (
    DigitOCR,
    iou_2d,
    ioa_min_2d,
    deduplicate_spatial_2d,
    filter_collinear_adaptive
)
from src.vision_ai.sequence_arbiter import validate_reading_sequence


class ArgusVisionPipeline:
    """
    Enterprise Two-Stage Vision Pipeline untuk Pengawasan Stand KWH Meter PLN.
    """
    def __init__(
        self,
        counter_model_path: Optional[Union[str, Path]] = None,
        digit_model_path: Optional[Union[str, Path]] = None
    ):
        base_dir = Path(__file__).resolve().parent.parent.parent
        v5_path = base_dir / "models" / "digit_ocr_detector_v5.pt"
        v4_path = base_dir / "models" / "digit_ocr_detector_v4.pt"
        default_digit = v5_path if v5_path.is_file() else (v4_path if v4_path.is_file() else (base_dir / "models" / "digit_ocr_detector.pt"))

        self.counter_model_path = Path(counter_model_path or (base_dir / "models" / "meter_counter_detector.pt"))
        self.digit_model_path = Path(digit_model_path or default_digit)

        print("🔄 Memuat Model AI ARGUS (Clean Modular Architecture)...")
        print(f"   - Model 1 (Counter) : {self.counter_model_path.name}")
        print(f"   - Model 2 (Digit)   : {self.digit_model_path.name}")

        self.counter_detector = CounterDetector(self.counter_model_path)
        self.digit_ocr = DigitOCR(self.digit_model_path)
        self.barcode_engine = BarcodeEngine()

        # Backward compatibility reference
        self.counter_model = self.counter_detector.model
        self.digit_model = self.digit_ocr.model

        print("✅ Pipeline AI ARGUS Siap Digunakan!\n")

    def predict_image(
        self,
        image_input: Union[str, Path, np.ndarray],
        output_dir: Optional[Union[str, Path]] = None,
        padding_ratio: float = 0.03,
        save_mode: str = "all"
    ) -> Dict[str, Any]:
        """
        Alur Utama Prediksi Citra Meteran:
        Mengembalikan kamus hasil evaluasi audit lengkap, nilai stan baca, selisih,
        status triage (Hijau/Kuning/Merah), metrik kualitas citra, dan koordinat deteksi.
        """
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

        # 1. TIER 1: LAPLACIAN BLUR PRE-CHECK PADA AREA TENGAH
        blur_score, is_blurry = calculate_roi_blur(img, roi_factor=0.6, blur_threshold=60.0)

        # 2. TAHAP 1: DETEKSI KOTAK COUNTER DIAL (Model 1)
        is_fallback_counter, counter_data = self.counter_detector.detect_counter(img, padding_ratio=padding_ratio)

        if not counter_data:
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

        crop_img = counter_data["crop_img"]
        crop_x1, crop_y1, crop_x2, crop_y2 = counter_data["crop_box"]
        counter_conf = counter_data["counter_conf"]

        if crop_img.size == 0:
            return {"status": "ERROR", "tier_color": "RED", "message": "Crop area berukuran 0 piksel."}

        # Guard: Resolusi Krop Ekstrem Rendah (< 12px)
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

        # 3. TAHAP 1B & 2: BENTENG BLUR & SILAU PADA ROI COUNTER
        dial_blur_score, dial_is_blurry = calculate_roi_blur(crop_img, roi_factor=1.0, blur_threshold=35.0)
        is_low_blur = dial_is_blurry or dial_blur_score < 35.0
        is_glare_severe, glare_ratio = detect_glare(crop_img, v_thresh=240, s_thresh=30, glare_limit=0.22)

        # Helper internal OCR + Validator
        def run_digit_pipeline(target_crop):
            collinear, avg_conf = self.digit_ocr.detect_digits(target_crop)
            val = validate_reading_sequence(
                collinear,
                crop_w=target_crop.shape[1],
                crop_h=target_crop.shape[0]
            )
            return val, collinear, avg_conf

        def count_num_tokens(d_list):
            return sum(1 for d in d_list if str(d.get("digit", "")).isdigit())

        # 4. TAHAP 3: STRATEGI MULTI-PASS
        # Pass 3A: RAW Asli
        validation, detected_digits, avg_digit_conf = run_digit_pipeline(crop_img)
        dehaze_rescued = False
        is_scaled = False
        dehazed_blur_score = dial_blur_score

        # Pass 3B: Dehaze CLAHE jika RAW belum HIJAU dan krop buram
        if not (validation.get("is_valid") and validation.get("tier_color") == "GREEN") and is_low_blur:
            c_dehaze = dehaze_crop_clahe(crop_img, clip_limit=3.0, tile_grid=(8, 8))
            val_dehaze, det_dehaze, conf_dehaze = run_digit_pipeline(c_dehaze)
            dehazed_blur_score, _ = calculate_roi_blur(c_dehaze, roi_factor=1.0, blur_threshold=35.0)

            if val_dehaze.get("is_valid") and val_dehaze.get("tier_color") == "GREEN" and conf_dehaze >= 0.62:
                validation = val_dehaze
                detected_digits = det_dehaze
                avg_digit_conf = conf_dehaze
                dehaze_rescued = True
                validation["reason"] = (
                    f"Penyelamatan Kabut / Dehaze Sukses (Skor Blur Awal: {dial_blur_score:.1f} -> {dehazed_blur_score:.1f}, "
                    f"Conf: {avg_digit_conf:.2f}). Stand PLN: {validation['stand_baca']}."
                )

        # Pass 3C: Super-Resolution 2x jika krop kecil (<50px)
        raw_strong_3d = count_num_tokens(detected_digits) >= 3 and avg_digit_conf >= 0.80
        if not (validation.get("is_valid") and validation.get("tier_color") == "GREEN") and crop_img.shape[0] < 50 and not raw_strong_3d:
            c_up, scale_up, was_up = enhance_small_crop(crop_img, min_height=50)
            if was_up:
                val_up, det_up, conf_up = run_digit_pipeline(c_up)
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

                # Pass 3D: Kombinasi Super-Resolution + Dehaze
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

        # Pass 3E: Rotasi Deskewing untuk Smartmeter miring
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

        saved_paths = {}

        # 5. EVALUASI AKHIR SILAU
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

        # 6. EVALUASI AKHIR BLUR
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

        # 7. STRICT FALLBACK GATEKEEPER
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

        # 8. VISUALISASI ANOTASI
        annotated_crop = crop_img.copy()
        colors = [
            (255, 100, 0), (0, 200, 255), (0, 255, 100), (255, 0, 150),
            (200, 0, 255), (0, 150, 255), (255, 255, 0), (0, 255, 255),
            (255, 150, 150), (150, 255, 150)
        ]

        for _, d in enumerate(detected_digits):
            color = colors[int(d["digit"]) % len(colors)] if d["digit"].isdigit() else (0, 255, 255)
            bx1, by1, bx2, by2 = int(d["x1"]), int(d["y1"]), int(d["x2"]), int(d["y2"])
            cv2.rectangle(annotated_crop, (bx1, by1), (bx2, by2), color, 2)
            label_text = f"{d['digit']} ({d['conf']:.2f})"
            cv2.putText(annotated_crop, label_text, (bx1, max(12, by1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

        annotated_full = img.copy()
        tier = validation.get("tier_color", "RED")
        if tier == "GREEN":
            status_color = (0, 255, 0)
            if dehaze_rescued:
                header_text = f"STAND: {validation['stand_baca']} [DEHAZE RESCUED]"
            else:
                header_text = f"STAND: {validation['stand_baca']} (Conf: {avg_digit_conf:.2f})"
        elif tier == "YELLOW":
            status_color = (0, 215, 255)
            header_text = f"[AMBIGU] {validation['status']}"
        else:
            status_color = (0, 0, 255)
            header_text = f"[REJECTED] {validation['status']}"

        cv2.rectangle(annotated_full, (crop_x1, crop_y1), (crop_x2, crop_y2), status_color, 3)
        cv2.putText(annotated_full, header_text, (crop_x1, max(30, crop_y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, status_color, 2, cv2.LINE_AA)

        should_save = bool(output_dir)
        if should_save and save_mode == "focused":
            tier = validation.get("tier_color", "RED")
            if tier == "GREEN":
                should_save = False

        if should_save:
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
    print(f"🎉 Selesai! Seluruh visualisasi kotak warna tersimpan di:")
    print(f"📁 {output_dir}")
    print("=" * 105)


if __name__ == "__main__":
    run_benchmark_on_samples()
