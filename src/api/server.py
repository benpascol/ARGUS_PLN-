import io
import sys
import time
import base64
from contextlib import asynccontextmanager
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Fix Windows console UTF-8 encoding
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Pastikan root ARGUS masuk ke sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.vision_ai.pipeline import ArgusVisionPipeline

# Global Pipeline Instance (dimuat sekali ke VRAM GPU saat startup)
pipeline: Optional[ArgusVisionPipeline] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    print("=" * 60)
    print("🚀 MEMULAI ARGUS LOCAL REST API SERVER...")
    print("=" * 60)
    pipeline = ArgusVisionPipeline()
    print("✅ ArgusVisionPipeline Siap Menerima Permintaan di http://127.0.0.1:8000")
    print("📄 Dokumentasi Interaktif (Swagger UI): http://127.0.0.1:8000/docs")
    print("=" * 60)
    yield
    print("🛑 Mematikan Server ARGUS...")

# Inisialisasi Aplikasi FastAPI
app = FastAPI(
    title="⚡ Project ARGUS - Local Vision API Engine",
    description="Engine Inferensi Lokal untuk Audit Pembacaan KWH Meter PT PLN (Persero) UP3 Mojokerto. 100% Offline & Pure Local.",
    version="1.0.0",
    lifespan=lifespan
)

# Konfigurasi CORS (Izinkan Web Extension & Portal ACM PLN mengakses localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sanitize_for_json(data: Any) -> Any:
    """Mengonversi tipe data NumPy/Torch menjadi tipe native Python agar aman diserialisasi JSON."""
    if isinstance(data, dict):
        return {k: sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        return [sanitize_for_json(v) for v in data]
    elif isinstance(data, (np.floating, float)):
        return round(float(data), 4)
    elif isinstance(data, (np.integer, int)):
        return int(data)
    elif isinstance(data, np.ndarray):
        return data.tolist()
    return data

class Base64PredictRequest(BaseModel):
    image_base64: str
    filename: Optional[str] = "image_upload.jpg"

def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    """Mengonversi raw bytes ke numpy array OpenCV."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Citra korup atau format tidak didukung.")
    return img

def decode_base64_string(b64_str: str) -> np.ndarray:
    """Mengonversi data URI atau Base64 mentah ke numpy array OpenCV."""
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    image_bytes = base64.b64decode(b64_str)
    return decode_image_bytes(image_bytes)

@app.get("/")
def root():
    """Health check & status engine."""
    return {
        "app": "Project ARGUS AI Vision Engine",
        "unit": "PT PLN (Persero) UP3 Mojokerto",
        "status": "ONLINE",
        "mode": "100% Pure Local & Offline",
        "version": "1.0.0"
    }

@app.post("/predict")
async def predict_file(file: UploadFile = File(...)):
    """
    Endpoint Unggah Berkas Citra (Multipart/Form-Data).
    Digunakan untuk pengujian lewat Swagger UI atau script pengunggah file.
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline AI belum selesai dimuat.")

    try:
        content = await file.read()
        img = decode_image_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal membaca berkas citra: {str(e)}")

    t0 = time.time()
    result = pipeline.predict_image(img)
    latency_ms = round((time.time() - t0) * 1000, 2)
    result["image_name"] = file.filename
    result["latency_ms"] = latency_ms

    return JSONResponse(content=sanitize_for_json(result))

@app.post("/predict-base64")
async def predict_base64(payload: Base64PredictRequest):
    """
    Endpoint Base64 JSON.
    Sangat ramah untuk Userscript Tampermonkey di Google Chrome (GM_xmlhttpRequest).
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline AI belum selesai dimuat.")

    try:
        img = decode_base64_string(payload.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal mendecode Base64: {str(e)}")

    t0 = time.time()
    result = pipeline.predict_image(img)
    latency_ms = round((time.time() - t0) * 1000, 2)
    result["image_name"] = payload.filename
    result["latency_ms"] = latency_ms

    return JSONResponse(content=sanitize_for_json(result))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
