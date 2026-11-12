"""
=============================================================================
PROJECT ARGUS: LOCAL REST API SERVER (CLEAN ARCHITECTURE ENTRYPOINT)
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Inisialisasi server FastAPI ramping:
1. Lifespan event (memuat model AI ke GPU VRAM sekali saat startup).
2. Konfigurasi CORS & StaticFiles.
3. Registrasi modular router (views, audit, excel).
=============================================================================
"""

import io
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Pastikan root ARGUS masuk ke sys.path sebelum mengimpor modul src
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Fix Windows console UTF-8 encoding tanpa menutup stream
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.dependencies import DASHBOARD_DIR, set_pipeline
from src.vision_ai.pipeline import ArgusVisionPipeline
from src.api.routes import audit, excel, views


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("🚀 MEMULAI ARGUS LOCAL REST API SERVER (MODULAR ARCHITECTURE)...")
    print("=" * 60)
    pipeline = ArgusVisionPipeline()
    set_pipeline(pipeline)
    print("✅ ArgusVisionPipeline Siap Menerima Permintaan di http://127.0.0.1:8000")
    print("📄 Dokumentasi Interaktif (Swagger UI): http://127.0.0.1:8000/docs")
    print("=" * 60)
    yield
    print("🛑 Mematikan Server ARGUS...")


app = FastAPI(
    title="⚡ Project ARGUS - Local Vision API Engine",
    description="Engine Inferensi Lokal untuk Audit Pembacaan KWH Meter PT PLN (Persero) UP3 Mojokerto. 100% Offline & Pure Local.",
    version="1.0.0",
    lifespan=lifespan
)

# Konfigurasi CORS (Izinkan Web Extension & Portal ACM PLN)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Folder Statis Dashboard
if (DASHBOARD_DIR / "static").is_dir():
    app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR / "static")), name="static")

# Registrasi Router Modular
app.include_router(views.router)
app.include_router(audit.router)
app.include_router(excel.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
