"""
=============================================================================
PROJECT ARGUS: AI INFERENCE AUDIT ROUTES
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Menyediakan endpoint inferensi visual AI:
1. POST /predict        : Unggah berkas gambar (Multipart/Form-Data)
2. POST /predict-base64 : Payload Base64 JSON (Tampermonkey & Web Dashboard)
=============================================================================
"""

import time
import asyncio
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from src.api.dependencies import (
    get_pipeline,
    sanitize_for_json,
    decode_image_bytes,
    decode_base64_string,
    Base64PredictRequest
)

router = APIRouter(tags=["Audit & AI Inference"])


@router.post("/predict")
async def predict_file(file: UploadFile = File(...)):
    """
    Endpoint Unggah Berkas Citra (Multipart/Form-Data).
    Digunakan untuk pengujian lewat Swagger UI atau script pengunggah file.
    """
    pipeline = get_pipeline()
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline AI belum selesai dimuat ke VRAM GPU.")

    try:
        content = await file.read()
        img = decode_image_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca berkas citra: {str(e)}")

    t0 = time.time()
    result = await asyncio.to_thread(pipeline.predict_image, img)
    latency_ms = round((time.time() - t0) * 1000, 2)
    result["image_name"] = file.filename
    result["latency_ms"] = latency_ms

    return JSONResponse(content=sanitize_for_json(result))


@router.post("/predict-base64")
async def predict_base64(payload: Base64PredictRequest):
    """
    Endpoint Base64 JSON.
    Sangat ramah untuk Userscript Tampermonkey di Google Chrome (GM_xmlhttpRequest)
    dan batch auditor 4x GPU worker pool.
    """
    pipeline = get_pipeline()
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline AI belum selesai dimuat ke VRAM GPU.")

    try:
        img = decode_base64_string(payload.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal mendecode Base64: {str(e)}")

    t0 = time.time()
    result = await asyncio.to_thread(pipeline.predict_image, img)
    latency_ms = round((time.time() - t0) * 1000, 2)
    result["image_name"] = payload.filename
    result["latency_ms"] = latency_ms

    return JSONResponse(content=sanitize_for_json(result))
