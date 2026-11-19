import os
import sys
import io
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

def train_yolo_digits():
    # Pastikan CUDA tersedia
    import torch
    print("=" * 60)
    print("🚀 ARGUS YOLO DIGIT TRAINING PIPELINE")
    print("=" * 60)
    print(f"PyTorch Version  : {torch.__version__}")
    print(f"CUDA Available   : {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"Device Name      : {torch.cuda.get_device_name(0)}")
        print(f"VRAM Capacity    : {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
    else:
        print("⚠️ PERINGATAN: CUDA tidak terdeteksi, training akan berjalan di CPU!")
    print("=" * 60)

    from ultralytics import YOLO

    # Path konfigurasi dataset
    dataset_yaml = Path(__file__).resolve().parent.parent.parent / "data" / "datasets" / "argus_digits_v3" / "data.yaml"
    if not dataset_yaml.exists():
        raise FileNotFoundError(f"File data.yaml tidak ditemukan di: {dataset_yaml}")

    print(f"📁 Menggunakan dataset: {dataset_yaml}")

    # Menggunakan pretrained YOLOv8s (Small) untuk ekstraksi fitur yang tajam
    base_model_path = Path(__file__).resolve().parent.parent.parent / "models" / "yolov8s.pt"
    model = YOLO(str(base_model_path) if base_model_path.exists() else "yolov8s.pt")

    print("\n🏋️ MEMULAI PELATIHAN MODEL (11 KELAS: 0-9 + DOTS)...")
    print("⚙️ Hyperparameters Disetel Khusus Digit Meteran PLN:")
    print("   - fliplr=0.0 (DILARANG HORIZONTAL FLIP)")
    print("   - flipud=0.0 (DILARANG VERTICAL FLIP)")
    print("   - epochs=100 dengan early stopping patience=20")
    print("   - imgsz=640, batch=16\n")

    results = model.train(
        data=str(dataset_yaml),
        epochs=100,
        patience=20,
        batch=16,
        imgsz=640,
        device=0 if torch.cuda.is_available() else "cpu",
        workers=4,
        project="runs",
        name="argus_digits_v3",
        exist_ok=True,
        # ⚠️ KUNCI SUKSES OCR DIGIT: MATIKAN FLIP APAPUN!
        fliplr=0.0,
        flipud=0.0,
        degrees=5.0,
        shear=2.0,
        perspective=0.0005,
        hsv_h=0.015,
        hsv_s=0.2,
        hsv_v=0.2,
        save=True,
        save_period=10,
        plots=True,
        verbose=True
    )

    best_pt = Path("runs/argus_digits_v3/weights/best.pt")
    target_pt = Path(__file__).resolve().parent.parent.parent / "models" / "digit_ocr_detector.pt"
    backup_pt = Path(__file__).resolve().parent.parent.parent / "models" / "digit_ocr_detector_v2_backup.pt"

    print("\n" + "=" * 60)
    print("🎉 TRAINING SELESAI!")
    print(f"Hasil terbaik tersimpan di: {best_pt}")
    
    if best_pt.exists():
        import shutil
        if target_pt.exists() and not backup_pt.exists():
            shutil.copy2(target_pt, backup_pt)
            print(f"📦 Backup model lama tersimpan di: {backup_pt}")
        shutil.copy2(best_pt, target_pt)
        print(f"🚀 Model v3 berhasil dipasang ke: {target_pt}")
    print("=" * 60)

if __name__ == "__main__":
    train_yolo_digits()
