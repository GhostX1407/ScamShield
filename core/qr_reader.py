"""
qr_reader.py – Decode a QR code from raw image bytes.

Uses OpenCV's built-in QRCodeDetectorAruco (more robust than the basic detector).
Returns the decoded string, or raises a descriptive exception on failure.
"""

import cv2
import numpy as np


class QRDecodeError(Exception):
    """Raised when no QR code can be decoded from the image."""


def decode_qr_from_bytes(image_bytes: bytes) -> str:
    """
    Decode the first QR code found in image_bytes.

    Args:
        image_bytes: Raw bytes of a JPEG, PNG, or similar image.

    Returns:
        The decoded string content of the QR code.

    Raises:
        QRDecodeError: If the image is invalid or no QR code is detected.
    """
    if not image_bytes:
        raise QRDecodeError("Empty image data received.")

    # Decode bytes to numpy array
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        raise QRDecodeError(
            "That doesn't look like a valid image file. "
            "Please upload a clear JPEG or PNG photo."
        )

    # Try the more robust ArUco-based detector first
    try:
        detector = cv2.QRCodeDetectorAruco()
        data, _, _ = detector.detectAndDecode(img)
        if data:
            return data
    except Exception:
        pass

    # Fall back to the basic QR detector
    detector_basic = cv2.QRCodeDetector()
    data, _, _ = detector_basic.detectAndDecode(img)
    if data:
        return data

    # If image is very small, mention it explicitly
    h, w = img.shape[:2]
    if h < 50 or w < 50:
        raise QRDecodeError(
            "The image is too small to read. Please use a larger, clearer photo."
        )

    raise QRDecodeError(
        "No QR code found in this image. "
        "Make sure the QR code is clearly visible and not blurry or cut off."
    )
