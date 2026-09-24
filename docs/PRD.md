# Product Requirements Document (PRD) — ScamShield

**Document Version:** 1.0  
**Project:** ScamShield  
**Academic Context:** B.Sc.-IT(Hons.) Semester 5 — Cyber Security in Mobile, Cloud and IoT  
**Authors:** Jaivin Vachhani (`2405101200043`), Yash Jadhav (`2405101200015`), Tirth Bariya (`2405101200050`)  
**Status:** Approved & Complete  

---

## 1. Executive Summary

With the explosive growth of UPI, mobile banking, and digital commerce in India, cyber criminals have pivoted from complex network intrusions to deceptive social engineering attacks targeting everyday citizens. Fraudulent SMS messages (smishing), deceptive URLs, malicious QR codes (quishing), and UPI payment collect-request scams account for millions of rupees in losses annually.

**ScamShield** is an offline, privacy-first cybersecurity tool built to empower digital consumers to inspect suspicious text messages, payment links, and QR codes before interacting with them. By operating 100% locally on the user's device, ScamShield preserves absolute privacy while delivering actionable, plain-language risk evaluations in both English and Hindi.

---

## 2. Problem Statement

1. **Smishing Epidemic**: Attackers exploit fear and greed using fake alerts about blocked SBI/HDFC accounts, electricity bill disconnections, lottery winnings, and tax penalties.
2. **Deceptive URLs & Typosquatting**: Phishing sites employ visual lookalikes (e.g., `paytrn.com`, `sbi-kyc-update.xyz`) to deceive users into surrendering NetBanking credentials and card numbers.
3. **Quishing & UPI Reverse-Charge Scams**: Fraudsters send QR codes claiming "Scan this QR to receive your cashback or prize", exploiting the common misconception that scanning a QR code can credit money to a bank account.
4. **Cloud Privacy Dilemma**: Existing cloud security checkers require users to upload confidential messages and links to third-party servers, creating data privacy and compliance risks.
5. **Language Barrier**: Most cybersecurity tools operate exclusively in technical English, leaving non-English speakers vulnerable.

---

## 3. Product Vision & Goals

- **Zero-Network Privacy**: Guarantee that zero bytes of user data leave the host device.
- **Explainable Cybersecurity**: Rather than just displaying a binary "Blocked" warning, ScamShield educates the user on *why* the message is dangerous and *what* specific action should be taken.
- **Bilingual Inclusivity**: First-class support for English and Hindi (Devanagari script), both in the web interface and in downloadable PDF forensic reports.
- **Sub-Second Performance**: Instant deterministic threat heuristics without dependencies on heavy cloud-based AI inference models.

---

## 4. User Personas

### Persona 1: Suresh (58, Retired Government Employee)
- **Context**: Uses WhatsApp and Google Pay for daily transactions. Receives frequent SMS alerts regarding "Electricity bill unpaid — power will be disconnected at 9:30 PM".
- **Pain Point**: Finds it difficult to distinguish official bank communications from urgent scams. Afraid of clicking links.
- **Need**: A simple tool where he can paste the message in Hindi, receive an instant clear verdict, and understand what to do.

### Persona 2: Priya (20, College Student)
- **Context**: Active online shopper and user of digital wallets (Paytm, PhonePe).
- **Pain Point**: Frequently receives Telegram/WhatsApp messages promising "Part-time job: earn ₹5,000/day by liking YouTube videos" or "Free iPhone reward".
- **Need**: Fast link check and ability to download a PDF report to warn friends and family.

### Persona 3: Ramesh (42, Local Kirana Store Owner)
- **Context**: Displays UPI QR codes at his checkout counter.
- **Pain Point**: Customers sometimes show QR codes or payment confirmation screens attempting refund scams or asking him to scan a QR code to receive a payment.
- **Need**: Fast verification of QR codes and clear confirmation that scanning never receives money.

---

## 5. Functional Requirements

### FR-1: Multi-Modal Input Ingestion
- **FR-1.1**: The system shall provide a tabbed interface supporting three input modes:
  1. Plain Text Message (SMS / WhatsApp) with live character counter (max 10,000 chars).
  2. Direct Web Link (URL).
  3. QR Code Image (via drag-and-drop, file selector, or live webcam video stream).
- **FR-1.2**: Supported image formats: JPEG, PNG, WebP, GIF, BMP (maximum file size 5 MB).
- **FR-1.3**: The system shall offer 15 pre-configured sample inputs (safe and scam examples across English, Hindi, and Hinglish) for quick testing.

### FR-2: Threat Detection & Classification
- **FR-2.1**: The system shall evaluate inputs against **10 distinct threat categories**:
  1. Urgency / Panic Induction
  2. Financial Demands & Fees
  3. KYC / Account Suspension
  4. Prize / Lottery / Cashback
  5. Fake Refunds
  6. Legal Threats & Law Enforcement Impersonation
  7. Sensitive Personal Info Harvest (OTP, CVV, PIN, Aadhaar)
  8. Deceptive / Shortened Links
  9. Malicious URL Structure (IP hosts, `@` auth bypass, suspicious TLDs)
  10. Brand Lookalikes & Typosquatting (Levenshtein distance ≤ 2)
- **FR-2.2**: The system shall detect transliterated Hinglish keywords (e.g., `turant`, `inaam`, `police case`, `blok`).
- **FR-2.3**: The system shall parse UPI strings (`upi://pay`), extract `pa` (VPA), `pn` (Name), `am` (Amount), and `tn` (Note), and flag any prefilled transaction requests.

### FR-3: Scoring & Verdict Generation
- **FR-3.1**: Risk score shall range from **0 to 100** computed via category weight ceilings.
- **FR-3.2**: Verdict thresholds:
  - `0 – 29`: **Looks Safe** (Green)
  - `30 – 59`: **Looks Suspicious** (Amber)
  - `60 – 100`: **This is Dangerous** (Red)
- **FR-3.3**: The verdict display shall include an animated circular SVG score gauge and contextual icon.

### FR-4: Word-Level Highlighting & Visual Feedback
- **FR-4.1**: For message inputs, the system shall highlight detected keywords and phrases using color-coded badges corresponding to the category legend.
- **FR-4.2**: Overlapping match spans shall be normalized cleanly without corrupting the surrounding text.

### FR-5: Educational "Learn Why" Module
- **FR-5.1**: For every red flag generated, the system shall provide a direct link to an educational card on the `/learn` page.
- **FR-5.2**: Each card must contain three standardized sections:
  1. *What this is* (plain-language definition)
  2. *Why scammers use it* (psychological / technical mechanism)
  3. *What to do now* (immediate defensive action)
- **FR-5.2**: The Learn page shall support real-time search filtering and deep-link URL hash navigation (e.g., `/learn#kyc`).

### FR-6: Bilingual Localization (i18n)
- **FR-6.1**: Full user interface localization between English (`en`) and Hindi (`hi`).
- **FR-6.2**: The system shall maintain 100% key parity between English and Hindi dictionaries (105 UI keys and 24 educational flag cards).
- **FR-6.3**: User language selection shall persist across sessions in `localStorage`.

### FR-7: Bilingual PDF Forensic Report Export
- **FR-7.1**: The system shall generate downloadable PDF reports on demand (`POST /api/export/pdf`).
- **FR-7.2**: Hindi reports must employ `uharfbuzz` text shaping with the bundled `NotoSansDevanagari` font to guarantee correct complex conjunct and matra rendering.

### FR-8: Local Scan History & Privacy Preservation
- **FR-8.1**: Every completed scan shall be logged to a local SQLite database (`scamshield.db`).
- **FR-8.2**: To preserve privacy, preview text must be truncated to a maximum of 60 characters.
- **FR-8.3**: Users must be able to filter history by verdict, input type, or date.
- **FR-8.4**: Users must have the ability to delete individual scans or clear their entire history.

---

## 6. Non-Functional Requirements (NFR)

| ID | Category | Requirement Specification |
|---|---|---|
| **NFR-1** | **Privacy** | 100% of threat evaluation occurs in-memory. Zero network sockets opened to external hosts. |
| **NFR-2** | **Performance** | API response time for text analysis under 50ms; QR image analysis under 150ms. |
| **NFR-3** | **Security** | 100% parameterized SQLite statements (`?`) to prevent SQL injection attacks. Target URLs are never fetched over HTTP/HTTPS. |
| **NFR-4** | **Usability** | Modern dark glassmorphism interface adhering to responsive design standards (mobile, tablet, desktop). |
| **NFR-5** | **Reliability** | Comprehensive test suite covering at least 160 automated test cases with 100% passing status. |

---

## 7. Success Criteria & Verification Matrix

| Milestone | Target | Verification Method | Status |
|---|---|---|:---:|
| Core Detection Accuracy | ≥ 95% on 30 benchmark cases | `pytest tests/test_analyzer.py` | ✅ Passed (30/30) |
| SQL Injection Resilience | Zero vulnerability | `pytest tests/test_history.py` | ✅ Passed |
| Bilingual Key Parity | 100% parity (en vs hi) | `pytest tests/test_i18n_pdf.py` | ✅ Passed (105/105) |
| Devanagari PDF Shaping | Valid PDF without glyph error | `pytest tests/test_i18n_pdf.py` | ✅ Passed |
| Frontend Route Integrity | 200 OK across all pages | `pytest tests/test_frontend.py` | ✅ Passed |
| Full Automated Suite | ≥ 160 tests passing | `pytest tests/ -v` | ✅ 169 Passed |
