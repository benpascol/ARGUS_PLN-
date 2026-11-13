"""
=============================================================================
PROJECT ARGUS: CELENGAN FEEDBACK AI (INCREMENTAL LEARNING VAULT ENGINE)
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Menyimpan dan mengakumulasi kasus koreksi auditor & catatan evaluasi model AI
secara persisten di disk lokal (data/feedback_staging/) lintas sesi, lintas
refresh browser, dan aman dari tombol Reset Tabel.

Ketika tabungan kasus mencapai target kuota (1.000 kasus unik), sistem
otomatis mengemas 1 Paket Rilis ZIP lengkap (Excel Master Feedback + Citra +
AI Pre-Label YOLOv8) ke data/feedback_releases/ lalu mengosongkan celengan.
=============================================================================
"""

import os
import json
import csv
import shutil
import zipfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from src.api.dependencies import BASE_DIR, decode_base64_string, resolve_photo_path

FEEDBACK_TARGET_COUNT = 1000

STAGING_DIR = BASE_DIR / "data" / "feedback_staging"
STAGING_IMAGES_DIR = STAGING_DIR / "images"
STAGING_LABELS_DIR = STAGING_DIR / "labels"
MANIFEST_FILE = STAGING_DIR / "manifest.json"
RELEASES_DIR = BASE_DIR / "data" / "feedback_releases"

_VAULT_LOCK = threading.Lock()


def make_item_key(idpel: str, filename: str) -> str:
    """Membentuk kunci unik deterministik per pelanggan + berkas foto untuk mencegah duplikasi."""
    safe_idpel = "".join(c for c in str(idpel or "NOID") if c.isalnum() or c in ("_", "-"))
    clean_name = Path(filename or "unknown.jpg").name
    safe_name = "".join(c for c in clean_name if c.isalnum() or c in (".", "_", "-"))
    return f"{safe_idpel}__{safe_name}"


def _ensure_dirs():
    STAGING_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_LABELS_DIR.mkdir(parents=True, exist_ok=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)


def _load_manifest_unlocked() -> Dict[str, Dict[str, Any]]:
    _ensure_dirs()
    if not MANIFEST_FILE.is_file():
        return {}
    try:
        data = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_manifest_unlocked(manifest: Dict[str, Dict[str, Any]]):
    _ensure_dirs()
    tmp_file = MANIFEST_FILE.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp_file), str(MANIFEST_FILE))


def _save_item_assets(
    key: str,
    item: Dict[str, Any],
    manifest: Dict[str, Dict[str, Any]],
) -> Dict[str, Optional[str]]:
    """Menyimpan citra bersih & YOLO pre-label (jika koordinat tersedia) ke folder staging."""
    filename = item.get("filename") or "meter.jpg"
    idpel = item.get("idpel") or ""
    ext = Path(filename).suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"

    safe_stem = Path(key).stem
    dest_img_name = f"{safe_stem}{ext}"
    dest_img_path = STAGING_IMAGES_DIR / dest_img_name

    # Prioritaskan berkas fisik lokal jika ada, fallback ke payload Base64 dari browser
    existing_img = manifest.get(key, {}).get("saved_image")
    if not dest_img_path.is_file():
        resolved = resolve_photo_path(filename, idpel=idpel)
        if resolved and resolved.is_file():
            shutil.copy2(str(resolved), str(dest_img_path))
        elif item.get("image_base64"):
            try:
                img = decode_base64_string(item["image_base64"])
                cv2.imwrite(str(dest_img_path), img)
            except Exception:
                pass
        elif existing_img and (STAGING_IMAGES_DIR / existing_img).is_file():
            dest_img_name = existing_img

    saved_img_rel = dest_img_name if dest_img_path.is_file() else None

    # Simpan Pre-Label YOLO (.txt) bila counter_box dan digits_detail tersedia
    dest_lbl_name = f"{safe_stem}.txt"
    dest_lbl_path = STAGING_LABELS_DIR / dest_lbl_name
    counter_box = item.get("counter_box")
    digits_detail = item.get("digits_detail")
    crop_shape = item.get("crop_shape")

    saved_lbl_rel: Optional[str] = manifest.get(key, {}).get("saved_label")
    if (
        dest_img_path.is_file()
        and isinstance(digits_detail, list)
        and len(digits_detail) > 0
        and isinstance(crop_shape, list)
        and len(crop_shape) == 2
        and crop_shape[0] > 0
        and crop_shape[1] > 0
    ):
        # Simpan crop bersih + koordinat pre-label YOLO
        crop_h, crop_w = int(crop_shape[0]), int(crop_shape[1])
        yolo_lines: List[str] = []
        for d in digits_detail:
            d_char = str(d.get("digit", ""))
            if d_char.isdigit():
                cls_id = int(d_char)
            elif d_char in ("dots", "dot", ".", ","):
                cls_id = 10
            else:
                continue

            dx1, dy1 = float(d.get("x1", 0)), float(d.get("y1", 0))
            dx2, dy2 = float(d.get("x2", 0)), float(d.get("y2", 0))
            cen_x = max(0.0, min(1.0, ((dx1 + dx2) / 2.0) / crop_w))
            cen_y = max(0.0, min(1.0, ((dy1 + dy2) / 2.0) / crop_h))
            bw = max(0.0, min(1.0, (dx2 - dx1) / crop_w))
            bh = max(0.0, min(1.0, (dy2 - dy1) / crop_h))
            yolo_lines.append(f"{cls_id} {cen_x:.6f} {cen_y:.6f} {bw:.6f} {bh:.6f}")

        if yolo_lines:
            # Simpan pula versi crop counter bersih untuk training Roboflow jika counter_box valid
            if isinstance(counter_box, list) and len(counter_box) == 4:
                raw_img = cv2.imread(str(dest_img_path))
                if raw_img is not None:
                    cx1, cy1, cx2, cy2 = [int(v) for v in counter_box]
                    h_img, w_img = raw_img.shape[:2]
                    cx1, cy1 = max(0, cx1), max(0, cy1)
                    cx2, cy2 = min(w_img, cx2), min(h_img, cy2)
                    if cy2 > cy1 and cx2 > cx1:
                        crop_file = STAGING_IMAGES_DIR / f"{safe_stem}_crop.jpg"
                        cv2.imwrite(str(crop_file), raw_img[cy1:cy2, cx1:cx2])
            dest_lbl_path.write_text("\n".join(yolo_lines) + "\n", encoding="utf-8")
            saved_lbl_rel = dest_lbl_name

    return {"saved_image": saved_img_rel, "saved_label": saved_lbl_rel}


def _list_releases_unlocked() -> List[Dict[str, Any]]:
    _ensure_dirs()
    releases = []
    for p in sorted(RELEASES_DIR.glob("ARGUS_AI_Feedback_*.zip"), reverse=True):
        stat = p.stat()
        releases.append({
            "filename": p.name,
            "size_kb": round(stat.st_size / 1024.0, 1),
            "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return releases


def _write_feedback_excel(excel_path: Path, entries: List[Dict[str, Any]], batch_no: int):
    """Menyusun buku kerja Excel Master Rekap Feedback AI untuk tim Engineer/IT."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Feedback Model AI"

    header_fill = PatternFill(start_color="005A87", fill_type="solid")
    sub_fill = PatternFill(start_color="E0F2FE", fill_type="solid")
    thin_side = Side(style="thin", color="CBD5E1")
    border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    headers = [
        ("NO", 6),
        ("IDPEL", 16),
        ("NAMA PELANGGAN", 24),
        ("NAMA FILE FOTO", 28),
        ("STAN LAPANGAN", 15),
        ("STAN AI ASLI", 15),
        ("KOREKSI AUDITOR", 16),
        ("VONIS ASLI AI", 18),
        ("VONIS BARU AUDITOR", 18),
        ("CATATAN FEEDBACK MODEL AI", 42),
        ("SKOR BLUR", 12),
        ("SILAU (%)", 12),
        ("STATUS PRE-LABEL YOLO", 20),
        ("WAKTU DICATAT", 20),
    ]

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    title_cell = ws.cell(
        row=1,
        column=1,
        value=f"ARGUS AI V5 — PAKET FEEDBACK INCREMENTAL LEARNING BATCH #{batch_no:02d} ({len(entries)} KASUS)",
    )
    title_cell.fill = header_fill
    title_cell.font = Font(name="Segoe UI", size=12, bold=True, color="FFFFFF")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
    sub_cell = ws.cell(
        row=2,
        column=1,
        value="PT PLN (Persero) UP3 Mojokerto | Lead Engineer: Benedictus Pascal | Siap Kurasi Roboflow & Fine-Tuning",
    )
    sub_cell.fill = sub_fill
    sub_cell.font = Font(name="Segoe UI", size=9.5, italic=True, color="0F172A")
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20

    for col_idx, (col_title, col_width) in enumerate(headers, 1):
        c = ws.cell(row=4, column=col_idx, value=col_title)
        c.fill = PatternFill(start_color="007BB5", fill_type="solid")
        c.font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width
    ws.row_dimensions[4].height = 26

    for idx, entry in enumerate(entries, 1):
        r_idx = 4 + idx
        row_vals = [
            idx,
            entry.get("idpel", ""),
            entry.get("nama", ""),
            entry.get("filename", ""),
            entry.get("stan_lapangan", "-"),
            entry.get("orig_argus", "-"),
            entry.get("corrected_argus", "-"),
            entry.get("orig_status", "-"),
            entry.get("corrected_status", "-"),
            entry.get("ai_notes", "") or "-",
            entry.get("blur_score", 0.0),
            entry.get("glare_ratio", 0.0),
            "TERSEDIA (.txt)" if entry.get("saved_label") else "TANPA BBOX",
            entry.get("updated_at", ""),
        ]
        for c_idx, val in enumerate(row_vals, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Segoe UI", size=9.5, color="0F172A")
            cell.border = border
            horiz = "left" if c_idx in (3, 4, 10) else "center"
            cell.alignment = Alignment(horizontal=horiz, vertical="center", wrap_text=True)

    ws.freeze_panes = "A5"
    wb.save(str(excel_path))


def _package_release_locked(manifest: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Membungkus seluruh data di staging menjadi 1 berkas ZIP rilis dan mereset celengan."""
    if not manifest:
        return None

    _ensure_dirs()
    existing = list(RELEASES_DIR.glob("ARGUS_AI_Feedback_Batch_*.zip"))
    batch_no = len(existing) + 1
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"ARGUS_AI_Feedback_Batch_{batch_no:02d}_{len(manifest)}cases_{stamp}.zip"
    zip_path = RELEASES_DIR / zip_name

    entries = list(manifest.values())
    temp_dir = RELEASES_DIR / f"_tmp_batch_{batch_no:02d}_{stamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        excel_path = temp_dir / f"ARGUS_AI_Feedback_Batch_{batch_no:02d}.xlsx"
        _write_feedback_excel(excel_path, entries, batch_no)

        # Tulis CSV manifest
        csv_path = temp_dir / "feedback_manifest.csv"
        fieldnames = [
            "idpel", "nama", "filename", "stan_lapangan",
            "orig_argus", "corrected_argus", "orig_status", "corrected_status",
            "ai_notes", "blur_score", "glare_ratio", "saved_image", "saved_label", "updated_at",
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for e in entries:
                writer.writerow({k: e.get(k, "") for k in fieldnames})

        # Tulis classes.txt untuk impor Roboflow
        classes_path = temp_dir / "classes.txt"
        classes_path.write_text("\n".join([str(i) for i in range(10)] + ["dots"]) + "\n", encoding="utf-8")

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(excel_path, arcname=excel_path.name)
            zf.write(csv_path, arcname=csv_path.name)
            zf.write(classes_path, arcname="classes.txt")

            for e in entries:
                img_rel = e.get("saved_image")
                if img_rel and (STAGING_IMAGES_DIR / img_rel).is_file():
                    zf.write(STAGING_IMAGES_DIR / img_rel, arcname=f"images/{img_rel}")
                    crop_rel = f"{Path(img_rel).stem}_crop.jpg"
                    if (STAGING_IMAGES_DIR / crop_rel).is_file():
                        zf.write(STAGING_IMAGES_DIR / crop_rel, arcname=f"crops/{crop_rel}")

                lbl_rel = e.get("saved_label")
                if lbl_rel and (STAGING_LABELS_DIR / lbl_rel).is_file():
                    zf.write(STAGING_LABELS_DIR / lbl_rel, arcname=f"labels/{lbl_rel}")

        # Bersihkan staging untuk memulai celengan batch berikutnya
        shutil.rmtree(STAGING_IMAGES_DIR, ignore_errors=True)
        shutil.rmtree(STAGING_LABELS_DIR, ignore_errors=True)
        _ensure_dirs()
        _save_manifest_unlocked({})
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return zip_name


def get_vault_status() -> Dict[str, Any]:
    """Mengembalikan jumlah tabungan celengan aktif, target kuota (1000), dan daftar rilis."""
    with _VAULT_LOCK:
        manifest = _load_manifest_unlocked()
        return {
            "staging_count": len(manifest),
            "target": FEEDBACK_TARGET_COUNT,
            "releases": _list_releases_unlocked(),
            "staging_dir": str(STAGING_DIR),
            "releases_dir": str(RELEASES_DIR),
        }


def sync_feedback_items(
    upsert_items: Optional[List[Dict[str, Any]]] = None,
    remove_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Menyinkronkan perubahan koreksi/catatan AI ke disk celengan staging secara atomik.
    Otomatis menerbitkan paket rilis ZIP apabila jumlah tabungan mencapai target 1.000 kasus.
    """
    upsert_items = upsert_items or []
    remove_keys = remove_keys or []

    with _VAULT_LOCK:
        manifest = _load_manifest_unlocked()

        # Hapus entri yang dikembalikan ke nilai asli AI (un-edited)
        for rk in remove_keys:
            if rk in manifest:
                old = manifest.pop(rk)
                old_img = old.get("saved_image")
                old_lbl = old.get("saved_label")
                if old_img:
                    (STAGING_IMAGES_DIR / old_img).unlink(missing_ok=True)
                    (STAGING_IMAGES_DIR / f"{Path(old_img).stem}_crop.jpg").unlink(missing_ok=True)
                if old_lbl:
                    (STAGING_LABELS_DIR / old_lbl).unlink(missing_ok=True)

        # Tambahkan / perbarui entri koreksi atau catatan AI
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in upsert_items:
            key = make_item_key(item.get("idpel", ""), item.get("filename", ""))
            assets = _save_item_assets(key, item, manifest)
            manifest[key] = {
                "key": key,
                "idpel": str(item.get("idpel", "")),
                "nama": str(item.get("nama", "")),
                "tarif_daya": str(item.get("tarif_daya", "")),
                "filename": str(item.get("filename", "")),
                "stan_lapangan": str(item.get("stan_lapangan", "")),
                "orig_argus": str(item.get("orig_argus", "-")),
                "corrected_argus": str(item.get("corrected_argus", "-")),
                "orig_status": str(item.get("orig_status", "PENDING")),
                "corrected_status": str(item.get("corrected_status", "PENDING")),
                "ai_notes": str(item.get("ai_notes", "")).strip(),
                "blur_score": float(item.get("blur_score") or 0.0),
                "glare_ratio": float(item.get("glare_ratio") or 0.0),
                "saved_image": assets["saved_image"],
                "saved_label": assets["saved_label"],
                "updated_at": now_str,
            }

        _save_manifest_unlocked(manifest)

        milestone_triggered = False
        release_zip_name = None
        if len(manifest) >= FEEDBACK_TARGET_COUNT:
            release_zip_name = _package_release_locked(manifest)
            milestone_triggered = bool(release_zip_name)
            manifest = {}

        return {
            "staging_count": len(manifest),
            "target": FEEDBACK_TARGET_COUNT,
            "milestone_triggered": milestone_triggered,
            "release_zip_name": release_zip_name,
            "releases": _list_releases_unlocked(),
        }


def force_package_release() -> Dict[str, Any]:
    """Memaketkan tabungan saat ini menjadi ZIP lebih awal (khusus kebutuhan Engineer)."""
    with _VAULT_LOCK:
        manifest = _load_manifest_unlocked()
        if not manifest:
            return {
                "packaged": False,
                "message": "Celengan feedback masih kosong (0 kasus).",
                "staging_count": 0,
                "target": FEEDBACK_TARGET_COUNT,
                "releases": _list_releases_unlocked(),
            }
        zip_name = _package_release_locked(manifest)
        return {
            "packaged": bool(zip_name),
            "release_zip_name": zip_name,
            "staging_count": 0,
            "target": FEEDBACK_TARGET_COUNT,
            "releases": _list_releases_unlocked(),
        }
