"""
=============================================================================
PROJECT ARGUS: CELENGAN FEEDBACK AI & INCREMENTAL LEARNING ROUTES
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Menyediakan endpoint manajemen Celengan Feedback AI (Target 1.000 kasus):
1. GET  /api/feedback/status            : Jumlah tabungan aktif & daftar rilis ZIP
2. POST /api/feedback/sync              : Simpan/hapus entri koreksi & catatan AI secara persisten
3. POST /api/feedback/package-now       : Kemas paksa tabungan menjadi ZIP (opsional)
4. GET  /api/feedback/download/{fname}  : Unduh berkas paket ZIP rilis tim IT
=============================================================================
"""

import sys
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

# Pastikan root direktori proyek ARGUS masuk ke sys.path
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.feedback_vault import (
    RELEASES_DIR,
    force_package_release,
    get_vault_status,
    sync_feedback_items,
)

router = APIRouter(prefix="/api/feedback", tags=["Incremental Feedback Vault"])


class FeedbackItemPayload(BaseModel):
    idpel: str = ""
    nama: str = ""
    tarif_daya: str = ""
    filename: str
    stan_lapangan: str = ""
    orig_argus: str = "-"
    corrected_argus: str = "-"
    orig_status: str = "PENDING"
    corrected_status: str = "PENDING"
    ai_notes: str = ""
    blur_score: float = 0.0
    glare_ratio: float = 0.0
    counter_box: Optional[List[int]] = None
    crop_shape: Optional[List[int]] = None
    digits_detail: Optional[List[Dict[str, Any]]] = None
    image_base64: Optional[str] = None


class FeedbackSyncRequest(BaseModel):
    upsert: List[FeedbackItemPayload] = []
    remove_keys: List[str] = []


@router.get("/status")
async def feedback_status():
    """Mengembalikan jumlah tabungan aktif di disk celengan & daftar paket rilis."""
    status = await asyncio.to_thread(get_vault_status)
    return JSONResponse(content=status)


@router.post("/sync")
async def feedback_sync(payload: FeedbackSyncRequest):
    """Menyimpan koreksi & catatan model AI ke celengan persisten (otomatis terkemas jika >= 1000)."""
    upsert_dicts = [item.model_dump() for item in payload.upsert]
    result = await asyncio.to_thread(
        sync_feedback_items,
        upsert_items=upsert_dicts,
        remove_keys=payload.remove_keys,
    )
    if result.get("milestone_triggered"):
        print(
            f"🎁 [CELENGAN AI] Target 1.000 kasus tercapai! Paket rilis siap: {result.get('release_zip_name')}",
            flush=True,
        )
    return JSONResponse(content=result)


@router.post("/package-now")
async def feedback_package_now():
    """Mengemas tabungan celengan saat ini menjadi berkas ZIP lebih awal."""
    result = await asyncio.to_thread(force_package_release)
    return JSONResponse(content=result)


@router.get("/download/{filename}")
async def feedback_download(filename: str):
    """Mengunduh berkas ZIP rilis Celengan Feedback AI secara aman."""
    safe_name = Path(filename).name
    target = (RELEASES_DIR / safe_name).resolve()
    if not str(target).startswith(str(RELEASES_DIR.resolve())) or not target.is_file():
        raise HTTPException(status_code=404, detail="Berkas paket feedback AI tidak ditemukan.")
    return FileResponse(str(target), filename=safe_name, media_type="application/zip")
