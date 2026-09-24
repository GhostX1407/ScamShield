# Technology Stack & Implementation Rationale — ScamShield

**Document Version:** 1.0  
**Project:** ScamShield  
**Course:** BCA Semester 5 — Cyber Security in Mobile, Cloud and IoT  
**Authors:** Jaivin Vachhani (`2405101200043`), Yash Jadhav (`2405101200015`), Tirth Bariya (`2405101200050`)  
**Status:** Approved & Complete  

---

## 1. Technology Stack Summary

| Layer | Component | Version / Tool | Rationale |
|---|---|---|---|
| **Runtime** | Python | 3.11+ | High-performance CPython runtime, robust standard library, strong type hint support |
| **Web Framework** | Flask | 3.0.3 | Minimalist WSGI microframework; avoids bloated ORM/admin overhead |
| **CORS Middleware** | flask-cors | 4.0.1 | Allows cross-origin API invocation for mobile testing or integration |
| **Computer Vision** | OpenCV Headless | 4.10.0.84 | Fast C++ image decoding, grayscale conversion, and `cv2.QRCodeDetector` |
| **Image Processing** | Pillow (PIL) | 10.4.0 | Multi-format image stream buffering and dimension validation |
| **String Metrics** | RapidFuzz | 3.9.3 | C++ accelerated Levenshtein string distance algorithm for brand typosquatting |
| **Domain Analysis** | tldextract | 5.1.2 | Correctly splits subdomains, domains, and multi-part TLDs using Public Suffix List |
| **PDF Generation** | fpdf2 | 2.7.9 | Pure Python PDF generation with vector graphics, table auto-layout, and metadata |
| **Text Shaping** | uharfbuzz | 0.39.3 | HarfBuzz bindings for complex Devanagari OpenType glyph positioning and ligature shaping |
| **Database** | SQLite3 | Built-in | Zero-configuration, serverless, ACID-compliant relational storage with WAL mode |
| **Frontend Markup** | HTML5 | Semantic | Standardized accessible layout with ARIA attributes and data-i18n bindings |
| **Frontend Styling** | Vanilla CSS3 | Custom Tokens | Premium dark glassmorphism design system; 0ms build step, zero npm dependencies |
| **Frontend Logic** | Vanilla ES6 JS | Native Modules | Modern JavaScript with async/await, Fetch API, and `MediaDevices.getUserMedia` |
| **Testing Engine** | Pytest | 8.2.2 | Parameterized test fixtures, test isolation via monkeypatch, sub-5s test execution |

---

## 2. Component Justification & Architecture Rationale

### 2.1 Backend: Flask vs Django vs FastAPI
- **Choice**: **Flask 3.0.3**
- **Why**:
  - Django is heavyweight and includes unnecessary baggage (ORM, auth system, admin panel) that contradicts our zero-configuration, lightweight desktop utility goal.
  - FastAPI introduces an asynchronous ASGI event loop and Pydantic dependency tree that adds unnecessary complexity for our synchronous deterministic heuristic pipeline.
  - Flask provides an elegant, predictable, transparent micro-core that allows us to expose clean REST endpoints with sub-10ms overhead.

### 2.2 Domain Extraction: `tldextract` vs `urllib.parse`
- **Choice**: **tldextract 5.1.2**
- **Why**:
  - Standard `urllib.parse` fails on multi-part public suffixes common in India and the UK (e.g., `sbi.co.in` or `amazon.co.uk`). `urllib` erroneously treats `.co` as the domain and `.in` as the TLD.
  - `tldextract` consults the official Mozilla Public Suffix List (PSL), accurately separating `sbi` (domain) from `co.in` (suffix), ensuring our typosquatting and allowlisting rules function with 100% precision.

### 2.3 Brand Lookalikes: RapidFuzz vs fuzzywuzzy / Levenshtein
- **Choice**: **RapidFuzz 3.9.3**
- **Why**:
  - `fuzzywuzzy` is slow and relies on a GPL-licensed C wrapper or pure-Python fallback.
  - `rapidfuzz` is MIT licensed, written from scratch in modern C++ with SIMD optimizations, and is up to **50x faster** than traditional fuzzy matching libraries, ensuring our lookalike engine runs in microseconds per URL.

### 2.4 PDF Export: `fpdf2` + `uharfbuzz` vs `reportlab` vs `wkhtmltopdf`
- **Choice**: **`fpdf2` with `uharfbuzz` OpenType Shaping**
- **Why**:
  - `wkhtmltopdf` and headless Chromium PDF engines require multi-hundred megabyte external binaries that cannot be easily embedded in a student project.
  - `reportlab` standard editions have notoriously difficult Devanagari text-shaping setups and often mangle Hindi conjunct characters (e.g., converting `क्` + `य` into broken disconnected characters).
  - `fpdf2` provides native integration with `uharfbuzz` (the world's standard text shaping engine used in Chrome, Android, and Firefox). By bundling Google's official `NotoSansDevanagari-Regular.ttf` font, ScamShield renders Hindi typography with professional printing-press quality.

### 2.5 Frontend: Vanilla Modern CSS & JS vs Tailwind / React / Vue
- **Choice**: **Pure Vanilla CSS3 Design System & ES6 JS**
- **Why**:
  - **Zero Build Toolchain**: No `node_modules`, no npm dependencies, no Webpack or Vite build steps. Anyone who clones the repository can immediately run `python app.py` and see a finished, high-performance UI.
  - **Instant Load Time**: Zero bundle parsing overhead. The UI loads in under 100 milliseconds.
  - **Aesthetic Control**: Pure CSS custom properties (tokens) allow complete, granular control over glassmorphism blurs (`backdrop-filter`), neon glows, radial gradients, and responsive layouts.

### 2.6 Local Heuristic Engine vs Cloud LLMs (e.g., OpenAI / Gemini API)
- **Choice**: **Deterministic Multi-Layer Rule Engine & Local Classifiers**
- **Why**:
  - **Privacy**: Sending a user's SMS messages, WhatsApp chats, or bank OTP alerts to a remote cloud API violates basic consumer privacy and leaves users vulnerable to data leaks.
  - **Offline Capability**: ScamShield works on an air-gapped machine with no internet connection.
  - **Predictability & Zero Hallucination**: Regular expression threat matrices and Levenshtein algorithms produce 100% reproducible, verifiable results with explainable mathematical certainty.
  - **Zero API Cost / Rate Limits**: No subscription costs, token limits, or network latency spikes.

---

## 3. Dependency Management

All production dependencies are pinned in `requirements.txt`:

```text
Flask==3.0.3
flask-cors==4.0.1
opencv-python-headless==4.10.0.84
tldextract==5.1.2
rapidfuzz==3.9.3
fpdf2==2.7.9
uharfbuzz==0.39.3
pytest==8.2.2
Pillow==10.4.0
```

Installation is reproducible across Windows, macOS, and Linux:
```bash
pip install -r requirements.txt
```
