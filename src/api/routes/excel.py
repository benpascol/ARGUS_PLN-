"""
=============================================================================
PROJECT ARGUS: EXCEL ACMT PARSER & OFFICIAL REPORT EXPORT ROUTES
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Menangani integrasi data tabular:
1. POST /api/parse-acmt-excel  : Parser rekap ACMT / LBKB (.xlsx, .xls, .csv) & Auto-Pairing
2. POST /api/export-audit-excel: Ekspor laporan audit resmi PLN UP3 Mojokerto ber-Hyperlink
=============================================================================
"""

import io
import re
import csv
import sys
import time
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse

# Pastikan root direktori proyek ARGUS masuk ke sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.api.dependencies import BASE_DIR, resolve_photo_path

router = APIRouter(tags=["Excel ACMT & Export"])


class AuditRowItem(BaseModel):
    no: int
    idpel: str
    nama: str
    tarif_daya: str
    kdbaca: Optional[str] = "F"
    stan_lapangan: str
    raw_display: Optional[str] = "-"
    stan_argus: Optional[str] = "-"
    selisih: Optional[str] = "0"
    verdict: str
    diagnosa_detail: Optional[str] = ""
    tier_color: Optional[str] = "GREEN"
    latency_ms: Optional[float] = 0.0
    blur_score: Optional[float] = 0.0
    glare_ratio: Optional[float] = 0.0
    filename: str
    is_edited: Optional[bool] = False
    notes: Optional[str] = ""


class ExportExcelRequest(BaseModel):
    rows: List[AuditRowItem]


@router.post("/api/parse-acmt-excel")
async def parse_acmt_excel_endpoint(file: UploadFile = File(...)):
    """
    Engine Parser Rekap ACMT / LBKB Excel (.xlsx, .xls) & CSV.
    Mengekstrak IDPEL, NAMA, TARIF, DAYA, STAN_BACA / STAN_LAPANGAN,
    dan NAMA FILE untuk mekanisme pemasangan otomatis (auto-pairing).
    """
    filename = file.filename or ""
    lower_fn = filename.lower()
    if not (lower_fn.endswith(".xlsx") or lower_fn.endswith(".xls") or lower_fn.endswith(".csv")):
        raise HTTPException(status_code=400, detail="Format berkas harus .xlsx, .xls, atau .csv.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Berkas kosong.")

    records = []
    detected_cols = {}

    try:
        if lower_fn.endswith(".csv"):
            text_data = content.decode("utf-8", errors="replace")
            sample_chunk = text_data[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample_chunk, delimiters=",;\t|")
                delimiter = dialect.delimiter
            except Exception:
                delimiter = ";" if ";" in sample_chunk else ","

            reader = csv.reader(io.StringIO(text_data), delimiter=delimiter)
            all_rows = list(reader)
        else:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            sheet = wb.active
            all_rows = list(sheet.iter_rows(values_only=True))

        header_row = None
        header_idx = -1

        for idx, row in enumerate(all_rows[:15]):
            if not row or all(v is None or str(v).strip() == "" for v in row):
                continue
            row_str = [str(v).strip().upper() if v is not None else "" for v in row]
            if any("IDPEL" in col or "NOMOR PELANGGAN" in col or "ID_PEL" in col for col in row_str):
                header_row = row_str
                header_idx = idx
                break

        if not header_row:
            raise HTTPException(status_code=400, detail="Header kolom IDPEL / Nomor Pelanggan tidak ditemukan dalam dokumen.")

        def find_col_idx(patterns):
            for p in patterns:
                for i, col in enumerate(header_row):
                    if re.search(p, col, re.IGNORECASE):
                        return i
            return None

        idpel_col = find_col_idx([r"\bIDPEL\b", r"ID.*PEL", r"NO.*PEL"])
        nama_col = find_col_idx([r"\bNAMA\b", r"NAMA.*PEL", r"CUSTOMER"])
        tarif_col = find_col_idx([r"\bTARIF\b", r"\bTARIP\b"])
        daya_col = find_col_idx([r"\bDAYA\b"])
        stan_col = find_col_idx([r"STAN.*BACA", r"STAN.*METER", r"STAN.*LAP", r"\bSTAND\b", r"\bSTAN\b"])
        file_col = find_col_idx([r"NAMA.*FILE", r"\bPHOTO\b", r"\bFOTO\b", r"\bGAMBAR\b"])
        alamat_col = find_col_idx([r"\bALAMAT\b"])

        detected_cols = {
            "idpel": idpel_col,
            "nama": nama_col,
            "tarif": tarif_col,
            "daya": daya_col,
            "stan": stan_col,
            "file": file_col
        }

        for r in all_rows[header_idx + 1:]:
            if not r or all(v is None or str(v).strip() == "" for v in r):
                continue

            raw_idpel = str(r[idpel_col]).strip() if idpel_col is not None and r[idpel_col] is not None else ""
            m_idpel = re.search(r"\d{10,13}", raw_idpel)
            if not m_idpel:
                continue
            idpel = m_idpel.group(0)

            nama = str(r[nama_col]).strip() if nama_col is not None and r[nama_col] is not None else ""
            tarif = str(r[tarif_col]).strip() if tarif_col is not None and r[tarif_col] is not None else ""
            daya = str(r[daya_col]).strip() if daya_col is not None and r[daya_col] is not None else ""
            tarif_daya = f"{tarif} / {daya} VA" if tarif and daya else (tarif or daya or "-")

            stan = ""
            if stan_col is not None and r[stan_col] is not None:
                raw_stan = str(r[stan_col]).strip()
                sm = re.search(r"\d+", raw_stan)
                stan = sm.group(0) if sm else raw_stan

            photo_name = str(r[file_col]).strip() if file_col is not None and r[file_col] is not None else ""
            alamat = str(r[alamat_col]).strip() if alamat_col is not None and r[alamat_col] is not None else ""

            records.append({
                "idpel": idpel,
                "nama": nama,
                "tarif": tarif,
                "daya": daya,
                "tarif_daya": tarif_daya,
                "stan_lapangan": stan,
                "nama_file": photo_name,
                "alamat": alamat
            })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses file Excel: {str(e)}")

    print(f"📁 [ACMT EXCEL] Berkas berhasil diunggah: {filename} ({len(records)} data pelanggan dipasangkan)")

    return JSONResponse(content={
        "status": "success",
        "filename": filename,
        "total_records": len(records),
        "detected_columns": detected_cols,
        "records": records
    })


@router.post("/api/export-audit-excel")
async def export_audit_excel_endpoint(payload: ExportExcelRequest):
    """
    Ekspor Laporan Audit Excel Resmi PLN UP3 Mojokerto ber-Hyperlink
    memanfaatkan langsung engine openpyxl di src.audit_excel.
    """
    from src.audit_excel import export_audit_excel_file

    annotated_dir = BASE_DIR / "data" / "audit_results" / "annotated_samples"

    audit_results = []
    stats = {
        "MATCH": 0, "ROLLING": 0, "TRIAGE": 0, "MISMATCH": 0,
        "GLARE": 0, "BLUR": 0, "FRAUD": 0, "total_latency_ms": 0.0
    }

    for item in payload.rows:
        resolved_photo = resolve_photo_path(item.filename, idpel=item.idpel)
        if resolved_photo and resolved_photo.is_file():
            abs_photo = resolved_photo.resolve()
        else:
            abs_photo = (BASE_DIR / "data" / "input_foto" / item.filename).resolve()

        annotated_file = annotated_dir / f"result_crop_{item.filename}"
        abs_annotated = annotated_file.resolve() if annotated_file.is_file() else None

        diag = item.diagnosa_detail or ""
        if item.is_edited and item.notes:
            diag = f"[KOREKSI AUDITOR: {item.notes}] {diag}".strip()
        elif item.is_edited:
            diag = f"[KOREKSI AUDITOR] {diag}".strip()

        v = (item.verdict or "").upper()
        if "MATCH" in v or "SESUAI" in v:
            stats["MATCH"] += 1
            verdict_clean = "SESUAI_MATCH"
        elif "ROLLING" in v:
            stats["ROLLING"] += 1
            verdict_clean = "ROLLING_DIGIT"
        elif any(k in v for k in ("BUKAN", "NIHIL", "FRAUD")):
            stats["FRAUD"] += 1
            verdict_clean = "TIDAK_TERDETEKSI_KWH"
        elif "DIFF" in v or "BEDA" in v:
            stats["MISMATCH"] += 1
            verdict_clean = "BEDA_STAND"
        elif "BURAM" in v or "BLUR" in v:
            stats["BLUR"] += 1
            verdict_clean = "FOTO_BURAM"
        elif "SILAU" in v or "GLARE" in v:
            stats["GLARE"] += 1
            verdict_clean = "FOTO_SILAU"
        else:
            stats["TRIAGE"] += 1
            verdict_clean = "PERLU_TINJAU_ULANG"

        stats["total_latency_ms"] += (item.latency_ms or 0.0)

        audit_results.append({
            "no": item.no,
            "idpel": item.idpel,
            "nama": item.nama,
            "tarif_daya": item.tarif_daya,
            "kdbaca": item.kdbaca or "F",
            "stan_lapangan": item.stan_lapangan,
            "raw_display": item.raw_display or "-",
            "stan_argus": item.stan_argus or "-",
            "selisih": item.selisih or "0",
            "verdict": verdict_clean,
            "diagnosa_detail": diag or "Audit Mandiri Dashboard V5",
            "tier_color": item.tier_color or "GREEN",
            "latency_ms": item.latency_ms or 0.0,
            "blur_score": item.blur_score or 0.0,
            "glare_ratio": item.glare_ratio or 0.0,
            "filename": item.filename,
            "abs_photo_path": abs_photo,
            "ai_annotated_file": abs_annotated,
            "harvest_crop_file": None
        })

    out_dir = BASE_DIR / "data" / "audit_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_excel = out_dir / f"Audit_LBKB_Result_Dashboard_V5_{int(time.time())}.xlsx"

    export_audit_excel_file(
        output_excel=out_excel,
        audit_results=audit_results,
        total_found=len(audit_results),
        stats=stats,
        total_time_s=1.0,
        annotated_dir=annotated_dir,
        harvest=False
    )

    print(f"📊 [EKSPOR EXCEL] Laporan resmi ber-Hyperlink berhasil dibuat: {out_excel.name} ({len(audit_results)} data)")

    return FileResponse(
        str(out_excel),
        filename="Audit_LBKB_Result_ARGUS_V5_Official.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
