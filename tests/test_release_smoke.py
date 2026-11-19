#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
PROJECT ARGUS v1.0.0: AUTOMATED RELEASE SMOKE TEST SUITE
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Menguji keutuhan seluruh komponen inti ARGUS v1.0.0 secara terisolasi tanpa
mengubah folder %LOCALAPPDATA% pengguna ataupun memanggil API cloud eksternal:
1. Quality Filter (Laplacian blur ROI, HSV glare masking, CLAHE)
2. Sequence Arbiter (Analog 5/6 digit, Digital decimal dot split, anti-partial)
3. Feedback Vault (%LOCALAPPDATA% isolation, YOLO pre-label export, force ZIP)
4. Ground Truth Evaluator (prepare 100-sample form & Precision/Recall/F1 score)
5. FastAPI Endpoints (/, /dashboard, /tutorial, /api/feedback/status, ACMT CSV,
   dan Excel Export resmi UP3 Mojokerto dalam direktori temp)
=============================================================================
"""

import base64
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import openpyxl
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src import evaluate_ground_truth as gt_eval
from src import feedback_vault
from src.api.routes import excel as excel_route
from src.api.server import app
from src.vision_ai.quality_filter import calculate_roi_blur, dehaze_crop_clahe, detect_glare
from src.vision_ai.sequence_arbiter import validate_reading_sequence


class QualityFilterTests(unittest.TestCase):
    def test_blur_detection_distinguishes_flat_vs_sharp_image(self):
        flat_img = np.full((240, 240, 3), 120, dtype=np.uint8)
        sharp_img = np.zeros((240, 240, 3), dtype=np.uint8)
        for y in range(0, 240, 12):
            for x in range(0, 240, 12):
                if ((x // 12) + (y // 12)) % 2 == 0:
                    sharp_img[y : y + 12, x : x + 12] = 255

        flat_score, flat_blurry = calculate_roi_blur(flat_img, blur_threshold=60.0)
        sharp_score, sharp_blurry = calculate_roi_blur(sharp_img, blur_threshold=60.0)

        self.assertTrue(flat_blurry)
        self.assertFalse(sharp_blurry)
        self.assertGreater(sharp_score, flat_score)

    def test_glare_detection_and_clahe_output_shape(self):
        bright_img = np.full((80, 200, 3), 255, dtype=np.uint8)
        severe, ratio = detect_glare(bright_img)
        self.assertTrue(severe)
        self.assertGreater(ratio, 0.9)

        dehazed = dehaze_crop_clahe(bright_img)
        self.assertEqual(dehazed.shape, bright_img.shape)


class SequenceArbiterTests(unittest.TestCase):
    @staticmethod
    def _box(digit: str, x1: int, x2: int, conf: float = 0.92):
        return {"digit": digit, "x1": x1, "y1": 10, "x2": x2, "y2": 50, "conf": conf}

    def test_analog_5_digit_valid_green(self):
        boxes = [
            self._box("0", 10, 42),
            self._box("7", 48, 80),
            self._box("5", 86, 118),
            self._box("0", 124, 156),
            self._box("1", 162, 194),
        ]
        res = validate_reading_sequence(boxes, crop_w=210, crop_h=60)
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["tier_color"], "GREEN")
        self.assertEqual(res["status"], "SUKSES_ANALOG")
        self.assertEqual(res["stand_baca"], "07501")

    def test_digital_dot_splits_integer_stand_only(self):
        boxes = [
            self._box("1", 10, 34),
            self._box("2", 38, 62),
            self._box("3", 66, 90),
            self._box("dot", 94, 102),
            self._box("4", 106, 130),
            self._box("5", 134, 158),
        ]
        res = validate_reading_sequence(boxes, crop_w=170, crop_h=60)
        self.assertTrue(res["is_valid"])
        self.assertEqual(res["tier_color"], "GREEN")
        self.assertEqual(res["status"], "SUKSES_DIGITAL")
        self.assertEqual(res["stand_baca"], "123")
        self.assertEqual(res["raw_display"], "123.45")

    def test_low_confidence_routes_to_yellow_triage(self):
        boxes = [self._box("6", 10, 40, conf=0.35), self._box("8", 45, 75, conf=0.90)]
        res = validate_reading_sequence(boxes, crop_w=150, crop_h=60)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["tier_color"], "YELLOW")
        self.assertEqual(res["status"], "DIGIT_AMBIGU")

    def test_partial_single_digit_rejected_red(self):
        boxes = [self._box("6", 80, 105, conf=0.90)]
        res = validate_reading_sequence(boxes, crop_w=200, crop_h=60)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["tier_color"], "RED")
        self.assertEqual(res["status"], "STAND_TIDAK_LENGKAP")


class FeedbackVaultIsolationTests(unittest.TestCase):
    def test_sync_and_force_package_in_isolated_temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault_base = Path(tmp) / "feedback_vault"
            staging = vault_base / "staging"
            staging_imgs = staging / "images"
            staging_lbls = staging / "labels"
            manifest = staging / "manifest.json"
            releases = vault_base / "releases"

            sample_img = np.full((120, 200, 3), 180, dtype=np.uint8)
            ok, encoded = cv2.imencode(".jpg", sample_img)
            self.assertTrue(ok)
            img_b64 = "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")

            with (
                patch.object(feedback_vault, "VAULT_BASE_DIR", vault_base),
                patch.object(feedback_vault, "STAGING_DIR", staging),
                patch.object(feedback_vault, "STAGING_IMAGES_DIR", staging_imgs),
                patch.object(feedback_vault, "STAGING_LABELS_DIR", staging_lbls),
                patch.object(feedback_vault, "MANIFEST_FILE", manifest),
                patch.object(feedback_vault, "RELEASES_DIR", releases),
            ):
                status_init = feedback_vault.get_vault_status()
                self.assertEqual(status_init["staging_count"], 0)
                self.assertEqual(status_init["vault_dir"], str(vault_base))

                sync_res = feedback_vault.sync_feedback_items(
                    upsert_items=[
                        {
                            "idpel": "514500001376",
                            "nama": "PELANGGAN UJI",
                            "tarif_daya": "R1 / 900 VA",
                            "filename": "202601-514500001376-L.jpg",
                            "stan_lapangan": "123",
                            "orig_argus": "128",
                            "corrected_argus": "123",
                            "orig_status": "DIFF",
                            "corrected_status": "MATCH",
                            "ai_notes": "Salah Baca Angka",
                            "blur_score": 150.5,
                            "glare_ratio": 0.0,
                            "counter_box": [10, 20, 180, 90],
                            "crop_shape": [70, 170],
                            "digits_detail": [{"digit": "1", "x1": 10, "y1": 10, "x2": 30, "y2": 50}],
                            "image_base64": img_b64,
                        }
                    ]
                )
                self.assertEqual(sync_res["staging_count"], 1)

                pkg = feedback_vault.force_package_release()
                self.assertTrue(pkg["packaged"])
                self.assertEqual(pkg["packaged_count"], 1)
                self.assertEqual(pkg["staging_count"], 0)

                zip_path = releases / pkg["release_zip_name"]
                self.assertTrue(zip_path.is_file())
                with zipfile.ZipFile(zip_path, "r") as zf:
                    names = zf.namelist()
                    self.assertIn("feedback_manifest.csv", names)
                    self.assertIn("classes.txt", names)
                    self.assertTrue(any(n.endswith(".xlsx") for n in names))
                    self.assertTrue(any(n.startswith("images/") for n in names))
                    self.assertTrue(any(n.startswith("labels/") and n.endswith(".txt") for n in names))


class GroundTruthEvaluatorTests(unittest.TestCase):
    def test_prepare_and_score_ground_truth_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            src_xlsx = tmp_dir / "source_audit.xlsx"
            gt_xlsx = tmp_dir / "gt_10_samples.xlsx"
            json_out = tmp_dir / "gt_summary.json"

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["NO", "IDPEL", "NAMA PELANGGAN", "TARIF / DAYA", "STAN LAPANGAN", "HASIL ANALISA ARGUS", "HASIL STAN BACA", "VONIS AUDIT", "LINK FOTO ASLI", "NAMA FILE FOTO"])
            for i in range(1, 11):
                verdict = "SESUAI_MATCH" if i <= 7 else "BEDA_STAND"
                ws.append([i, f"5145000000{i:02d}", f"PELANGGAN {i}", "R1/900", str(100 + i), str(100 + i), str(100 + i), verdict, "-", f"f{i}.jpg"])
            wb.save(str(src_xlsx))

            prep_info = gt_eval.prepare_ground_truth_sheet(src_xlsx, gt_xlsx, sample_size=6, seed=7)
            self.assertEqual(prep_info["sampled_count"], 6)
            self.assertTrue(gt_xlsx.is_file())

            # Isi ground truth di 6 baris sampel: 5 tepat cocok, 1 salah stand & false billing escape
            wb_gt = openpyxl.load_workbook(str(gt_xlsx))
            ws_gt = wb_gt.active
            for r_idx in range(4, 10):
                pred_stand = ws_gt.cell(row=r_idx, column=7).value
                pred_v = str(ws_gt.cell(row=r_idx, column=8).value)
                ws_gt.cell(row=r_idx, column=11, value=pred_stand)
                ws_gt.cell(row=r_idx, column=12, value="SESUAI" if "SESUAI" in pred_v else "KELAINAN")
            # Paksakan baris sampel terakhir beda stand & ternyata kelainan (uji False Negative / FN)
            ws_gt.cell(row=9, column=11, value="999")
            ws_gt.cell(row=9, column=12, value="KELAINAN")
            wb_gt.save(str(gt_xlsx))

            summary = gt_eval.score_ground_truth_sheet(gt_xlsx, json_out=json_out)
            self.assertTrue(json_out.is_file())
            self.assertEqual(summary["stand_evaluation"]["evaluated_count"], 6)
            self.assertEqual(summary["stand_evaluation"]["exact_match_count"], 5)
            self.assertEqual(summary["classification_evaluation"]["evaluated_count"], 6)
            self.assertTrue(gt_eval.stands_match("17", "17.84"))
            self.assertTrue(gt_eval.stands_match("00000", "00000.4"))


class FastAPIRoutesTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_web_views_and_health_routes(self):
        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertEqual(r_root.json()["version"], "1.0.0")

        r_dash = self.client.get("/dashboard")
        self.assertEqual(r_dash.status_code, 200)
        self.assertIn("SISTEM AUDIT STAND KWH METER", r_dash.text.upper())
        self.assertIn("/static/js/feedback_vault.js", r_dash.text)

        r_tut = self.client.get("/tutorial")
        self.assertEqual(r_tut.status_code, 200)
        self.assertIn("PANDUAN OPERASIONAL", r_tut.text.upper())

        r_sim = self.client.get("/simulator")
        self.assertEqual(r_sim.status_code, 404)

    def test_acmt_csv_parser_and_excel_export_isolated(self):
        csv_payload = "IDPEL;NAMA;TARIF;DAYA;STAN BACA;NAMA FILE\n514500001376;BUDI;R1;900;00451;meter1.jpg\n".encode("utf-8")
        r_parse = self.client.post(
            "/api/parse-acmt-excel",
            files={"file": ("rekap_acmt.csv", csv_payload, "text/csv")},
        )
        self.assertEqual(r_parse.status_code, 200)
        body = r_parse.json()
        self.assertEqual(body["total_records"], 1)
        self.assertEqual(body["records"][0]["idpel"], "514500001376")
        self.assertEqual(body["records"][0]["stan_lapangan"], "00451")

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(excel_route, "BASE_DIR", Path(tmp)):
                r_exp = self.client.post(
                    "/api/export-audit-excel",
                    json={
                        "rows": [
                            {
                                "no": 1,
                                "idpel": "514500001376",
                                "nama": "BUDI",
                                "tarif_daya": "R1 / 900 VA",
                                "kdbaca": "F",
                                "stan_lapangan": "451",
                                "raw_display": "00451",
                                "stan_argus": "00451",
                                "selisih": "0",
                                "verdict": "SESUAI_MATCH",
                                "diagnosa_detail": "Cocok 100%",
                                "tier_color": "GREEN",
                                "latency_ms": 42.5,
                                "blur_score": 120.0,
                                "glare_ratio": 0.0,
                                "filename": "202601-514500001376-L.jpg",
                                "is_edited": False,
                                "notes": "",
                            }
                        ]
                    },
                )
                self.assertEqual(r_exp.status_code, 200)
                self.assertIn("spreadsheetml", r_exp.headers.get("content-type", ""))
                self.assertGreater(len(r_exp.content), 2000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
