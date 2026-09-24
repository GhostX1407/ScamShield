"""
export_pdf.py – Generate a PDF report for a scan result.

Uses fpdf2 with uharfbuzz text shaping so Hindi (Devanagari) renders correctly.
The Noto Sans Devanagari font is bundled at assets/fonts/.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ── Paths ──────────────────────────────────────────────────────────────────
_ROOT       = Path(__file__).parent.parent
_FONT_PATH  = _ROOT / "assets" / "fonts" / "NotoSansDevanagari-Regular.ttf"
_I18N_DIR   = _ROOT / "i18n"
_LEARN_EN   = json.loads((_I18N_DIR / "learn_en.json").read_text(encoding="utf-8"))
_LEARN_HI   = json.loads((_I18N_DIR / "learn_hi.json").read_text(encoding="utf-8"))

# ── Colours ────────────────────────────────────────────────────────────────
_COLOUR = {
    "Safe":        (39,  174,  96),   # green
    "Suspicious":  (230, 126,  34),   # orange
    "Dangerous":   (192,  57,  43),   # red
    "heading":     (44,  62,  80),    # dark navy
    "body":        (52,  73,  94),    # slate
    "muted":       (127, 140, 149),   # grey
    "white":       (255, 255, 255),
    "light_bg":    (245, 246, 250),
}

# ── Label maps (for PDF captions without full i18n load) ──────────────────
_LABELS = {
    "en": {
        "title":        "ScamShield Report",
        "generated":    "Generated on",
        "verdict":      "Verdict",
        "score":        "Risk Score",
        "input_type":   "Input Type",
        "language":     "Language",
        "flags":        "Red Flags Found",
        "no_flags":     "No red flags found.",
        "upi_title":    "UPI Payment Details",
        "payee":        "Payee Address",
        "payee_name":   "Payee Name",
        "amount":       "Amount",
        "note":         "Note",
        "warnings":     "Warnings",
        "learn_title":  "Why These Were Flagged",
        "what":         "What this is",
        "why":          "Why scammers use it",
        "do":           "What to do",
        "footer":       "ScamShield — Nothing you scan is ever sent to the internet.",
        "types": {
            "message": "Message",
            "link":    "Link",
            "qr":      "QR Code",
            "upi":     "UPI QR",
        },
        "langs": {
            "en":       "English",
            "hi":       "Hindi",
            "hinglish": "Hinglish",
        },
    },
    "hi": {
        "title":        "ScamShield रिपोर्ट",
        "generated":    "तैयार किया गया",
        "verdict":      "निर्णय",
        "score":        "जोखिम स्कोर",
        "input_type":   "इनपुट प्रकार",
        "language":     "भाषा",
        "flags":        "मिली चेतावनियाँ",
        "no_flags":     "कोई चेतावनी नहीं मिली।",
        "upi_title":    "UPI भुगतान विवरण",
        "payee":        "प्राप्तकर्ता का पता",
        "payee_name":   "प्राप्तकर्ता का नाम",
        "amount":       "राशि",
        "note":         "नोट",
        "warnings":     "चेतावनियाँ",
        "learn_title":  "इन्हें क्यों चिह्नित किया गया",
        "what":         "यह क्या है",
        "why":          "ठग इसका उपयोग क्यों करते हैं",
        "do":           "अभी क्या करें",
        "footer":       "ScamShield — आप जो भी जाँचते हैं वह इंटरनेट पर नहीं जाता।",
        "types": {
            "message": "संदेश",
            "link":    "लिंक",
            "qr":      "QR कोड",
            "upi":     "UPI QR",
        },
        "langs": {
            "en":       "अंग्रेज़ी",
            "hi":       "हिन्दी",
            "hinglish": "हिंग्लिश",
        },
    },
}


# ── PDF builder ────────────────────────────────────────────────────────────

class _ShieldPDF(FPDF):
    """Custom FPDF subclass with header/footer and Devanagari support."""

    def __init__(self, lang: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.lang    = lang
        self.labels  = _LABELS.get(lang, _LABELS["en"])

        self.set_margins(20, 20, 20)
        self.set_auto_page_break(auto=True, margin=20)

        # Register Noto Sans Devanagari for all text (it covers Latin too)
        self.add_font("Noto", style="",  fname=str(_FONT_PATH))
        self.add_font("Noto", style="B", fname=str(_FONT_PATH))

        # Enable text shaping for complex scripts (Devanagari)
        self.set_text_shaping(True)

        self.add_page()

    def header(self):
        self.set_font("Noto", "B", 10)
        self.set_text_color(*_COLOUR["muted"])
        self.cell(0, 8, self.labels["title"], align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Noto", "", 8)
        self.set_text_color(*_COLOUR["muted"])
        self.cell(0, 6, self.labels["footer"], align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Helpers ────────────────────────────────────────────────────────────

    def section_heading(self, text: str):
        self.ln(4)
        self.set_font("Noto", "B", 11)
        self.set_text_color(*_COLOUR["heading"])
        self.set_fill_color(*_COLOUR["light_bg"])
        self.cell(0, 8, text, fill=True, align="L",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def label_value(self, label: str, value: str):
        self.set_font("Noto", "B", 9)
        self.set_text_color(*_COLOUR["muted"])
        self.cell(50, 6, label + ":", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("Noto", "", 9)
        self.set_text_color(*_COLOUR["body"])
        self.multi_cell(0, 6, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def verdict_banner(self, verdict: str, score: int):
        colour = _COLOUR.get(verdict, _COLOUR["body"])
        self.set_fill_color(*colour)
        self.set_text_color(*_COLOUR["white"])
        self.set_font("Noto", "B", 22)
        self.cell(0, 18, verdict, fill=True, align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Noto", "", 11)
        lbl = self.labels
        score_line = f"{lbl['score']}: {score}/100"
        self.set_fill_color(*[max(0, c - 30) for c in colour])
        self.cell(0, 9, score_line, fill=True, align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*_COLOUR["body"])
        self.ln(4)

    def flag_card(self, flag_id: str, learn_db: dict):
        card = learn_db.get(flag_id)
        if not card:
            return
        lbl = self.labels
        self.set_font("Noto", "B", 10)
        self.set_text_color(*_COLOUR["heading"])
        self.multi_cell(0, 6, f"• {card.get('title', flag_id)}",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        for key, label in [("what", lbl["what"]),
                            ("why",  lbl["why"]),
                            ("do",   lbl["do"])]:
            self.set_font("Noto", "B", 8)
            self.set_text_color(*_COLOUR["muted"])
            self.cell(30, 5, label + ":", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_font("Noto", "", 8)
            self.set_text_color(*_COLOUR["body"])
            self.multi_cell(0, 5, card.get(key, ""),
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)


# ── Public API ─────────────────────────────────────────────────────────────

def generate_pdf(result: dict, lang: str = "en") -> bytes:
    """
    Build a PDF report for a scan result dict.
    Returns the PDF as raw bytes.
    """
    if lang not in ("en", "hi"):
        lang = "en"

    learn_db = _LEARN_HI if lang == "hi" else _LEARN_EN
    lbl      = _LABELS[lang]

    pdf = _ShieldPDF(lang=lang)

    # ── Title block ────────────────────────────────────────────────────────
    pdf.set_font("Noto", "B", 18)
    pdf.set_text_color(*_COLOUR["heading"])
    pdf.cell(0, 12, lbl["title"], align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d  %H:%M UTC")
    pdf.set_font("Noto", "", 9)
    pdf.set_text_color(*_COLOUR["muted"])
    pdf.cell(0, 6, f"{lbl['generated']}: {ts}", align="C",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # ── Verdict banner ─────────────────────────────────────────────────────
    verdict = result.get("verdict", "Safe")
    score   = result.get("score",   0)
    pdf.verdict_banner(verdict, score)

    # ── Meta info ──────────────────────────────────────────────────────────
    pdf.section_heading(lbl["verdict"])
    input_type = result.get("input_type", "message")
    lang_code  = result.get("language",   "en")
    pdf.label_value(lbl["input_type"],
                    lbl["types"].get(input_type, input_type))
    pdf.label_value(lbl["language"],
                    lbl["langs"].get(lang_code, lang_code))

    # ── Flags ──────────────────────────────────────────────────────────────
    flags = result.get("flags", [])
    pdf.section_heading(lbl["flags"])
    if not flags:
        pdf.set_font("Noto", "", 9)
        pdf.set_text_color(*_COLOUR["muted"])
        pdf.cell(0, 6, lbl["no_flags"],
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        for f in flags:
            pdf.label_value(f["id"], f"weight: {f.get('weight', 0)}")

    # ── UPI details ────────────────────────────────────────────────────────
    upi = result.get("upi_details")
    if upi:
        pdf.section_heading(lbl["upi_title"])
        if upi.get("payee_address"):
            pdf.label_value(lbl["payee"],      upi["payee_address"])
        if upi.get("payee_name"):
            pdf.label_value(lbl["payee_name"], upi["payee_name"])
        if upi.get("amount"):
            pdf.label_value(lbl["amount"],     f"Rs. {upi['amount']}")
        if upi.get("note"):
            pdf.label_value(lbl["note"],       upi["note"])
        for w in upi.get("warnings", []):
            pdf.set_font("Noto", "", 8)
            pdf.set_text_color(192, 57, 43)
            pdf.multi_cell(0, 5, w,
                           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(*_COLOUR["body"])

    # ── Learn Why cards ────────────────────────────────────────────────────
    if flags:
        pdf.section_heading(lbl["learn_title"])
        for f in flags:
            pdf.flag_card(f["id"], learn_db)

    return bytes(pdf.output())
