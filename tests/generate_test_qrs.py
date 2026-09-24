"""
Generate test QR images for Part 3 verification.
Run once: python tests/generate_test_qrs.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import qrcode
from PIL import Image

OUT = Path(__file__).parent / "qr_samples"
OUT.mkdir(exist_ok=True)

cases = [
    ("normal_url.png",     "https://www.google.com"),
    ("upi_scam.png",       "upi://pay?pa=scammer123@ybl&pn=FakeRefund&am=500&tn=cashback refund claim"),
    ("shortener.png",      "https://bit.ly/scam123"),
    ("lookalike_sbi.png",  "https://sbi-kyc-login.xyz/verify?session=abc"),
]

for filename, data in cases:
    img = qrcode.make(data)
    img.save(str(OUT / filename))
    print(f"Generated: {filename} -> {data}")

print("Done. QR images saved to tests/qr_samples/")
