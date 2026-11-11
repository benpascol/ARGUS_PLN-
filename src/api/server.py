import io
import sys
import time
import base64
from contextlib import asynccontextmanager
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Any
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

@app.get("/simulator", response_class=HTMLResponse)
def get_simulator():
    """Halaman Simulator Portal ACMT PLN untuk Uji Coba Evaluasi & Tampermonkey."""
    sim_path = BASE_DIR / "web_extension" / "simulator.html"
    if not sim_path.is_file():
        raise HTTPException(status_code=404, detail="Berkas simulator.html tidak ditemukan.")
    return HTMLResponse(content=sim_path.read_text(encoding="utf-8"))

# Konfigurasi Aset Statis & Jinja2 Templates (Modular Dashboard)
DASHBOARD_DIR = BASE_DIR / "web_extension" / "dashboard"
if (DASHBOARD_DIR / "static").is_dir():
    app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(DASHBOARD_DIR)) if DASHBOARD_DIR.is_dir() else None

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    """Halaman Standalone Web Dashboard ARGUS (Modular Component Architecture)."""
    if templates and (DASHBOARD_DIR / "index.html").is_file():
        return templates.TemplateResponse(request=request, name="index.html")
    dash_path = BASE_DIR / "web_extension" / "dashboard.html"
    if dash_path.is_file():
        return HTMLResponse(content=dash_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Berkas dashboard tidak ditemukan.")

@app.get("/sample-photo/{filename}")
def get_sample_photo(filename: str):
    """Menyajikan foto sampel meteran asli dari Docs/DOkumentasi LBKB."""
    photo_path = BASE_DIR / "Docs" / "DOkumentasi LBKB" / filename
    if not photo_path.is_file():
        raise HTTPException(status_code=404, detail=f"Foto {filename} tidak ditemukan.")
    return FileResponse(str(photo_path), media_type="image/jpeg")

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
    rows: list[AuditRowItem]

@app.post("/api/export-audit-excel")
async def export_audit_excel_endpoint(payload: ExportExcelRequest):
    """
    Ekspor Laporan Audit Excel Resmi PLN UP3 Mojokerto ber-Hyperlink
    memanfaatkan langsung engine openpyxl di src.audit_excel.
    """
    from src.audit_excel import export_audit_excel_file
    
    photo_dir = BASE_DIR / "Docs" / "DOkumentasi LBKB"
    annotated_dir = BASE_DIR / "data" / "audit_results" / "annotated_samples"
    
    audit_results = []
    stats = {
        "MATCH": 0, "ROLLING": 0, "TRIAGE": 0, "MISMATCH": 0,
        "GLARE": 0, "BLUR": 0, "FRAUD": 0, "total_latency_ms": 0.0
    }
    
    for item in payload.rows:
        photo_path = photo_dir / item.filename
        if not photo_path.is_file():
            matched = list(photo_dir.glob(f"*{item.idpel}*.jpg"))
            abs_photo = matched[0].resolve() if matched else photo_path.resolve()
        else:
            abs_photo = photo_path.resolve()
            
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
    
    return FileResponse(
        str(out_excel),
        filename="Audit_LBKB_Result_ARGUS_V5_Official.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
