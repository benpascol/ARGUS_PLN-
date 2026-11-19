"""
=============================================================================
PROJECT ARGUS: BARCODE & QR SCANNER ENGINE
PT PLN (Persero) UP3 Mojokerto
Lead Engineer: Benedictus Pascal
=============================================================================
Ekstraksi otomatis barcode IDPEL (Nomor Pelanggan 11-12 digit)
menggunakan OpenCV Barcode/QR Detector dengan CLAHE preprocessing.
=============================================================================
"""

import re
import cv2
import numpy as np
from typing import Optional, Dict, Any


class BarcodeEngine:
    def __init__(self):
        self.barcode_detector = None
        self.qr_detector = None
        try:
            self.barcode_detector = cv2.barcode_BarcodeDetector()
        except Exception:
            pass
        try:
            self.qr_detector = cv2.QRCodeDetector()
        except Exception:
            pass

    def scan_idpel(self, image: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Memindai barcode IDPEL 11-12 digit pada citra meteran.
        Menggunakan pra-pemrosesan CLAHE multi-skala.
        """
        if image is None or image.size == 0:
            return None

        # 1. Coba pada citra grayscale langsung
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        res = self._detect_raw(gray)
        if res:
            return res

        # 2. Coba dengan CLAHE enhancement
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        gray_clahe = clahe.apply(gray)
        res = self._detect_raw(gray_clahe)
        if res:
            return res

        # 3. Coba dengan thresholding Otsu
        _, otsu = cv2.threshold(gray_clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        res = self._detect_raw(otsu)
        if res:
            return res

        return None

    def _detect_raw(self, gray_img: np.ndarray) -> Optional[Dict[str, Any]]:
        # A. Coba Barcode Detector
        if self.barcode_detector is not None:
            try:
                retval, decoded_info, decoded_type, points = self.barcode_detector.detectAndDecode(gray_img)
                if retval and decoded_info:
                    for text in decoded_info:
                        if text:
                            m = re.search(r"\b(5145\d{7,8}|\d{11,12})\b", str(text))
                            if m:
                                return {"idpel": m.group(0), "raw": text, "type": "BARCODE"}
            except Exception:
                pass

        # B. Coba QR Detector
        if self.qr_detector is not None:
            try:
                text, points, _ = self.qr_detector.detectAndDecode(gray_img)
                if text:
                    m = re.search(r"\b(5145\d{7,8}|\d{11,12})\b", str(text))
                    if m:
                        return {"idpel": m.group(0), "raw": text, "type": "QR"}
            except Exception:
                pass

        return None
