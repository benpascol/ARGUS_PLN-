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
import time
import threading
import webbrowser
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

from src.api.dependencies import DASHBOARD_DIR, set_pipeline, get_hardware_info
from src.vision_ai.pipeline import ArgusVisionPipeline
from src.api.routes import audit, excel, views


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Deteksi hardware komputasi riil
    hw = get_hardware_info()
    dev_name = hw.get("device_name", "GPU / CPU")

    print(f"🔧 [KOMPUTASI] : {dev_name}", flush=True)
    print("🔒 [MODE]      : 100% Pure Local & Offline (Host: 127.0.0.1:8000)", flush=True)
    print("🔄 Memuat Model AI Vision ke Memori GPU...", flush=True)

    pipeline = ArgusVisionPipeline()
    set_pipeline(pipeline)

    print("✅ Model AI Siap Menerima Pemeriksaan Meteran!", flush=True)
    print("\n🌐 Membuka Dashboard Mandiri di browser default Anda...", flush=True)
    print("   URL: http://127.0.0.1:8000/dashboard", flush=True)
    print("-" * 78, flush=True)
    print("💡 PETUNJUK PENGOPERASIAN:", flush=True)
    print("   • Biarkan jendela terminal ini tetap terbuka selama proses audit berlangsung.", flush=True)
    print("   • Untuk mematikan server dengan aman, tekan [Ctrl+C] atau tutup jendela ini.", flush=True)
    print("-" * 78, flush=True)
    print("   Sistem Pengawasan Visual Otomatis LBKB | Lead Engineer: Benedictus Pascal", flush=True)
    print("=" * 78 + "\n", flush=True)

    # Auto-launch browser di thread terpisah
    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open("http://127.0.0.1:8000/dashboard")
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()

    yield
    print("\n🛑 Mematikan Server ARGUS...", flush=True)


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
    # Gunakan log_level warning agar terminal tidak banjir request statis
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
