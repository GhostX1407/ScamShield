"""
test_docs.py – Part 7 Documentation Completeness & Verification Tests.

Tests:
  1. README.md exists, has proper structure, installation instructions, and API docs.
  2. docs/PRD.md exists, covers problem statement, functional & non-functional requirements.
  3. docs/ARCHITECTURE.md exists, details subsystem design, data flow, and DB schema.
  4. docs/TECH_STACK.md exists, provides library justifications and comparisons.
  5. Academic context (BCA Sem 5) and team member details are properly documented.
"""

from pathlib import Path


def test_readme_completeness():
    readme = Path("README.md")
    assert readme.exists(), "README.md is missing"
    content = readme.read_text(encoding="utf-8")
    assert len(content) > 1500, "README.md is too short"
    assert "ScamShield" in content
    assert "Installation & Setup" in content
    assert "pip install -r requirements.txt" in content
    assert "REST API Reference" in content
    assert "/api/scan/text" in content
    assert "Jaivin Vachhani" in content
    assert "2405101200043" in content
    assert "Yash Jadhav" in content
    assert "2405101200015" in content
    assert "Tirth Bariya" in content
    assert "2405101200050" in content


def test_prd_completeness():
    prd = Path("docs/PRD.md")
    assert prd.exists(), "docs/PRD.md is missing"
    content = prd.read_text(encoding="utf-8")
    assert len(content) > 1500, "docs/PRD.md is too short"
    assert "Product Requirements Document" in content
    assert "Problem Statement" in content
    assert "User Personas" in content
    assert "Functional Requirements" in content
    assert "Non-Functional Requirements" in content
    assert "FR-1" in content
    assert "FR-2" in content
    assert "FR-3" in content


def test_architecture_completeness():
    arch = Path("docs/ARCHITECTURE.md")
    assert arch.exists(), "docs/ARCHITECTURE.md is missing"
    content = arch.read_text(encoding="utf-8")
    assert len(content) > 1500, "docs/ARCHITECTURE.md is too short"
    assert "System Architecture Document" in content
    assert "Pipeline Data Flow" in content
    assert "Subsystem Specifications" in content
    assert "Database Schema" in content
    assert "Security & Privacy Model" in content
    assert "CREATE TABLE IF NOT EXISTS scans" in content


def test_tech_stack_completeness():
    tech = Path("docs/TECH_STACK.md")
    assert tech.exists(), "docs/TECH_STACK.md is missing"
    content = tech.read_text(encoding="utf-8")
    assert len(content) > 1500, "docs/TECH_STACK.md is too short"
    assert "Technology Stack" in content
    assert "Flask" in content
    assert "OpenCV" in content
    assert "RapidFuzz" in content
    assert "tldextract" in content
    assert "fpdf2" in content
    assert "uharfbuzz" in content
    assert "SQLite3" in content
