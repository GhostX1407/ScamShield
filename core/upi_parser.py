"""
upi_parser.py – Parse and analyse UPI payment URIs.

UPI URI format: upi://pay?pa=<vpa>&pn=<name>&am=<amount>&tn=<note>&...

Key safety rule enforced here:
  You NEVER need to SCAN a QR code to RECEIVE money.
  Scanning a UPI QR always SENDS money from YOUR account.
"""

from urllib.parse import urlparse, parse_qs
from core.scoring import FLAG_WEIGHTS, FLAG_CATEGORIES

# Keywords in the transaction note that signal a scam context
_SCAM_NOTE_KEYWORDS = {
    "refund", "cashback", "prize", "reward", "winning", "lottery",
    "claim", "bonus", "gift", "lucky", "free", "offer",
    "inaam", "jeeta", "cashbeck", "wapas",
}


def _make_flag(flag_id: str, detail: str = "") -> dict:
    return {
        "id":       flag_id,
        "weight":   FLAG_WEIGHTS.get(flag_id, 15),
        "category": FLAG_CATEGORIES.get(flag_id, "upi"),
        "spans":    [],
        "detail":   detail,
    }


def parse_upi(uri: str) -> dict:
    """
    Parse a UPI URI and return structured data + scam flags.

    Returns:
        {
          "payee_address": str,
          "payee_name":    str,
          "amount":        str | None,
          "note":          str | None,
          "flags":         [FLAG, ...],
          "warnings":      [str, ...]   ← plain-language user-facing warnings
        }
    """
    parsed = urlparse(uri)
    params = parse_qs(parsed.query, keep_blank_values=True)

    def first(key: str) -> str:
        vals = params.get(key, [])
        return vals[0].strip() if vals else ""

    payee_address = first("pa")
    payee_name    = first("pn")
    amount        = first("am") or None
    note          = first("tn") or None

    flags:    list[dict] = []
    warnings: list[str]  = []

    # ── Core UPI safety warning (always shown) ─────────────────────────────
    warnings.append(
        "⚠️ Scanning this QR will SEND money from your account. "
        "You never need to scan a QR code to RECEIVE money — "
        "that is always a scam trick."
    )

    # ── Flag: prefilled amount ─────────────────────────────────────────────
    if amount:
        try:
            amt_val = float(amount)
            if amt_val > 0:
                flags.append(_make_flag(
                    "upi_prefilled_amount",
                    f"QR pre-sets payment of ₹{amount} — scammers do this so you pay without noticing."
                ))
                warnings.append(
                    f"This QR has a pre-filled amount of ₹{amount}. "
                    "Scammers pre-fill amounts so you pay without realising."
                )
        except ValueError:
            pass

    # ── Flag: scam keywords in transaction note ────────────────────────────
    if note:
        note_lower = note.lower()
        for kw in _SCAM_NOTE_KEYWORDS:
            if kw in note_lower:
                flags.append(_make_flag(
                    "upi_scam_note",
                    f"Transaction note mentions '{kw}' — a common scam trick."
                ))
                warnings.append(
                    f"The payment note says '{note}'. "
                    "Scammers use words like 'refund', 'cashback' or 'prize' "
                    "to trick you into scanning a payment QR."
                )
                break   # one flag per note is enough

    # ── Flag: payee name and address look unrelated ────────────────────────
    if payee_address and payee_name:
        # Extract the name part before @
        addr_prefix = payee_address.split("@")[0].lower().replace(".", "").replace("-", "")
        name_clean  = payee_name.lower().replace(" ", "").replace(".", "")
        # If none of the first 4 characters match at all, flag it
        if addr_prefix and name_clean:
            common = sum(1 for c in addr_prefix[:4] if c in name_clean)
            if common == 0:
                flags.append(_make_flag(
                    "upi_name_mismatch",
                    f"Payee name '{payee_name}' looks unrelated to address '{payee_address}'."
                ))
                warnings.append(
                    f"The payee name '{payee_name}' does not match "
                    f"the payment address '{payee_address}'. "
                    "This can be a sign of a fake QR."
                )

    return {
        "payee_address": payee_address,
        "payee_name":    payee_name,
        "amount":        amount,
        "note":          note,
        "flags":         flags,
        "warnings":      warnings,
    }
