#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
PROJECT ARGUS: DIGIT OCR DETECTOR FINE-TUNING ENGINE (MODEL V4 UPGRADE)
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Pascol
=============================================================================
Skrip otomatis untuk melakukan transfer learning / fine-tuning pada model
YOLOv8 digit detector menggunakan base weights (digit_ocr_detector.pt)
dan dataset kasus anomali lapangan terbaru (argus_audit_v1).
=============================================================================
"""

import sys
import io
import os
import shutil
import random
import argparse
from pathlib import Path

# Fix Windows console UTF-8 encoding
if __name__ == "__main__" and sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import torch
from ultralytics import YOLO


def prepare_dataset_split(dataset_dir: Path, val_ratio: float = 0.15, seed: int = 42):
    """
    Memastikan dataset memiliki partisi train dan valid.
    Jika folder valid masih kosong, secara otomatis memindahkan sejumlah file
    dari train ke valid sesuai val_ratio.
    """
    train_img_dir = dataset_dir / "train" / "images"
    train_lbl_dir = dataset_dir / "train" / "labels"
    val_img_dir = dataset_dir / "valid" / "images"
    val_lbl_dir = dataset_dir / "valid" / "labels"

    val_img_dir.mkdir(parents=True, exist_ok=True)
    val_lbl_dir.mkdir(parents=True, exist_ok=True)

    existing_val = list(val_img_dir.glob("*.jpg")) + list(val_img_dir.glob("*.png"))
    if len(existing_val) > 0:
        print(f"ℹ️ Folder validasi sudah terisi {len(existing_val)} citra. Melewati proses split.")
        return

    train_images = sorted(list(train_img_dir.glob("*.jpg")) + list(train_img_dir.glob("*.png")))
    total_imgs = len(train_images)
    num_val = max(1, int(total_imgs * val_ratio))

    print(f"🔄 Melakukan auto-split dataset ({total_imgs} total):")
    print(f"   - Train set : {total_imgs - num_val} citra ({(1-val_ratio)*100:.0f}%)")
    print(f"   - Valid set : {num_val} citra ({val_ratio*100:.0f}%)")

    random.seed(seed)
    val_selected = random.sample(train_images, num_val)

    for img_path in val_selected:
        lbl_name = img_path.stem + ".txt"
        lbl_path = train_lbl_dir / lbl_name

        dest_img = val_img_dir / img_path.name
        dest_lbl = val_lbl_dir / lbl_name

        shutil.move(str(img_path), str(dest_img))
        if lbl_path.is_file():
            shutil.move(str(lbl_path), str(dest_lbl))

    print("✅ Partisi Train/Validasi selesai dipersiapkan!\n")


def update_data_yaml(yaml_path: Path, dataset_dir: Path):
    """
    Menyesuaikan data.yaml agar path absolute / relative valid untuk YOLOv8.
    """
    content = f"""path: {dataset_dir.as_posix()}
train: train/images
val: valid/images
test: valid/images

nc: 11
names: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'dots']
"""
    yaml_path.write_text(content, encoding="utf-8")
    print(f"✅ File konfigurasi dataset diperbarui: {yaml_path}")


def run_training(
    base_model_path: Path,
    dataset_yaml: Path,
    output_model_dir: Path,
    version_tag: str = "v5",
    epochs: int = 40,
    batch_size: int = 16,
    imgsz: int = 640
):
    print("=" * 80)
    print(f"⚡ PROJECT ARGUS: FINE-TUNING DIGIT OCR DETECTOR (MODEL {version_tag.upper()})")
    print("   PT PLN (Persero) UP3 Mojokerto | Lead Engineer: Pascol")
    print("=" * 80)
    
    device_name = "cpu"
    if torch.cuda.is_available():
        device_name = f"cuda:0 ({torch.cuda.get_device_name(0)})"
    print(f"💻 Perangkat Komputasi : {device_name}")
    print(f"🧠 Base Model Weights  : {base_model_path.name}")
    print(f"📂 Dataset Config      : {dataset_yaml}")
    print(f"🎯 Total Epochs        : {epochs}")
    print(f"📦 Batch Size          : {batch_size}")
    print(f"📐 Image Resolution    : {imgsz}x{imgsz}")
    print("=" * 80 + "\n")

    if not base_model_path.is_file():
        raise FileNotFoundError(f"Base model tidak ditemukan di: {base_model_path}")

    # Memuat base weights
    print(f"🔄 Memuat base weights dari {base_model_path.name}...")
    model = YOLO(str(base_model_path))

    # Eksekusi fine-tuning
    runs_dir = BASE_DIR / "runs" / "finetune"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_name = f"argus_digit_{version_tag.lower()}"

    print(f"\n🚀 Memulai fine-tuning transfer learning di GPU RTX 4060 (Run: {run_name})...")
    train_results = model.train(
        data=str(dataset_yaml),
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=0 if torch.cuda.is_available() else "cpu",
        project=str(runs_dir),
        name=run_name,
        exist_ok=True,
        pretrained=True,
        lr0=0.001,          # Learning rate awal rendah untuk fine-tuning
        lrf=0.01,           # Final learning rate
        warmup_epochs=2,    # Warmup singkat
        patience=15,        # Early stopping jika tidak ada peningkatan
        save=True,
        verbose=True
    )

    # Validasi model terbaik yang dihasilkan
    best_weight_src = runs_dir / run_name / "weights" / "best.pt"
    if best_weight_src.is_file():
        output_model_dir.mkdir(parents=True, exist_ok=True)
        target_model_file = output_model_dir / f"digit_ocr_detector_{version_tag.lower()}.pt"
        shutil.copy2(str(best_weight_src), str(target_model_file))
        
        # Juga perbarui digit_ocr_detector.pt sebagai symlink/fallback produksi
        prod_target = output_model_dir / "digit_ocr_detector.pt"
        shutil.copy2(str(best_weight_src), str(prod_target))

        print("\n" + "=" * 80)
        print("🎉 PELATIHAN FINE-TUNING SELESAI DENGAN SUKSES!")
        print("=" * 80)
        print(f"📦 Bobot Terbaik (best.pt) tersimpan di:\n👉 {best_weight_src}")
        print(f"🚀 Model Produksi Resmi {version_tag.upper()} siap dipakai di:\n👉 {target_model_file}")
        print(f"🔄 Model Standar Produksi diperbarui di:\n👉 {prod_target}")
        print("=" * 80)

        # Evaluasi akurasi akhir
        print(f"\n📊 Mengevaluasi performa model {version_tag.upper()} pada data validasi...")
        best_model = YOLO(str(target_model_file))
        val_metrics = best_model.val(data=str(dataset_yaml), imgsz=imgsz, device=0 if torch.cuda.is_available() else "cpu")
        map50 = val_metrics.box.map50
        map5095 = val_metrics.box.map
        print(f"📈 Hasil Validasi mAP@50    : {map50*100:.2f}%")
        print(f"📈 Hasil Validasi mAP@50-95 : {map5095*100:.2f}%\n")
    else:
        print("⚠️ Peringatan: File best.pt tidak ditemukan di folder runs.")


def main():
    parser = argparse.ArgumentParser(description="ARGUS Model Fine-Tuning Runner")
    default_dataset = BASE_DIR / "data" / "datasets" / "argus_audit_v2"
    if not default_dataset.is_dir():
        default_dataset = BASE_DIR / "data" / "datasets" / "argus_audit_v1"

    default_base = BASE_DIR / "models" / "digit_ocr_detector_v4.pt"
    if not default_base.is_file():
        default_base = BASE_DIR / "models" / "digit_ocr_detector.pt"

    parser.add_argument(
        "--dataset-dir",
        type=str,
        default=str(default_dataset),
        help="Direktori dataset Roboflow yang telah diunduh"
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default=str(default_base),
        help="Path model base weights (best.pt / v4 sebelumnya)"
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v5",
        help="Tag versi model baru (default: v5)"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=35,
        help="Jumlah epoch training (default: 35)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=16,
        help="Ukuran batch GPU (default: 16)"
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset_dir)
    yaml_path = dataset_path / "data.yaml"

    if not dataset_path.is_dir():
        print(f"❌ Error: Direktori dataset tidak ditemukan di: {dataset_path}")
        return

    # 1. Otomatisasi Train/Valid split
    prepare_dataset_split(dataset_path, val_ratio=0.15)

    # 2. Sinkronisasi data.yaml
    update_data_yaml(yaml_path, dataset_path)

    # 3. Jalankan fine-tuning
    run_training(
        base_model_path=Path(args.base_model),
        dataset_yaml=yaml_path,
        output_model_dir=BASE_DIR / "models",
        version_tag=args.version,
        epochs=args.epochs,
        batch_size=args.batch
    )


if __name__ == "__main__":
    main()

