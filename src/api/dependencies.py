"""
=============================================================================
PROJECT ARGUS: API DEPENDENCIES & LIFECYCLE MANAGEMENT
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Manajemen dependensi global:
1. Singleton Instance ArgusVisionPipeline (VRAM GPU).
2. Deteksi Hardware Komputasi Riil (GPU RTX / CPU).
3. Helper decoding OpenCV / Base64 & sanitasi JSON.
=============================================================================
"""

import sys
from pathlib import Path

# Pastikan root direktori proyek ARGUS masuk ke sys.path
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import cv2
import base64
import numpy as np
from typing import Optional, Any, Dict
from pydantic import BaseModel

from src.vision_ai.pipeline import ArgusVisionPipeline

# Root Paths
DASHBOARD_DIR = BASE_DIR / "web_extension" / "dashboard"

# Global Pipeline Singleton
_pipeline_instance: Optional[ArgusVisionPipeline] = None


def get_pipeline() -> Optional[ArgusVisionPipeline]:
    """Mengembalikan instance pipeline AI yang aktif di VRAM GPU."""
    global _pipeline_instance
    return _pipeline_instance


def set_pipeline(pipeline: ArgusVisionPipeline):
    """Menyetel instance pipeline AI saat startup aplikasi."""
    global _pipeline_instance
    _pipeline_instance = pipeline


def get_hardware_info() -> Dict[str, Any]:
    """Mengembalikan deteksi hardware komputasi riil GPU/CPU."""
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1)
        device_label = f"ENGINE: ARGUS AI V5 ({gpu_name})"
        batch_concurrency = 4
        hardware_type = "GPU"
        hardware_desc = f"{gpu_name} ({vram_gb} GB VRAM)"
    else:
        import platform
        cpu_name = platform.processor() or "CPU Mode"
        device_label = "ENGINE: ARGUS AI V5 (CPU Mode)"
        batch_concurrency = 2
        hardware_type = "CPU"
        hardware_desc = f"CPU Mode ({cpu_name[:30]})"

    return {
        "type": hardware_type,
        "device_name": hardware_desc,
        "engine_label": device_label,
        "concurrency": batch_concurrency
    }


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


class Base64PredictRequest(BaseModel):
    image_base64: str
    filename: Optional[str] = "image_upload.jpg"


def resolve_photo_path(filename: str, idpel: Optional[str] = None) -> Optional[Path]:
    """
    Mencari lokasi fisik file foto meteran secara cerdas melintasi beberapa direktori kandidat:
    1. BASE_DIR / data / input_foto (dan subfolder di dalamnya)
    2. BASE_DIR / Docs / DOkumentasi LBKB (dan subfolder di dalamnya)
    3. Pencarian fuzzy berdasarkan nama file atau IDPEL
    """
    clean_name = Path(filename).name
    candidate_roots = [
        BASE_DIR / "data" / "input_foto",
        BASE_DIR / "Docs" / "DOkumentasi LBKB",
    ]

    for root in candidate_roots:
        if not root.is_dir():
            continue

        # 1. Direct path check
        direct = root / filename
        if direct.is_file():
            return direct.resolve()

        clean_path = root / clean_name
        if clean_path.is_file():
            return clean_path.resolve()

        # 2. Match exact name in subdirectories (1 level deep)
        matched = list(root.glob(f"**/{clean_name}"))
        if matched and matched[0].is_file():
            return matched[0].resolve()

        # 3. Match IDPEL or pattern
        search_terms = []
        if idpel and len(str(idpel)) >= 8:
            search_terms.append(str(idpel))
        if "-" in clean_name:
            parts = clean_name.replace(".jpg", "").replace(".jpeg", "").replace(".png", "").split("-")
            for p in parts:
                if len(p) >= 10 and p.isdigit():
                    search_terms.append(p)

        for term in search_terms:
            m = list(root.glob(f"*{term}*"))
            if not m:
                m = list(root.glob(f"**/*{term}*"))
            if m and m[0].is_file():
                return m[0].resolve()

    return None
