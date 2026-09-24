"""
ScamShield – Flask application entry point.
Serves the frontend and exposes API routes.
"""

import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

from core.analyzer import analyse_text, analyse_image

app = Flask(__name__)
CORS(app)

# ── File upload limits ─────────────────────────────────────────────────────
MAX_IMAGE_BYTES   = 5 * 1024 * 1024   # 5 MB
ALLOWED_MIMETYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}


# ══════════════════════════════════════════════════════════════════════════
# Page routes
# ══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/history")
def history_page():
    return render_template("history.html")

@app.route("/learn")
def learn_page():
    return render_template("learn.html")

@app.route("/about")
def about_page():
    return render_template("about.html")


# ══════════════════════════════════════════════════════════════════════════
# Health check
# ══════════════════════════════════════════════════════════════════════════

@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "ScamShield", "version": "0.1.0"})


# ══════════════════════════════════════════════════════════════════════════
# Scan API
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/scan/text", methods=["POST"])
def scan_text():
    """
    Scan a text input (message, URL, or UPI string).

    Body: JSON { "text": "..." }
    Returns: analysis result JSON
    """
    body = request.get_json(silent=True)
    if not body or "text" not in body:
        return jsonify({"error": "Missing 'text' field in request body."}), 400

    text = str(body["text"]).strip()
    if not text:
        return jsonify({"error": "Input text cannot be empty."}), 400

    if len(text) > 10_000:
        return jsonify({"error": "Input is too long. Please keep it under 10,000 characters."}), 400

    result = analyse_text(text)

    # Save to history (imported lazily to avoid circular imports)
    from core.history import save_scan
    save_scan(result, preview_text=text)

    return jsonify(result)


@app.route("/api/scan/image", methods=["POST"])
def scan_image():
    """
    Scan a QR code image.

    Body: multipart/form-data with field 'image'
    Returns: analysis result JSON
    """
    if "image" not in request.files:
        return jsonify({"error": "No image file uploaded. Please attach an image."}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    # Validate MIME type
    mimetype = file.mimetype or ""
    if mimetype not in ALLOWED_MIMETYPES:
        return jsonify({
            "error": "Unsupported file type. Please upload a JPEG, PNG, or WebP image."
        }), 415

    # Read and validate size
    image_bytes = file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return jsonify({
            "error": "Image is too large. Please upload a file smaller than 5 MB."
        }), 413

    result = analyse_image(image_bytes)

    # Save to history only if QR was decoded successfully
    if "error" not in result:
        from core.history import save_scan
        decoded = result.get("decoded_text", "")
        save_scan(result, preview_text=decoded)

    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════
# History API  (implemented fully in Part 4)
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/history", methods=["GET"])
def history_list():
    from core.history import list_scans
    verdict  = request.args.get("verdict")
    inp_type = request.args.get("type")
    date     = request.args.get("date")
    scans = list_scans(verdict=verdict, input_type=inp_type, date=date)
    return jsonify(scans)

@app.route("/api/history/<int:scan_id>", methods=["DELETE"])
def history_delete(scan_id: int):
    from core.history import delete_scan
    deleted = delete_scan(scan_id)
    if not deleted:
        return jsonify({"error": "Scan not found."}), 404
    return jsonify({"deleted": scan_id})

@app.route("/api/history", methods=["DELETE"])
def history_delete_all():
    from core.history import delete_all_scans
    count = delete_all_scans()
    return jsonify({"deleted_count": count})

@app.route("/api/history/stats", methods=["GET"])
def history_stats():
    from core.history import get_stats
    return jsonify(get_stats())


# ══════════════════════════════════════════════════════════════════════════
# i18n / Learn / Samples  (implemented fully in Part 5)
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/i18n/<lang>")
def i18n(lang: str):
    import json
    from pathlib import Path
    if lang not in ("en", "hi"):
        return jsonify({"error": "Unsupported language."}), 400
    path = Path("i18n") / f"{lang}.json"
    if not path.exists():
        return jsonify({}), 200
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))

@app.route("/api/learn/<lang>")
def learn_cards(lang: str):
    import json
    from pathlib import Path
    if lang not in ("en", "hi"):
        return jsonify({"error": "Unsupported language."}), 400
    path = Path("i18n") / f"learn_{lang}.json"
    if not path.exists():
        return jsonify({}), 200
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))

@app.route("/api/samples")
def samples():
    import json
    from pathlib import Path
    path = Path("data") / "samples.json"
    if not path.exists():
        return jsonify([]), 200
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))


# ══════════════════════════════════════════════════════════════════════════
# PDF export  (implemented fully in Part 5)
# ══════════════════════════════════════════════════════════════════════════

@app.route("/api/export/pdf", methods=["POST"])
def export_pdf():
    from core.export_pdf import generate_pdf
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Missing request body."}), 400
    lang = body.get("lang", "en")
    result = body.get("result")
    if not result:
        return jsonify({"error": "Missing 'result' field."}), 400

    pdf_bytes = generate_pdf(result, lang=lang)
    from flask import Response
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=scamshield_report.pdf"},
    )


# ══════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=5000)
