import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
base_dir = Path("ARGUS")
sys.path.insert(0, str(base_dir.resolve()))
from src.vision_ai.pipeline import ArgusVisionPipeline
import cv2

pipeline = ArgusVisionPipeline()

# Test Case 30
p30 = base_dir / "Docs" / "DOkumentasi LBKB" / "202601-514500365477-L.jpg"
res30 = pipeline.predict_image(str(p30))
print("Case 30 detected digits:")
for d in res30.get("digits_detail", []):
    print(" ", d["digit"], "conf=", d["conf"], "x=", (d["x1"], d["x2"]))

# Test Case 75
p75 = base_dir / "Docs" / "DOkumentasi LBKB" / "202601-514500297791-L.jpg"
res75 = pipeline.predict_image(str(p75))
print("\nCase 75 detected digits:")
print("  Status:", res75.get("status"), "Reading:", res75.get("reading"))
for d in res75.get("digits_detail", []):
    print(" ", d["digit"], "conf=", d["conf"], "x=", (d["x1"], d["x2"]))

