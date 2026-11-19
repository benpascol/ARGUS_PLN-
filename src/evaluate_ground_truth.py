#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
PROJECT ARGUS: EVALUASI GROUND TRUTH 100 SAMPEL (FASE 4 PILOT VALIDATION)
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Alat bantu ilmiah untuk Langkah 4.2 Roadmap (Uji Sampling Ground Truth):
1. Mode --prepare : Mengambil sampel acak terukur (default N=100) dari berkas
   ekspor Excel resmi ARGUS dan menyusun Formulir Verifikasi Manual PLN.
2. Mode --score   : Membaca formulir yang telah diisi pengawas PLN lalu
   menghitung Exact Stand Accuracy, MAE (kWh), Precision, Recall, F1-Score,
   Confusion Matrix, dan False Billing Escape Rate sesuai RULEBOOK Pilar 6.
=============================================================================
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


ANOMALY_KEYWORDS = (
    "BEDA",
    "DIFF",
    "KELAINAN",
    "TIDAK SESUAI",
    "TIDAK_SESUAI",
    "TIDAK_TERDETEKSI",
    "TIDAK TERDETEKSI",
    "BUKAN",
    "NIHIL",
    "FRAUD",
    "BURAM",
    "BLUR",
    "SILAU",
    "GLARE",
    "TRIAGE",
    "TINJAU",
    "ANOMALI",
    "RUSAK",
    "SALAH",
)

NORMAL_KEYWORDS = (
    "SESUAI",
    "MATCH",
    "ROLLING",
    "VALID",
    "COCOK",
    "AMAN",
    "NORMAL",
    "OK",
)


def normalize_stand_text(value: Any) -> str:
    """Menormalisasi nilai stand kWh dari sel Excel menjadi string bersih."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"
    text = str(value).strip()
    if text in ("", "-", "None", "NONE", "N/A"):
        return ""
    if re.fullmatch(r"\d+\.0+", text):
        return text.split(".")[0]
    return text


def parse_numeric_stand(text: str) -> Optional[float]:
    """Mengonversi teks stand kWh menjadi angka float bila valid."""
    clean = normalize_stand_text(text).replace(",", ".")
    if not clean:
        return None
    try:
        return float(clean)
    except ValueError:
        return None


def stands_match(pred_val: Any, gt_val: Any) -> Optional[bool]:
    """Membandingkan stand AI vs ground truth secara numerik/zero-padded.

    Mengembalikan None apabila ground truth kosong atau tidak diisi angka.
    """
    gt_text = normalize_stand_text(gt_val)
    if not gt_text:
        return None

    pred_text = normalize_stand_text(pred_val)
    if not pred_text:
        return False

    gt_num = parse_numeric_stand(gt_text)
    pred_num = parse_numeric_stand(pred_text)
    if gt_num is not None and pred_num is not None:
        return abs(gt_num - pred_num) < 1e-6

    return pred_text.upper() == gt_text.upper()


def is_anomaly_verdict(verdict: Any) -> Optional[bool]:
    """Memetakan label vonis menjadi kelas biner (True=Kelainan/Anomali, False=Sesuai/Normal)."""
    if verdict is None:
        return None
    text = str(verdict).strip().upper()
    if not text or text in ("-", "NONE", "PENDING", "BELUM DIAUDIT"):
        return None
    if text in ("1", "YA", "TRUE", "POSITIF"):
        return True
    if text in ("0", "TIDAK", "FALSE", "NEGATIF"):
        return False
    if any(k in text for k in ANOMALY_KEYWORDS):
        return True
    if any(k in text for k in NORMAL_KEYWORDS):
        return False
    return None


def _find_header_and_rows(excel_path: Path) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    """Mencari baris header yang memuat IDPEL beserta seluruh baris datanya."""
    wb = openpyxl.load_workbook(str(excel_path), data_only=False)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    for idx, row in enumerate(rows[:15]):
        if not row:
            continue
        cells = [str(c).strip().upper() if c is not None else "" for c in row]
        if any("IDPEL" in c for c in cells):
            headers = [str(c).strip() if c is not None else f"COL_{i+1}" for i, c in enumerate(row)]
            data_rows = [
                r for r in rows[idx + 1 :]
                if r and any(v is not None and str(v).strip() != "" for v in r)
            ]
            return headers, data_rows

    raise ValueError(f"Header tabel (kolom IDPEL) tidak ditemukan pada berkas: {excel_path}")


def _map_columns(headers: List[str]) -> Dict[str, Optional[int]]:
    """Memetakan indeks kolom relevan dari header Excel ARGUS maupun formulir GT."""
    def find_col(patterns: List[str]) -> Optional[int]:
        for pat in patterns:
            for i, h in enumerate(headers):
                if re.search(pat, h, re.IGNORECASE):
                    return i
        return None

    return {
        "no": find_col([r"^NO$"]),
        "idpel": find_col([r"\bIDPEL\b"]),
        "nama": find_col([r"NAMA PELANGGAN", r"\bNAMA\b"]),
        "tarif_daya": find_col([r"TARIF\s*/?\s*DAYA"]),
        "stan_lapangan": find_col([r"STAN\s*LAPANGAN", r"STAND\s*LAPANGAN"]),
        "raw_argus": find_col([r"HASIL ANALISA ARGUS"]),
        "stan_argus": find_col([r"HASIL STAN BACA", r"STAN ARGUS"]),
        "verdict": find_col([r"VONIS AUDIT", r"\bSTATUS\b"]),
        "link_foto": find_col([r"LINK FOTO ASLI"]),
        "filename": find_col([r"NAMA FILE FOTO", r"\bFILENAME\b"]),
        "gt_stand": find_col([r"GT_STAND", r"GROUND TRUTH STAND"]),
        "gt_status": find_col([r"GT_STATUS", r"GROUND TRUTH VONIS", r"GROUND TRUTH STATUS"]),
        "gt_notes": find_col([r"CATATAN SUPERVISOR", r"GT_NOTES"]),
    }


def _cell_str(row: Tuple[Any, ...], idx: Optional[int], default: str = "") -> str:
    if idx is None or idx >= len(row) or row[idx] is None:
        return default
    return str(row[idx]).strip()


def prepare_ground_truth_sheet(
    input_excel: Path,
    output_excel: Path,
    sample_size: int = 100,
    seed: int = 42,
    photo_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Membuat formulir Excel acak terukur untuk verifikasi manual Ground Truth bersama PLN."""
    headers, data_rows = _find_header_and_rows(input_excel)
    cols = _map_columns(headers)

    valid_rows = [r for r in data_rows if _cell_str(r, cols["idpel"])]
    if not valid_rows:
        raise ValueError("Tidak ditemukan baris pelanggan (IDPEL valid) pada berkas sumber.")

    actual_n = min(sample_size, len(valid_rows))
    rng = random.Random(seed)
    sampled_rows = rng.sample(valid_rows, actual_n)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ground Truth Sampling"

    out_cols = [
        ("NO SAMPEL", 11),
        ("IDPEL", 15),
        ("NAMA PELANGGAN", 24),
        ("TARIF / DAYA", 14),
        ("STAN LAPANGAN", 15),
        ("HASIL ANALISA ARGUS", 20),
        ("HASIL STAN BACA (AI)", 20),
        ("VONIS AUDIT (AI)", 22),
        ("LINK FOTO ASLI", 18),
        ("NAMA FILE FOTO", 28),
        ("GT_STAND_RIIL (ISI MANUAL PLN)", 26),
        ("GT_STATUS (SESUAI / KELAINAN)", 28),
        ("CATATAN SUPERVISOR PLN", 32),
    ]

    thin = Side(style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_fill = PatternFill(start_color="005A87", fill_type="solid")
    gt_hdr_fill = PatternFill(start_color="B45309", fill_type="solid")
    gt_cell_fill = PatternFill(start_color="FEF9C3", fill_type="solid")

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(out_cols))
    title_cell = ws.cell(
        row=1,
        column=1,
        value=f"FORMULIR UJI VALIDASI GROUND TRUTH ({actual_n} SAMPEL ACAK, SEED={seed}) — PT PLN (PERSERO) UP3 MOJOKERTO",
    )
    title_cell.fill = hdr_fill
    title_cell.font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(out_cols))
    sub_cell = ws.cell(
        row=2,
        column=1,
        value="Petunjuk Pengisian: Isi kolom kuning GT_STAND_RIIL dengan angka meter sebenarnya & GT_STATUS dengan 'SESUAI' atau 'KELAINAN'. Lead Engineer: Benedictus Pascal.",
    )
    sub_cell.fill = PatternFill(start_color="E0F2FE", fill_type="solid")
    sub_cell.font = Font(name="Segoe UI", size=9.5, italic=True, color="0369A1")
    sub_cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 20

    for c_idx, (col_name, col_width) in enumerate(out_cols, start=1):
        cell = ws.cell(row=3, column=c_idx, value=col_name)
        cell.fill = gt_hdr_fill if c_idx >= 11 else hdr_fill
        cell.font = Font(name="Segoe UI", size=9.5, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        ws.column_dimensions[get_column_letter(c_idx)].width = col_width
    ws.row_dimensions[3].height = 28

    resolved_photo_dir = photo_dir.resolve() if photo_dir is not None else None
    link_font = Font(name="Segoe UI", size=9.5, color="0369A1", underline="single")

    for sample_no, row in enumerate(sampled_rows, start=1):
        r_idx = sample_no + 3
        filename_val = _cell_str(row, cols["filename"])
        raw_link = row[cols["link_foto"]] if cols["link_foto"] is not None and cols["link_foto"] < len(row) else "-"
        if resolved_photo_dir is not None and filename_val:
            candidate = resolved_photo_dir / Path(filename_val).name
            if candidate.is_file():
                raw_link = f'=HYPERLINK("{str(candidate)}", "📷 Buka Foto Asli")'
        vals = [
            sample_no,
            _cell_str(row, cols["idpel"]),
            _cell_str(row, cols["nama"]),
            _cell_str(row, cols["tarif_daya"]),
            _cell_str(row, cols["stan_lapangan"]),
            _cell_str(row, cols["raw_argus"], "-"),
            _cell_str(row, cols["stan_argus"], "-"),
            _cell_str(row, cols["verdict"], "-"),
            raw_link if raw_link else "-",
            filename_val,
            "",
            "",
            "",
        ]
        for c_idx, val in enumerate(vals, start=1):
            c = ws.cell(row=r_idx, column=c_idx, value=val)
            c.border = border
            c.font = link_font if (c_idx == 9 and isinstance(val, str) and val.startswith("=HYPERLINK")) else Font(name="Segoe UI", size=9.5)
            c.alignment = Alignment(
                horizontal="left" if c_idx in (3, 10, 13) else "center",
                vertical="center",
            )
            if c_idx >= 11:
                c.fill = gt_cell_fill

    output_excel.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_excel))
    return {
        "source_rows": len(valid_rows),
        "sampled_count": actual_n,
        "seed": seed,
        "output_excel": str(output_excel),
    }


def score_ground_truth_sheet(gt_excel: Path, json_out: Optional[Path] = None) -> Dict[str, Any]:
    """Menghitung metrik lengkap Akurasi Stand, Precision, Recall, dan F1-Score dari berkas GT."""
    headers, data_rows = _find_header_and_rows(gt_excel)
    cols = _map_columns(headers)

    if cols["gt_stand"] is None and cols["gt_status"] is None:
        raise ValueError("Kolom 'GT_STAND_RIIL' maupun 'GT_STATUS' tidak ditemukan di berkas input.")

    stand_checked = 0
    stand_exact_match = 0
    abs_errors: List[float] = []

    tp = fp = tn = fn = 0
    total_rows = 0

    for row in data_rows:
        if not _cell_str(row, cols["idpel"]):
            continue
        total_rows += 1

        pred_stand = _cell_str(row, cols["stan_argus"])
        gt_stand = _cell_str(row, cols["gt_stand"])
        is_exact = stands_match(pred_stand, gt_stand)
        if is_exact is not None:
            stand_checked += 1
            if is_exact:
                stand_exact_match += 1
            p_num = parse_numeric_stand(pred_stand)
            g_num = parse_numeric_stand(gt_stand)
            if p_num is not None and g_num is not None:
                abs_errors.append(abs(p_num - g_num))

        pred_anom = is_anomaly_verdict(_cell_str(row, cols["verdict"]))
        gt_anom = is_anomaly_verdict(_cell_str(row, cols["gt_status"]))
        if pred_anom is not None and gt_anom is not None:
            if pred_anom and gt_anom:
                tp += 1
            elif pred_anom and not gt_anom:
                fp += 1
            elif not pred_anom and gt_anom:
                fn += 1
            else:
                tn += 1

    cls_total = tp + fp + tn + fn
    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    cls_acc = ((tp + tn) / cls_total) if cls_total > 0 else 0.0
    stand_acc = (stand_exact_match / stand_checked) if stand_checked > 0 else 0.0
    mae_kwh = (sum(abs_errors) / len(abs_errors)) if abs_errors else 0.0
    false_billing_escape = (fn / cls_total) if cls_total > 0 else 0.0
    auto_clear_rate = ((tn + fn) / cls_total) if cls_total > 0 else 0.0

    summary: Dict[str, Any] = {
        "file": str(gt_excel),
        "total_rows": total_rows,
        "stand_evaluation": {
            "evaluated_count": stand_checked,
            "exact_match_count": stand_exact_match,
            "exact_match_accuracy_pct": round(stand_acc * 100, 2),
            "mae_kwh": round(mae_kwh, 2),
        },
        "classification_evaluation": {
            "evaluated_count": cls_total,
            "confusion_matrix": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
            "precision_pct": round(precision * 100, 2),
            "recall_pct": round(recall * 100, 2),
            "f1_score_pct": round(f1 * 100, 2),
            "accuracy_pct": round(cls_acc * 100, 2),
            "false_billing_escape_pct": round(false_billing_escape * 100, 2),
            "auto_clearance_rate_pct": round(auto_clear_rate * 100, 2),
        },
    }

    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    return summary


def print_evaluation_report(summary: Dict[str, Any]) -> None:
    """Mencetak ringkasan metrik Ground Truth dalam format laporan teknis."""
    s_eval = summary["stand_evaluation"]
    c_eval = summary["classification_evaluation"]
    cm = c_eval["confusion_matrix"]

    print("\n" + "=" * 72)
    print("📊 LAPORAN EVALUASI GROUND TRUTH — PROJECT ARGUS (PT PLN UP3 MOJOKERTO)")
    print("=" * 72)
    print(f"Berkas Uji        : {summary['file']}")
    print(f"Total Baris Sampel: {summary['total_rows']}")
    print("-" * 72)
    print("1. AKURASI PEMBACAAN STAND METER (OCR DIGIT):")
    print(f"   • Sampel Terisi : {s_eval['evaluated_count']}")
    print(f"   • Cocok Eksak   : {s_eval['exact_match_count']} ({s_eval['exact_match_accuracy_pct']}%)")
    print(f"   • MAE kWh       : {s_eval['mae_kwh']} kWh")
    print("-" * 72)
    print("2. KLASIFIKASI DETEKSI KELAINAN / ANOMALI (Positif = Kelainan/Triage):")
    print(f"   • Sampel Terisi : {c_eval['evaluated_count']}")
    print(f"   • Confusion Mat : TP={cm['TP']} | FP={cm['FP']} | TN={cm['TN']} | FN={cm['FN']}")
    print(f"   • Precision     : {c_eval['precision_pct']}%")
    print(f"   • Recall        : {c_eval['recall_pct']}%")
    print(f"   • F1-Score      : {c_eval['f1_score_pct']}%")
    print(f"   • Akurasi Vonis : {c_eval['accuracy_pct']}%")
    print(f"   • Auto-Clearance: {c_eval['auto_clearance_rate_pct']}% (hemat beban cek manual)")
    print(f"   • Lolos Salah   : {c_eval['false_billing_escape_pct']}% (FN - bahaya billing)")
    print("=" * 72 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="ARGUS Phase 4 Ground Truth Sampling & Scientific Metric Calculator (Lead Engineer: Benedictus Pascal)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare", help="Buat formulir uji Ground Truth (100 sampel acak) dari hasil ekspor ARGUS.")
    prep.add_argument("--input", required=True, type=Path, help="Path file Excel hasil ekspor ARGUS (.xlsx).")
    prep.add_argument("--output", required=True, type=Path, help="Path output formulir Excel Ground Truth (.xlsx).")
    prep.add_argument("--samples", type=int, default=100, help="Jumlah sampel acak (default: 100).")
    prep.add_argument("--seed", type=int, default=42, help="Seed pengacakan agar reprodusibel (default: 42).")
    prep.add_argument("--photo-dir", type=Path, default=None, help="Opsional: folder foto asli agar hyperlink Excel 100% langsung terbuka.")

    sc = sub.add_parser("score", help="Hitung Precision, Recall, F1-Score, dan Akurasi Stand dari formulir Ground Truth.")
    sc.add_argument("--input", required=True, type=Path, help="Path formulir Ground Truth Excel yang sudah diisi PLN.")
    sc.add_argument("--json-out", type=Path, default=None, help="Opsional: simpan ringkasan metrik ke berkas JSON.")

    args = parser.parse_args()
    if args.command == "prepare":
        res = prepare_ground_truth_sheet(
            args.input,
            args.output,
            sample_size=args.samples,
            seed=args.seed,
            photo_dir=args.photo_dir,
        )
        print(f"✅ Formulir Ground Truth selesai dibuat: {res['output_excel']} ({res['sampled_count']} dari {res['source_rows']} baris, seed={res['seed']}).")
    elif args.command == "score":
        summary = score_ground_truth_sheet(args.input, json_out=args.json_out)
        print_evaluation_report(summary)
        if args.json_out:
            print(f"💾 Ringkasan JSON tersimpan ke: {args.json_out}")


if __name__ == "__main__":
    main()
