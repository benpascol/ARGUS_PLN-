"""
=============================================================================
PROJECT ARGUS: SEQUENCE & READING VALIDATION ARBITER
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Validasi sekuensial deretan horizontal angka meteran dan sistem triage 3 warna:
🟢 HIJAU  : SUKSES_ANALOG (5 digit seragam / 4 digit baru) / SUKSES_DIGITAL (Titik desimal terverifikasi)
🟡 KUNING : PERLU_TRIAGE / AMBIGU (Confidence rendah < 0.50, jeda abnormal, teks status LCD)
🔴 MERAH  : STAND_TIDAK_LENGKAP / ANOMALI (Digit < 4 dan span sempit akibat silau)
=============================================================================
"""

import numpy as np
from typing import Dict, Any, List


def validate_reading_sequence(detected_digits: List[Dict[str, Any]], crop_w: int, crop_h: int) -> Dict[str, Any]:
    """
    Two-Layer Sequence, Inter-Digit Gap & Spatial Validator (Sistem Triage 3 Warna).
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

    # KASUS TEKS STATUS OPERASIONAL LCD (Kasus Layar TUTUP - TR, PERIKSA, OFF, RELAY):
    ones_count = sum(1 for d in raw_tokens if d == "1")
    if num_tokens >= 5 and (ones_count / num_tokens) >= 0.55 and has_abnormal_gap:
        return {
            "is_valid": False,
            "stand_baca": None,
            "raw_display": "STATUS_LCD (TUTUP/PERIKSA)",
            "status": "METER_STATUS_OPERASIONAL",
            "tier_color": "YELLOW",
            "meter_type": "lcd_status_text",
            "span_ratio": span_ratio,
            "reason": f"Layar LCD menampilkan teks status operasional ({ones_count}/{num_tokens} stroke vertikal semu). Stand kWh tidak aktif di layar."
        }

    # KASUS KUNING (Jeda Renggang Abnormal):
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
