"""
test_frontend.py – Part 6 Frontend UI Verification Tests.

Tests:
  1. HTML page routes return 200 OK and render required markup.
  2. Static assets (CSS, JS) are properly served by Flask.
  3. Key parity check: every `data-i18n` and `data-i18n-placeholder` attribute in
     templates exists in `i18n/en.json`.
  4. Team credits and BCA Sem 5 info exist in about page.
  5. Scanner, History, and Learn page structures match specifications.
"""

import json
import re
from pathlib import Path
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_index_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "ScamShield" in html
    assert "id=\"messageInput\"" in html
    assert "id=\"linkInput\"" in html
    assert "id=\"qrDropzone\"" in html
    assert "id=\"resultSection\"" in html
    assert "id=\"verdictBanner\"" in html
    assert "id=\"scoreGaugeFill\"" in html


def test_history_page_renders(client):
    resp = client.get("/history")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "id=\"historyTable\"" in html
    assert "id=\"filterVerdict\"" in html
    assert "id=\"deleteAllBtn\"" in html
    assert "id=\"statTotal\"" in html


def test_learn_page_renders(client):
    resp = client.get("/learn")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "id=\"learnSearchInput\"" in html
    assert "id=\"learnGrid\"" in html


def test_about_page_renders(client):
    resp = client.get("/about")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Jaivin Vachhani" in html
    assert "2405101200043" in html
    assert "Yash Jadhav" in html
    assert "2405101200015" in html
    assert "Tirth Bariya" in html
    assert "2405101200050" in html
    assert "B.Sc.-IT(Hons.) Sem 5" in html


def test_static_assets_served(client):
    assets = [
        "/static/css/style.css",
        "/static/js/i18n.js",
        "/static/js/main.js",
        "/static/js/scanner.js",
        "/static/js/history.js",
        "/static/js/learn.js",
    ]
    for asset in assets:
        resp = client.get(asset)
        assert resp.status_code == 200, f"Asset failed to load: {asset}"
        assert len(resp.data) > 0, f"Asset is empty: {asset}"


def test_template_i18n_keys_exist_in_en_json():
    """Verify all data-i18n keys used in templates exist in en.json."""
    en_path = Path("i18n/en.json")
    assert en_path.exists()
    with open(en_path, encoding="utf-8") as f:
        en_keys = set(json.load(f).keys())

    template_dir = Path("templates")
    template_files = list(template_dir.glob("*.html"))
    assert len(template_files) >= 5

    data_i18n_regex = re.compile(r'data-i18n=["\']([^"\']+)["\']')
    data_placeholder_regex = re.compile(r'data-i18n-placeholder=["\']([^"\']+)["\']')

    for tf in template_files:
        content = tf.read_text(encoding="utf-8")
        # Check data-i18n
        for match in data_i18n_regex.finditer(content):
            key = match.group(1)
            # Skip jinja template variables if any
            if "{{" in key:
                continue
            assert key in en_keys, f"Template {tf.name} references missing i18n key: {key}"

        # Check data-i18n-placeholder
        for match in data_placeholder_regex.finditer(content):
            key = match.group(1)
            if "{{" in key:
                continue
            assert key in en_keys, f"Template {tf.name} references missing placeholder key: {key}"
