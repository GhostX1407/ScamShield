"""
analyzer.py – Orchestrator: detects input type, routes to the right rules,
              combines results into a single verdict JSON.

Input type detection order:
  1. image bytes  → QR decode → recurse with decoded string
  2. text starting with "upi://" → UPI path
  3. text that looks like a bare URL → URL path
  4. anything else → message path (also extracts embedded links)
"""

import re
from urllib.parse import urlparse

from core.message_rules import analyse_message
from core.url_rules import analyse_url
from core.lookalike import analyse_lookalike
from core.upi_parser import parse_upi
from core.qr_reader import decode_qr_from_bytes, QRDecodeError
from core.scoring import calculate_score, get_verdict, FLAG_WEIGHTS, FLAG_CATEGORIES

# Regex to find URLs embedded inside a message
_URL_RE = re.compile(
    r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
    re.IGNORECASE,
)

# Simple heuristic: does this text look like a standalone URL?
_BARE_URL_RE = re.compile(
    r"^(https?://|www\.)[^\s]+$",
    re.IGNORECASE,
)


def _is_url(text: str) -> bool:
    text = text.strip()
    return bool(_BARE_URL_RE.match(text))


def _extract_urls(text: str) -> list[str]:
    return _URL_RE.findall(text)


def _analyse_single_url(url: str) -> list[dict]:
    """Run URL rules + lookalike on one URL, merge results."""
    flags = analyse_url(url)
    flags += analyse_lookalike(url)
    # Deduplicate by id
    seen = set()
    deduped = []
    for f in flags:
        if f["id"] not in seen:
            seen.add(f["id"])
            deduped.append(f)
    return deduped


def _merge_flags(flag_lists: list[list[dict]]) -> list[dict]:
    """Merge multiple flag lists, deduplicating by id and merging spans."""
    merged: dict[str, dict] = {}
    for flags in flag_lists:
        for f in flags:
            if f["id"] not in merged:
                merged[f["id"]] = dict(f)
            else:
                merged[f["id"]]["spans"].extend(f.get("spans", []))
    return list(merged.values())


# ── Main public API ────────────────────────────────────────────────────────

def analyse_text(text: str) -> dict:
    """
    Analyse a text input (message, URL, or UPI string).
    Returns the full result dict.
    """
    text = text.strip()
    if not text:
        return _empty_result("message")

    # ── UPI path ───────────────────────────────────────────────────────────
    if text.lower().startswith("upi://"):
        return _analyse_upi(text)

    # ── Bare URL path ──────────────────────────────────────────────────────
    if _is_url(text):
        return _analyse_url_input(text)

    # ── Message path (default) ─────────────────────────────────────────────
    return _analyse_message_input(text)


def analyse_image(image_bytes: bytes) -> dict:
    """
    Decode a QR code from image bytes and analyse its content.
    Returns a full result dict (input_type="qr").
    """
    try:
        decoded = decode_qr_from_bytes(image_bytes)
    except QRDecodeError as e:
        return {
            "error": str(e),
            "input_type": "qr",
            "verdict": None,
            "score": 0,
            "flags": [],
            "highlighted_spans": [],
            "extracted_links": [],
            "upi_details": None,
            "language": "en",
        }

    # Recurse with decoded string but tag input_type as "qr"
    result = analyse_text(decoded)
    result["input_type"] = "qr"
    result["decoded_text"] = decoded
    return result


# ── Private helpers ────────────────────────────────────────────────────────

def _analyse_upi(uri: str) -> dict:
    upi_data = parse_upi(uri)
    all_flags = list(upi_data["flags"])

    # Also run URL rules on the payee address domain if it looks like a URL
    pa = upi_data.get("payee_address", "")
    if "@" in pa:
        domain_part = pa.split("@")[-1]
        all_flags += _analyse_single_url("https://" + domain_part)

    score   = calculate_score(all_flags)
    verdict = get_verdict(score)

    return {
        "input_type":        "upi",
        "verdict":           verdict,
        "score":             score,
        "flags":             _serialise_flags(all_flags),
        "highlighted_spans": [],
        "extracted_links":   [uri],
        "upi_details":       {
            "payee_address": upi_data["payee_address"],
            "payee_name":    upi_data["payee_name"],
            "amount":        upi_data["amount"],
            "note":          upi_data["note"],
            "warnings":      upi_data["warnings"],
        },
        "language": "en",
    }


def _analyse_url_input(url: str) -> dict:
    flags = _analyse_single_url(url)
    score   = calculate_score(flags)
    verdict = get_verdict(score)

    return {
        "input_type":        "link",
        "verdict":           verdict,
        "score":             score,
        "flags":             _serialise_flags(flags),
        "highlighted_spans": [],
        "extracted_links":   [url],
        "upi_details":       None,
        "language":          "en",
    }


def _analyse_message_input(text: str) -> dict:
    msg_result = analyse_message(text)
    language   = msg_result["language"]
    msg_flags  = msg_result["flags"]

    # Extract any embedded URLs and analyse each
    extracted_links = _extract_urls(text)
    url_flag_lists  = [_analyse_single_url(u) for u in extracted_links]

    all_flags = _merge_flags([msg_flags] + url_flag_lists)
    score     = calculate_score(all_flags)
    verdict   = get_verdict(score)

    # Collect highlighted spans from message flags
    highlighted_spans = []
    for f in msg_flags:
        for span in f.get("spans", []):
            highlighted_spans.append({
                "start":    span[0],
                "end":      span[1],
                "category": f["category"],
                "flag_id":  f["id"],
            })

    return {
        "input_type":        "message",
        "verdict":           verdict,
        "score":             score,
        "flags":             _serialise_flags(all_flags),
        "highlighted_spans": highlighted_spans,
        "extracted_links":   extracted_links,
        "upi_details":       None,
        "language":          language,
    }


def _serialise_flags(flags: list[dict]) -> list[dict]:
    """Return a clean, JSON-serialisable list of flags."""
    out = []
    for f in flags:
        out.append({
            "id":       f["id"],
            "weight":   FLAG_WEIGHTS.get(f["id"], f.get("weight", 0)),
            "category": FLAG_CATEGORIES.get(f["id"], f.get("category", "")),
            "detail":   f.get("detail", ""),
        })
    return out


def _empty_result(input_type: str) -> dict:
    return {
        "input_type":        input_type,
        "verdict":           "Safe",
        "score":             0,
        "flags":             [],
        "highlighted_spans": [],
        "extracted_links":   [],
        "upi_details":       None,
        "language":          "en",
    }
