#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
PROJECT ARGUS: BATCH AUDIT EXCEL ENGINE (TAHAP 5 - V2.0 UPGRADE)
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Pascol
=============================================================================
Skrip batch auditor mandiri untuk menguji ratusan foto lapangan secara
otomatis dari Master Excel LBKB ('Detail' sheet), membandingkan angka stan
petugas lapangan vs hasil bacaan AI ARGUS, menyediakan hyperlink interaktif
ke FOTO ASLI dan HASIL DETEKSI AI, serta memberikan diagnosa audit yang cerdas.
=============================================================================
"""

import sys
import io
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

import cv2
import numpy as np
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Fix Windows console UTF-8 encoding
if __name__ == "__main__" and sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# Pastikan root direktori proyek ARGUS masuk ke sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.vision_ai.pipeline import ArgusVisionPipeline


# Style Excel Palettes
HEADER_FILL = PatternFill(start_color="002060", end_color="002060", fill_type="solid")  # PLN Deep Navy
HEADER_FONT = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")

# Palette Penanda Audit Visual
FILL_MATCH = PatternFill(start_color="D9EAD3", fill_type="solid")        # Hijau Muda Segar (100% Match / Sesuai Desimal)
FILL_ROLLING = PatternFill(start_color="FFF2CC", fill_type="solid")      # Kuning Muda (Rolling Digit ±1-2 kWh)
FILL_TRIAGE = PatternFill(start_color="FFE599", fill_type="solid")       # Kuning Emas (Review Manual / Triage)
FILL_NIHIL = PatternFill(start_color="F4CCCC", fill_type="solid")        # MERAH SOFT (Kotak KWH Tidak Terdeteksi / Counter Nihil)
FILL_BEDA_STAND = PatternFill(start_color="FCE5CD", fill_type="solid")   # ORANYE PEACH (Beda Stand dengan Selisih Nyata)
FILL_BURAM = PatternFill(start_color="EFEFEF", fill_type="solid")        # Abu-Abu (Foto Goyang / Buram)
FILL_SILAU = PatternFill(start_color="FFF2CC", fill_type="solid")        # Kuning Hangat (Silau Matahari)

FONT_LINK = Font(name="Segoe UI", size=10, color="0563C1", underline="single", bold=True)
FONT_REGULAR = Font(name="Segoe UI", size=10)
FONT_BOLD = Font(name="Segoe UI", size=10, bold=True)
ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")

THIN_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC")
)


def find_photo_file(photo_dir: Path, blth: str, idpel: str) -> Optional[Path]:
    """Mencari file citra meteran berdasarkan IDPEL dan BLTH di folder dokumentasi."""
    candidates = [
        photo_dir / f"{blth}-{idpel}-L.jpg",
        photo_dir / f"{blth}-{idpel}-1.jpg",
        photo_dir / f"{blth}-{idpel}-2.jpg",
        photo_dir / f"{blth}-{idpel}.jpg",
        photo_dir / f"{idpel}-L.jpg",
        photo_dir / f"{idpel}.jpg",
    ]
    for c in candidates:
        if c.is_file():
            return c

    # Fallback: scan glob jika pola penamaan sedikit berbeda
    matched = list(photo_dir.glob(f"*{idpel}*.jpg"))
    if matched:
        return matched[0]
    return None


def run_batch_audit(
    excel_path: Path,
    photo_dir: Path,
    output_excel: Path,
    limit: int = 100,
    save_annotated: bool = True,
    save_mode: str = "focused",
    harvest: bool = False,
    harvest_dir: Optional[Path] = None,
    digit_model_path: Optional[Path] = None
):
    print("=" * 85)
    print("⚡ PROJECT ARGUS - BATCH AUDIT EXCEL ENGINE (V2.5 AUTO-HARVEST EDITION)")
    print("   PT PLN (Persero) UP3 Mojokerto | Lead Engineer: Pascol")
    print("=" * 85)
    print(f"📂 File Master Excel : {excel_path}")
    print(f"📁 Folder Foto       : {photo_dir}")
    print(f"🎯 Target Audit      : {limit} Foto Lapangan Riil")
    print(f"📊 Output Laporan    : {output_excel}")
    if digit_model_path:
        print(f"🧠 Model Digit AI    : {digit_model_path.name}")
    if harvest:
        h_dir = harvest_dir or (BASE_DIR / "data" / "harvest_anomalies")
        print(f"📦 Auto-Harvest      : AKTIF (Target Anomali -> {h_dir})")
    print(f"🖼️ Mode Simpan Foto  : {save_mode.upper()} ({'Fokus Anomali/Tinjau Ulang' if save_mode == 'focused' else 'Semua Sampel' if save_mode == 'all' else 'Nonaktif'})")
    print("=" * 85)

    if not excel_path.is_file():
        print(f"❌ Error: File master Excel tidak ditemukan: {excel_path}")
        return

    if not photo_dir.is_dir():
        print(f"❌ Error: Folder foto tidak ditemukan: {photo_dir}")
        return

    # Inisialisasi Pipeline AI Lokal
    pipeline = ArgusVisionPipeline(digit_model_path=str(digit_model_path) if digit_model_path else None)

    # Buka Master Excel
    print(f"📖 Membaca sheet 'Detail' dari master Excel...")
    t_start_read = time.time()
    wb_master = openpyxl.load_workbook(str(excel_path), read_only=True, data_only=True)
    ws_master = wb_master["Detail"] if "Detail" in wb_master.sheetnames else wb_master.active
    print(f"✅ Master Excel berhasil dibaca ({round(time.time() - t_start_read, 2)}s)")

    # Mapping Header Baris Pertama
    header_indices = {}
    rows_to_process = []
    
    print("🔍 Menyeleksi baris data yang memiliki file foto fisik...")
    for row_idx, row in enumerate(ws_master.iter_rows(values_only=True)):
        if row_idx == 0:
            for col_idx, col_name in enumerate(row):
                if col_name:
                    header_indices[str(col_name).strip().upper()] = col_idx
            continue

        idpel = str(row[header_indices.get("IDPEL", 1)] or "").strip()
        blth = str(row[header_indices.get("BLTH", 2)] or "").strip()
        nama = str(row[header_indices.get("NAMA", 3)] or "").strip()
        tarif = str(row[header_indices.get("TARIF", 5)] or "").strip()
        daya = str(row[header_indices.get("DAYA", 6)] or "").strip()
        kdbaca = str(row[header_indices.get("KDBACA", 7)] or "").strip()
        stan_lapangan_raw = str(row[header_indices.get("STAN_BACA", 13)] or "").strip()

        if not idpel or idpel == "None":
            continue

        photo_file = find_photo_file(photo_dir, blth, idpel)
        if photo_file:
            rows_to_process.append({
                "idpel": idpel,
                "blth": blth,
                "nama": nama,
                "tarif_daya": f"{tarif}/{daya}",
                "kdbaca": kdbaca,
                "stan_lapangan_raw": stan_lapangan_raw,
                "photo_file": photo_file
            })

        if len(rows_to_process) >= limit:
            break

    total_found = len(rows_to_process)
    print(f"🎯 Terpilih {total_found} data pelanggan dengan foto fisik siap audit!\n")

    if total_found == 0:
        print("❌ Tidak ada foto fisik yang cocok dengan data Excel.")
        return

    # Folder Output Anotasi Citra
    annotated_dir = None
    if save_annotated:
        annotated_dir = output_excel.parent / "annotated_samples"
        annotated_dir.mkdir(parents=True, exist_ok=True)

    # Inisialisasi Direktori Auto-Harvest untuk Training Roboflow
    manifest_csv_file = None
    if harvest:
        harvest_dir = harvest_dir or (BASE_DIR / "data" / "harvest_anomalies")
        harvest_dir.mkdir(parents=True, exist_ok=True)

        # 1. Simpan classes.txt format YOLOv8 (11 kelas)
        classes_file = harvest_dir / "classes.txt"
        classes_names = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "dots"]
        classes_file.write_text("\n".join(classes_names) + "\n", encoding="utf-8")

        # 2. Inisialisasi manifest CSV
        manifest_csv_file = harvest_dir / "harvest_manifest.csv"
        with open(manifest_csv_file, "w", encoding="utf-8") as f_man:
            f_man.write("NO,IDPEL,BLTH,STAN_LAPANGAN,STAN_ARGUS,SELISIH,VONIS,DIAGNOSA,IMAGE_CROP,LABEL_TXT\n")

    # Eksekusi Batch Audit
    audit_results = []
    stats = {
        "MATCH": 0,
        "ROLLING": 0,
        "MISMATCH": 0,
        "TRIAGE": 0,
        "GLARE": 0,
        "BLUR": 0,
        "FRAUD": 0,
        "HARVESTED": 0,
        "total_latency_ms": 0.0
    }

    print("-" * 105)
    print(f"{'NO':<4} | {'IDPEL':<13} | {'PLN':<7} | {'RAW AI':<8} | {'ARGUS':<8} | {'VONIS':<18} | {'DIAGNOSA DETAIL':<30} | {'LATENCY'}")
    print("-" * 105)

    t0_all = time.time()

    for idx, item in enumerate(rows_to_process, 1):
        photo_path = item["photo_file"]
        stan_lapangan = item["stan_lapangan_raw"]
        kdbaca = item["kdbaca"]
        
        # Eksekusi AI Pipeline lokal
        t0_single = time.time()
        pred = pipeline.predict_image(
            str(photo_path),
            output_dir=str(annotated_dir) if (save_annotated and save_mode != "none") else None,
            save_mode=save_mode
        )
        latency_ms = round((time.time() - t0_single) * 1000, 1)
        stats["total_latency_ms"] += latency_ms

        stan_argus = str(pred.get("stand_baca") or "").strip()
        raw_display = str(pred.get("raw_display") or "-").strip()
        tier_color = pred.get("tier_color", "RED")
        pred_status = pred.get("status", "UNKNOWN")

        # Pembersihan digit numerik & ekstraksi token raw
        clean_pln = "".join(filter(str.isdigit, stan_lapangan))
        clean_argus = "".join(filter(str.isdigit, stan_argus))
        raw_digits = "".join(filter(str.isdigit, raw_display))
        clean_pln_nz = clean_pln.lstrip("0") or ("0" if clean_pln else "")
        raw_digits_nz = raw_digits.lstrip("0") or ("0" if raw_digits else "")
        int_part_raw = raw_display.split(".")[0] if "." in raw_display else raw_display
        int_digits_raw = "".join(filter(str.isdigit, int_part_raw))
        int_digits_raw_nz = int_digits_raw.lstrip("0") or ("0" if int_digits_raw else "")

        # -----------------------------------------------------------------
        # PRE-CHECK RESCUE: GROUND-TRUTH CONSENSUS & SMARTMETER MATCHER
        # Menyelamatkan pembacaan AI pada raw_display yang sudah akurat terhadap
        # data lapangan namun tertahan oleh penalti confidence rendah / titik koma
        # (Menyelesaikan Kasus 100, 119, 122, 125, 135, 137, 176, 186, 207, 245, 252, 272, 289, 312, 325, 326, 337)
        # -----------------------------------------------------------------
        if pred_status not in ("FAIL_COUNTER_NOT_FOUND", "ANOMALI_GLARE_TERHALANG", "REJECTED_BLUR", "RESOLUSI_TERLALU_RENDAH", "STAND_KOSONG"):
            if not clean_argus and raw_digits and clean_pln:
                dec_diff_len = len(raw_digits_nz) - len(clean_pln_nz)
                # 1. Integer sebelum titik cocok persis (misal '76.19' vs '76' atau '107.93' vs '107')
                if "." in raw_display and int_digits_raw and int_digits_raw_nz == clean_pln_nz:
                    stan_argus = int_digits_raw
                    clean_argus = int_digits_raw
                # 2. Seluruh digit cocok persis / Smartmeter Omit-Dot (misal Kasus 272 '25357' == '25357', Kasus 245 '17397' == '17397')
                elif raw_digits_nz == clean_pln_nz:
                    stan_argus = clean_pln if "." in raw_display else raw_digits
                    clean_argus = stan_argus
                # 3. Smartmeter Decimal Prefix Match (1-3 digit desimal di belakang, misal Kasus 100 '62271' vs '62', Kasus 119 '5375' vs '53')
                elif raw_digits_nz.startswith(clean_pln_nz) and 1 <= dec_diff_len <= 3 and (
                    "." in raw_display or not raw_digits.startswith("0") or len(raw_digits) == 6
                ):
                    stan_argus = clean_pln
                    clean_argus = clean_pln
                # 4. Obstruksi 4-digit cocok prefix/suffix terhadap 5-digit PLN (misal Kasus 86 '1982' vs '11982')
                elif len(clean_pln) == 5 and len(raw_digits) == 4 and (
                    clean_pln.startswith(raw_digits) or clean_pln.endswith(raw_digits)
                ):
                    stan_argus = raw_digits
                    clean_argus = raw_digits
                # 5. Single-digit defect / rolling satuan pada 5-digit (misal Kasus 325 / Baris 331 '04438' vs '14439')
                elif len(clean_pln) <= 5 and len(raw_digits) == 5:
                    p_pln_pre = clean_pln.zfill(5)
                    p_raw_pre = raw_digits.zfill(5)
                    diff_pos_pre = [i for i in range(5) if p_pln_pre[i] != p_raw_pre[i]]
                    diff_f4_pre = [i for i in range(4) if p_pln_pre[i] != p_raw_pre[i]]
                    diff_last_pre = abs(int(p_pln_pre[4]) - int(p_raw_pre[4]))
                    if len(diff_pos_pre) == 1 or (len(diff_f4_pre) == 1 and diff_last_pre in (1, 2, 9)):
                        stan_argus = raw_digits
                        clean_argus = raw_digits

        verdict = "TIDAK_DIKENAL"
        diagnosa_detail = pred_status
        selisih = "-"

        # -----------------------------------------------------------------
        # EVALUASI LOGIKA DIAGNOSA CERDAS (STANDAR PLN TERSTRUKTUR)
        # -----------------------------------------------------------------
        # 1. Kasus Meter Tidak Terdeteksi (Kotak Counter Nihil)
        if pred_status == "FAIL_COUNTER_NOT_FOUND":
            verdict = "TIDAK_TERDETEKSI_KWH"
            diagnosa_detail = "KOTAK METER TIDAK TERDETEKSI"
            stats["FRAUD"] += 1

        # 2. Kasus Silau Ekstrem
        elif pred_status == "ANOMALI_GLARE_TERHALANG":
            verdict = "FOTO_SILAU"
            glare_pct = pred.get("glare_percentage", 0)
            diagnosa_detail = f"SILAU MATAHARI ({glare_pct}%)"
            stats["GLARE"] += 1

        # 3. Kasus Foto Buram Goyang
        elif pred_status == "REJECTED_BLUR":
            verdict = "FOTO_BURAM"
            diagnosa_detail = f"FOTO BURAM (Laplacian: {round(pred.get('blur_score', 0), 1)})"
            stats["BLUR"] += 1

        # 4. Kasus Foto dari Jarak Terlalu Jauh / Resolusi Rendah
        elif pred_status == "RESOLUSI_TERLALU_RENDAH":
            verdict = "PERLU_TINJAU_ULANG"
            diagnosa_detail = "RESOLUSI RENDAH / TERLALU JAUH"
            stats["TRIAGE"] += 1

        # 5. Kasus Stand Kosong / Gelap
        elif pred_status == "STAND_KOSONG":
            verdict = "PERLU_TINJAU_ULANG"
            diagnosa_detail = "COUNTER GELAP / MIKA KOTOR"
            stats["TRIAGE"] += 1

        # 6. Kasus Stand Valid Terbaca atau Berhasil Direscue oleh ARGUS
        elif clean_argus:
            val_argus = int(clean_argus)

            if clean_pln:
                val_pln = int(clean_pln)
                diff = val_argus - val_pln
                selisih = str(diff)
                dec_diff_len = len(raw_digits_nz) - len(clean_pln_nz)

                # Multi-Candidate Overlap Consensus (Menyelesaikan Kasus 136 '10116' vs '10118' & Kasus 185 '50' vs '90')
                if val_argus != val_pln:
                    numeric_digits = [d for d in pred.get("digits_detail", []) if str(d.get("digit", "")).isdigit()]
                    if len(clean_argus) == len(clean_pln) and len(numeric_digits) >= len(clean_argus):
                        diff_pos_list = [i for i in range(len(clean_argus)) if clean_argus[i] != clean_pln[i]]
                        if len(diff_pos_list) == 1:
                            d_idx = diff_pos_list[0]
                            target_char = clean_pln[d_idx]
                            alts = [a.get("digit") for a in numeric_digits[d_idx].get("alt_candidates", [])]
                            if target_char in alts:
                                clean_argus = clean_pln
                                stan_argus = clean_pln
                                val_argus = val_pln
                                diff = 0
                                selisih = "0"

                # A. Deteksi Obstruksi Fisik 4-Digit Cocok Prefix/Suffix
                # Kasus 75: Meter PLN 5-digit tapi terbaca 4-digit yang cocok prefix (digit terakhir tertutup)
                if len(clean_pln) == 5 and len(clean_argus) == 4 and clean_pln.startswith(clean_argus):
                    verdict = "PERLU_TINJAU_ULANG"
                    diagnosa_detail = "OBSTRUKSI FISIK (DIGIT TERAKHIR TERHALANG)"
                    stats["TRIAGE"] += 1

                # Kasus 86: Meter PLN 5-digit tapi terbaca 4-digit yang cocok suffix (digit pertama tidak terbaca / gelap)
                elif len(clean_pln) == 5 and len(clean_argus) == 4 and clean_pln.endswith(clean_argus):
                    verdict = "PERLU_TINJAU_ULANG"
                    diagnosa_detail = "OBSTRUKSI FISIK (DIGIT PERTAMA TIDAK TERBACA)"
                    stats["TRIAGE"] += 1

                # B. Cocok Persis (Exact Integer Match)
                elif val_pln == val_argus:
                    verdict = "SESUAI_MATCH"
                    if raw_digits_nz.startswith(clean_pln_nz) and len(raw_digits_nz) > len(clean_pln_nz):
                        decimals = raw_digits_nz[len(clean_pln_nz):]
                        selisih = f"+0.{decimals}"
                        diagnosa_detail = "SESUAI (Desimal Merah)" if (len(raw_digits) == 6 and len(decimals) == 1) else "SESUAI (Smartmeter Desimal)"
                    elif "." in raw_display and raw_digits_nz == clean_pln_nz and int_digits_raw_nz != clean_pln_nz:
                        selisih = "0"
                        diagnosa_detail = "SESUAI (Smartmeter Tanpa Koma)"
                    elif len(clean_argus) == 5:
                        diagnosa_detail = "SESUAI IDEAL (5 Digit)"
                    elif len(clean_argus) == 4:
                        diagnosa_detail = "SESUAI (4 Digit Meter Baru)"
                    else:
                        diagnosa_detail = f"SESUAI ({len(clean_argus)} Digit)"
                    stats["MATCH"] += 1

                # C. Smartmeter "Omit-Dot" Matcher (Kasus No. 3 '54.63' vs '5463', Kasus 403 '00157.3' vs '1573')
                elif raw_digits and raw_digits_nz == clean_pln_nz:
                    verdict = "SESUAI_MATCH"
                    stan_argus = clean_pln
                    selisih = "0"
                    diagnosa_detail = "SESUAI (Smartmeter Tanpa Koma)"
                    stats["MATCH"] += 1

                # D. Smartmeter & Analog Decimal Prefix Matcher (Menyelesaikan Kasus 156, 178, 181, 276, 362, 370, 371)
                elif raw_digits and raw_digits_nz.startswith(clean_pln_nz) and 1 <= dec_diff_len <= 3 and (
                    "." in raw_display or not raw_digits.startswith("0") or len(raw_digits) == 6
                ):
                    verdict = "SESUAI_MATCH"
                    decimals = raw_digits_nz[len(clean_pln_nz):]
                    stan_argus = clean_pln
                    selisih = f"+0.{decimals}"
                    diagnosa_detail = "SESUAI (Desimal Merah)" if (len(raw_digits) == 6 and len(decimals) == 1) else "SESUAI (Smartmeter Desimal)"
                    stats["MATCH"] += 1

                # E. Desimal Roda Merah Ikut Terbaca (6 Digit vs 5 Digit PLN)
                elif len(clean_argus) == 6 and clean_argus[:5] == clean_pln:
                    verdict = "SESUAI_MATCH"
                    selisih = f"+0.{clean_argus[5]}"
                    diagnosa_detail = "SESUAI (Desimal Merah)"
                    stats["MATCH"] += 1

                # F. Desimal Roda Merah Ikut Terbaca (5 Digit vs 4 Digit PLN)
                elif len(clean_argus) == 5 and clean_argus[:4] == clean_pln:
                    verdict = "SESUAI_MATCH"
                    selisih = f"+0.{clean_argus[4]}"
                    diagnosa_detail = "SESUAI (Desimal Merah)"
                    stats["MATCH"] += 1

                # G. Rolling Digit (Angka sedang berputar selisih murni ±1 atau ±2 kWh, atau transisi roda 0 <-> 9)
                elif abs(diff) in (1, 2) or (
                    len(clean_pln) <= 5 and len(clean_argus) == 5
                    and clean_pln.zfill(5)[:4] == clean_argus.zfill(5)[:4]
                    and (clean_pln.zfill(5)[4], clean_argus.zfill(5)[4]) in [('0', '9'), ('9', '0')]
                ):
                    verdict = "ROLLING_DIGIT"
                    diagnosa_detail = f"ANGKA GANTUNG / ROLLING ({diff:+d} kWh)"
                    stats["ROLLING"] += 1

                # H. Single-Digit Physical Defect Guard (4 dari 5 Digit Cocok 100%, 1 Digit Baret / Glare / Mika Kusam)
                # Menyelesaikan Kasus 56, 203, 291, 307, 325 (Baris 331), 377, 381, 388, 397, 409
                elif len(clean_pln) <= 5 and len(clean_argus) <= 5 and (
                    len([i for i in range(5) if clean_pln.zfill(5)[i] != clean_argus.zfill(5)[i]]) == 1
                    or (
                        len([i for i in range(4) if clean_pln.zfill(5)[i] != clean_argus.zfill(5)[i]]) == 1
                        and abs(int(clean_pln.zfill(5)[4]) - int(clean_argus.zfill(5)[4])) in (1, 2, 9)
                    )
                ):
                    p_pln_5 = clean_pln.zfill(5)
                    p_arg_5 = clean_argus.zfill(5)
                    diff_idxs = [i for i in range(5) if p_pln_5[i] != p_arg_5[i]]
                    first_diff_pos = diff_idxs[0] + 1
                    verdict = "PERLU_TINJAU_ULANG"
                    diagnosa_detail = f"1 DIGIT AMBIGU (4 DIGIT COCOK / CEK DIGIT KE-{first_diff_pos})"
                    stats["TRIAGE"] += 1

                # I. Selisih Nyata / Mismatch
                else:
                    verdict = "BEDA_STAND"
                    diagnosa_detail = f"BEDA STAND (Selisih {diff:+d} kWh)"
                    stats["MISMATCH"] += 1
            else:
                verdict = "BEDA_STAND"
                diagnosa_detail = "PLN STAN KOSONG"
                stats["MISMATCH"] += 1

        # 7. Kasus Obstruksi Fisik / Digit Parsial (Belum Ter-rescue)
        elif pred_status in ("STAND_TIDAK_LENGKAP", "OBSTRUKSI_FISIK"):
            verdict = "PERLU_TINJAU_ULANG"
            diagnosa_detail = "OBSTRUKSI FISIK (DIGIT PARSIAL)"
            stats["TRIAGE"] += 1

        # 8. Kasus Digit Ambigu (Confidence Rendah < 0.50, Belum Ter-rescue)
        elif pred_status == "DIGIT_AMBIGU":
            verdict = "PERLU_TINJAU_ULANG"
            diagnosa_detail = "DIGIT AMBIGU (CONFIDENCE RENDAH)"
            stats["TRIAGE"] += 1

        # 9. Kasus Layar Status Operasional LCD (TUTUP - TR, PERIKSA, OFF, dll)
        elif pred_status == "METER_STATUS_OPERASIONAL":
            verdict = "PERLU_TINJAU_ULANG"
            diagnosa_detail = "LAYAR OPERASIONAL (TUTUP/PERIKSA/STAND NON-AKTIF)"
            stats["TRIAGE"] += 1

        # 10. Kasus Tier Kuning / Perlu Analisis Manual Lainnya
        else:
            verdict = "PERLU_TINJAU_ULANG"
            diagnosa_detail = "PERLU ANALISIS MANUAL PETUGAS"
            stats["TRIAGE"] += 1

        if pred.get("dehaze_rescued"):
            diagnosa_detail += " [Penyelamatan Kabut]"

        # -----------------------------------------------------------------
        # MEKANISME AUTO-HARVEST ANOMALI (UNTUK TRAINING ROBOFLOW)
        # -----------------------------------------------------------------
        harvest_crop_file = None
        harvest_label_file = None
        is_harvested = False

        # Syarat Panen: Bukan SESUAI_MATCH, Bukan BUKAN_METER, dan Kotak Counter Terdeteksi
        is_anomaly = verdict in ("BEDA_STAND", "PERLU_TINJAU_ULANG", "ROLLING_DIGIT", "FOTO_SILAU")
        counter_box = pred.get("counter_box")

        if harvest and is_anomaly and counter_box:
            try:
                cx1, cy1, cx2, cy2 = counter_box
                raw_img = cv2.imread(str(photo_path))
                if raw_img is not None and cy2 > cy1 and cx2 > cx1:
                    clean_crop = raw_img[cy1:cy2, cx1:cx2]
                    if clean_crop.size > 0:
                        crop_h, crop_w = clean_crop.shape[:2]
                        prefix = f"{idx:05d}_{item['idpel']}_{item['blth']}_crop"
                        harvest_crop_file = harvest_dir / f"{prefix}.jpg"
                        harvest_label_file = harvest_dir / f"{prefix}.txt"

                        # 1. Simpan citra crop murni tanpa coretan visual
                        cv2.imwrite(str(harvest_crop_file), clean_crop)

                        # 2. Tulis file anotasi YOLOv8 otomatis (AI Pre-Labeling)
                        yolo_lines = []
                        for d in pred.get("digits_detail", []):
                            dx1, dy1, dx2, dy2 = d["x1"], d["y1"], d["x2"], d["y2"]
                            d_char = str(d.get("digit", ""))
                            if d_char.isdigit():
                                cls_id = int(d_char)
                            elif d_char in ("dots", "dot", ".", ","):
                                cls_id = 10
                            else:
                                continue

                            # Normalisasi koordinat ke rentang [0.0, 1.0]
                            cen_x = max(0.0, min(1.0, ((dx1 + dx2) / 2.0) / crop_w))
                            cen_y = max(0.0, min(1.0, ((dy1 + dy2) / 2.0) / crop_h))
                            bw = max(0.0, min(1.0, (dx2 - dx1) / crop_w))
                            bh = max(0.0, min(1.0, (dy2 - dy1) / crop_h))

                            yolo_lines.append(f"{cls_id} {cen_x:.6f} {cen_y:.6f} {bw:.6f} {bh:.6f}")

                        harvest_label_file.write_text("\n".join(yolo_lines) + ("\n" if yolo_lines else ""), encoding="utf-8")
                        stats["HARVESTED"] += 1
                        is_harvested = True

                        # 3. Catat entri ke harvest_manifest.csv
                        if manifest_csv_file and manifest_csv_file.is_file():
                            with open(manifest_csv_file, "a", encoding="utf-8") as f_man:
                                f_man.write(f'{idx},"{item["idpel"]}","{item["blth"]}","{stan_lapangan}","{stan_argus}","{selisih}","{verdict}","{diagnosa_detail}","{harvest_crop_file.name}","{harvest_label_file.name}"\n')
            except Exception as e:
                pass

        # File Anotasi Deteksi
        saved_paths = pred.get("saved_paths", {})
        ai_annotated_file = saved_paths.get("full_result") or saved_paths.get("crop_result")

        # Focused Mode Rescue: Jika ada anomali tetapi gambar belum disimpan (misal Green tapi beda stand),
        # simpan gambar anotasi untuk baris anomali ini agar auditor tetap bisa membuka fotonya
        if save_annotated and save_mode == "focused" and not ai_annotated_file and verdict != "SESUAI_MATCH" and annotated_dir:
            try:
                rescue_pred = pipeline.predict_image(str(photo_path), output_dir=str(annotated_dir), save_mode="all")
                r_saved = rescue_pred.get("saved_paths", {})
                ai_annotated_file = r_saved.get("full_result") or r_saved.get("crop_result")
            except Exception:
                pass

        audit_results.append({
            "no": idx,
            "idpel": item["idpel"],
            "nama": item["nama"],
            "tarif_daya": item["tarif_daya"],
            "kdbaca": item["kdbaca"],
            "stan_lapangan": stan_lapangan,
            "raw_display": raw_display,
            "stan_argus": stan_argus,
            "selisih": selisih,
            "verdict": verdict,
            "tier_color": tier_color,
            "diagnosa_detail": diagnosa_detail,
            "latency_ms": latency_ms,
            "blur_score": pred.get("blur_score", 0.0),
            "glare_ratio": pred.get("glare_ratio", 0.0),
            "filename": photo_path.name,
            "abs_photo_path": photo_path.resolve(),
            "ai_annotated_file": Path(ai_annotated_file).resolve() if ai_annotated_file else None,
            "harvest_crop_file": Path(harvest_crop_file).resolve() if harvest_crop_file else None,
            "is_harvested": is_harvested
        })

        # Cetak baris progres ke terminal
        status_disp = verdict
        if verdict == "SESUAI_MATCH":
            status_disp = "✅ SESUAI"
        elif verdict == "ROLLING_DIGIT":
            status_disp = "🔄 ROLLING"
        elif verdict == "BEDA_STAND":
            status_disp = "⚠️ BEDA STAND"
        elif verdict == "TIDAK_TERDETEKSI_KWH":
            status_disp = "🛑 KWH NIHIL"
        elif verdict == "FOTO_SILAU":
            status_disp = "☀️ SILAU"
        elif verdict == "FOTO_BURAM":
            status_disp = "🌫️ BURAM"
        elif verdict == "PERLU_TINJAU_ULANG":
            status_disp = "🔍 TINJAU ULANG"

        harvest_tag = "📦 [DIPANEN]" if is_harvested else ""
        print(f"{idx:<4} | {item['idpel']:<13} | {stan_lapangan[:7]:<7} | {raw_display[:8]:<8} | {stan_argus[:8]:<8} | {status_disp:<18} | {diagnosa_detail[:30]:<30} | {latency_ms:>5} ms {harvest_tag}")

    total_time_s = round(time.time() - t0_all, 2)
    avg_latency = round(stats["total_latency_ms"] / total_found, 1)

    print("-" * 95)
    print("\n" + "=" * 85)
    print("📊 REKAPITULASI HASIL AUDIT LAPANGAN ARGUS (V2.5)")
    print("=" * 85)
    print(f"Total Sampel Audit      : {total_found} Foto")
    print(f"Waktu Total Eksekusi    : {total_time_s} detik (Rata-rata: {avg_latency} ms/foto)")
    print(f"🟢 Sesuai / Match       : {stats['MATCH']} ({round(stats['MATCH']/total_found*100, 1)}%)")
    print(f"🟡 Rolling Digit (±1-2) : {stats['ROLLING']} ({round(stats['ROLLING']/total_found*100, 1)}%)")
    print(f"🟡 Perlu Tinjau Ulang   : {stats['TRIAGE']} ({round(stats['TRIAGE']/total_found*100, 1)}%)")
    print(f"🔴 Beda Stand Lapangan  : {stats['MISMATCH']} ({round(stats['MISMATCH']/total_found*100, 1)}%)")
    print(f"🔴 Silau (Tolak Tagih)  : {stats['GLARE']} ({round(stats['GLARE']/total_found*100, 1)}%)")
    print(f"🔴 Buram (Tolak Tagih)  : {stats['BLUR']} ({round(stats['BLUR']/total_found*100, 1)}%)")
    print(f"🔴 Fraud / Bukan Meter  : {stats['FRAUD']} ({round(stats['FRAUD']/total_found*100, 1)}%)")
    if harvest:
        print(f"📦 Total Anomali Dipanen: {stats['HARVESTED']} Pasang Citra & Label YOLOv8")
        print(f"📁 Folder Panen Roboflow: {harvest_dir}")
    print("=" * 85)

    # -----------------------------------------------------------------
    # MENULIS FILE OUTPUT EXCEL DENGAN DUAL HYPERLINK
    # -----------------------------------------------------------------
    print(f"\n📝 Menyusun Laporan Audit Excel Ber-Hyperlink: {output_excel} ...")
    output_excel.parent.mkdir(parents=True, exist_ok=True)

    wb_out = openpyxl.Workbook()
    ws_out = wb_out.active
    ws_out.title = "Hasil Audit ARGUS"

    columns = [
        ("NO", 6, ALIGN_CENTER),
        ("IDPEL", 15, ALIGN_CENTER),
        ("NAMA PELANGGAN", 25, ALIGN_LEFT),
        ("TARIF / DAYA", 14, ALIGN_CENTER),
        ("KDBACA", 10, ALIGN_CENTER),
        ("STAN LAPANGAN", 15, ALIGN_CENTER),
        ("RAW DISPLAY AI", 16, ALIGN_CENTER),
        ("STAN ARGUS", 15, ALIGN_CENTER),
        ("SELISIH kWh", 13, ALIGN_CENTER),
        ("VONIS AUDIT", 20, ALIGN_CENTER),
        ("DIAGNOSA DETAIL", 38, ALIGN_LEFT),
        ("LINK FOTO ASLI 📷", 22, ALIGN_CENTER),
        ("LINK HASIL DETEKSI AI 🤖", 25, ALIGN_CENTER),
        ("PANEN ROBOFLOW 📦", 22, ALIGN_CENTER),
        ("TIER COLOR", 13, ALIGN_CENTER),
        ("LATENSI (ms)", 13, ALIGN_RIGHT),
        ("SKOR BLUR", 13, ALIGN_RIGHT),
        ("SILAU (%)", 13, ALIGN_RIGHT),
        ("NAMA FILE FOTO", 32, ALIGN_LEFT),
    ]

    num_cols = len(columns)

    # -----------------------------------------------------------------
    # BARIS 1-4: PANDUAN KODE WARNA AUDIT ARGUS (EXECUTIVE LEGEND)
    # -----------------------------------------------------------------
    # Baris 1: Main Banner Title
    ws_out.merge_cells(start_row=1, start_column=1, end_row=1, end_column=num_cols)
    b1 = ws_out.cell(row=1, column=1, value="⚡ PROJECT ARGUS | LAPORAN AUDIT STAND KWH METER LBKB - PT PLN (PERSERO) UP3 MOJOKERTO")
    b1.fill = HEADER_FILL
    b1.font = Font(name="Segoe UI", size=12, bold=True, color="FFFFFF")
    b1.alignment = ALIGN_CENTER
    ws_out.row_dimensions[1].height = 25

    # Baris 2: Sub-Banner Lead Engineer & Info
    ws_out.merge_cells(start_row=2, start_column=1, end_row=2, end_column=num_cols)
    b2 = ws_out.cell(row=2, column=1, value="Sistem Pengawasan Otomatis Stand Meter AI Vision Lokal | Lead Engineer: Pascol | Perlindungan Billing & Tinjau Ulang")
    b2.fill = PatternFill(start_color="0B388A", fill_type="solid")
    b2.font = Font(name="Segoe UI", size=9.5, italic=True, color="E0E0E0")
    b2.alignment = ALIGN_CENTER
    ws_out.row_dimensions[2].height = 18

    # Baris 3: Header Panduan Warna
    ws_out.merge_cells(start_row=3, start_column=1, end_row=3, end_column=num_cols)
    b3 = ws_out.cell(row=3, column=1, value="🎨 PANDUAN KODE WARNA EVALUASI AUDITOR & INTERPRETASI SISTEM AI:")
    b3.fill = PatternFill(start_color="EAEEF3", fill_type="solid")
    b3.font = Font(name="Segoe UI", size=9.5, bold=True, color="002060")
    b3.alignment = ALIGN_LEFT
    ws_out.row_dimensions[3].height = 18

    # Baris 4: Kartu Legenda Warna (6 Kategori Visual)
    legend_cards = [
        (1, 3, "🟢 SESUAI MATCH : 100% Cocok / Desimal", FILL_MATCH, "1B5E20"),
        (4, 6, "🟡 ROLLING DIGIT : Angka Berputar (±1–2 kWh)", FILL_ROLLING, "7F6000"),
        (7, 9, "🟠 BEDA STAND : Selisih Nyata AI vs Lapangan", FILL_BEDA_STAND, "A04000"),
        (10, 12, "🔴 TIDAK TERDETEKSI KWH : Counter Nihil / Pagar", FILL_NIHIL, "9C0006"),
        (13, 16, "🟡 PERLU TINJAU ULANG : Obstruksi / 1 Digit Ambigu", FILL_TRIAGE, "7F6000"),
        (17, 19, "⚪ BURAM / SILAU : Kualitas Foto Ditolak", FILL_BURAM, "595959"),
    ]

    for start_c, end_c, text, fill_style, font_color in legend_cards:
        ws_out.merge_cells(start_row=4, start_column=start_c, end_row=4, end_column=end_c)
        card_cell = ws_out.cell(row=4, column=start_c, value=text)
        card_cell.fill = fill_style
        card_cell.font = Font(name="Segoe UI", size=8.5, bold=True, color=font_color)
        card_cell.alignment = ALIGN_CENTER
        card_cell.border = THIN_BORDER
        for c in range(start_c, end_c + 1):
            ws_out.cell(row=4, column=c).border = THIN_BORDER
            ws_out.cell(row=4, column=c).fill = fill_style

    ws_out.row_dimensions[4].height = 22
    ws_out.row_dimensions[5].height = 8  # Spacer row

    # -----------------------------------------------------------------
    # BARIS 6: HEADER TABEL DATA AUDIT
    # -----------------------------------------------------------------
    for col_idx, (col_name, width, align) in enumerate(columns, 1):
        cell = ws_out.cell(row=6, column=col_idx, value=col_name)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = ALIGN_CENTER
        cell.border = THIN_BORDER
        col_letter = get_column_letter(col_idx)
        ws_out.column_dimensions[col_letter].width = width
    ws_out.row_dimensions[6].height = 26

    # -----------------------------------------------------------------
    # BARIS 7 KE BAWAH: DATA HASIL AUDIT PER PELANGGAN
    # -----------------------------------------------------------------
    for row_idx, res in enumerate(audit_results, 7):
        # Format Formula Hyperlink Windows
        link_orig_formula = f'=HYPERLINK("{str(res["abs_photo_path"])}", "📷 Buka Foto Asli")'
        if res["ai_annotated_file"] and res["ai_annotated_file"].is_file():
            link_ai_formula = f'=HYPERLINK("{str(res["ai_annotated_file"])}", "🤖 Buka Hasil AI")'
        else:
            link_ai_formula = "-"

        if res.get("harvest_crop_file") and res["harvest_crop_file"].is_file():
            link_harvest_formula = f'=HYPERLINK("{str(res["harvest_crop_file"])}", "📦 Buka Crop Panen")'
        else:
            link_harvest_formula = "-"

        row_data = [
            res["no"],
            res["idpel"],
            res["nama"],
            res["tarif_daya"],
            res["kdbaca"],
            res["stan_lapangan"],
            res["raw_display"],
            res["stan_argus"],
            res["selisih"],
            res["verdict"],
            res["diagnosa_detail"],
            link_orig_formula,
            link_ai_formula,
            link_harvest_formula,
            res["tier_color"],
            res["latency_ms"],
            round(res["blur_score"], 1),
            f"{round(res['glare_ratio'] * 100, 1)}%",
            res["filename"]
        ]

        # Pemilihan Warna Highlight Baris
        row_fill = None
        if res["verdict"] == "SESUAI_MATCH":
            row_fill = FILL_MATCH
        elif res["verdict"] == "ROLLING_DIGIT":
            row_fill = FILL_ROLLING
        elif res["verdict"] in ("BUKAN_METER", "TIDAK_TERDETEKSI_KWH"):
            row_fill = FILL_NIHIL
        elif res["verdict"] == "BEDA_STAND":
            row_fill = FILL_BEDA_STAND
        elif res["verdict"] == "PERLU_TINJAU_ULANG":
            row_fill = FILL_TRIAGE
        elif res["verdict"] == "FOTO_SILAU":
            row_fill = FILL_SILAU
        elif res["verdict"] == "FOTO_BURAM":
            row_fill = FILL_BURAM

        for col_idx, val in enumerate(row_data, 1):
            cell = ws_out.cell(row=row_idx, column=col_idx, value=val)
            cell.font = FONT_REGULAR
            cell.alignment = columns[col_idx - 1][2]
            cell.border = THIN_BORDER

            # Penandaan Warna Sel Kunci (RAW DISPLAY, STAN ARGUS, SELISIH, VONIS, DIAGNOSA)
            if row_fill and col_idx in (7, 8, 9, 10, 11):
                cell.fill = row_fill
                if col_idx in (10, 11):
                    cell.font = FONT_BOLD

            # Khusus Kolom Hyperlink: Beri Gaya Link Biru Bergaris Bawah
            if col_idx in (12, 13, 14) and str(val).startswith("=HYPERLINK"):
                cell.font = FONT_LINK

    # Freeze Header (Baris 1-6 tetap tampak saat di-scroll ke bawah)
    ws_out.freeze_panes = "A7"

    wb_out.save(str(output_excel))
    print(f"\n🎉 SUKSES! File Laporan Audit Resmi Ber-Hyperlink tersimpan di:\n👉 {output_excel}")
    if annotated_dir:
        print(f"🖼️ Foto hasil crop & kotak deteksi tersimpan di:\n👉 {annotated_dir}")
    if harvest and stats["HARVESTED"] > 0:
        print(f"📦 Hasil Auto-Harvest Anomali ({stats['HARVESTED']} pasang gambar & label siap Roboflow) tersimpan di:\n👉 {harvest_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="ARGUS Batch Audit Excel Runner - PT PLN (Persero) UP3 Mojokerto"
    )
    parser.add_argument(
        "--excel-path",
        type=str,
        default=str(BASE_DIR / "Docs" / "File" / "12 LBKB Billing Rek 12 2025 copy+foto salinan.xlsx"),
        help="Path file master Excel PLN LBKB"
    )
    parser.add_argument(
        "--photo-dir",
        type=str,
        default=str(BASE_DIR / "Docs" / "DOkumentasi LBKB"),
        help="Path folder dokumentasi foto meteran"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=2500,
        help="Jumlah sampel foto riil yang ingin diaudit (default: 2500)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path output file Excel hasil audit (default: auto sesuai nilai --limit)"
    )
    parser.add_argument(
        "--no-crops",
        action="store_true",
        help="Jangan simpan foto hasil crop anotasi (menghemat disk)"
    )
    parser.add_argument(
        "--save-mode",
        type=str,
        choices=["focused", "all", "none"],
        default="focused",
        help="Mode simpan foto anotasi: 'focused' (hanya anomali/tinjau ulang), 'all' (semua), atau 'none'"
    )
    parser.add_argument(
        "--model-digit",
        type=str,
        default=None,
        help="Path file bobot model digit (default: digit_ocr_detector_v4.pt jika ada)"
    )
    parser.add_argument(
        "--harvest",
        action="store_true",
        default=False,
        help="Aktifkan Auto-Harvest foto anomali meteran (crop bersih + label YOLO .txt) untuk Roboflow (default: False)"
    )
    parser.add_argument(
        "--harvest-dir",
        type=str,
        default=str(BASE_DIR / "data" / "harvest_anomalies"),
        help="Folder penyimpanan pasangan crop .jpg dan label .txt untuk Roboflow"
    )

    args = parser.parse_args()

    limit = args.limit
    if args.output:
        out_excel = Path(args.output)
    else:
        out_excel = BASE_DIR / "data" / "audit_results" / f"Audit_LBKB_Result_{limit}_Samples.xlsx"

    digit_model = Path(args.model_digit) if args.model_digit else None

    save_mode = "none" if args.no_crops else args.save_mode
    run_batch_audit(
        excel_path=Path(args.excel_path),
        photo_dir=Path(args.photo_dir),
        output_excel=out_excel,
        limit=limit,
        save_annotated=(save_mode != "none"),
        save_mode=save_mode,
        harvest=args.harvest,
        harvest_dir=Path(args.harvest_dir) if args.harvest_dir else None,
        digit_model_path=digit_model
    )


if __name__ == "__main__":
    main()
