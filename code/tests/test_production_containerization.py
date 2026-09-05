from __future__ import annotations

import os
import re
from fastapi.testclient import TestClient
import pytest

from lexis_ops.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_dockerfile_multi_stage_structure():
    """Verifies Dockerfile exists and defines multi-stage build on Python 3.12-slim and Node 22-alpine."""
    dockerfile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dockerfile")
    assert os.path.exists(dockerfile_path), "Dockerfile must exist at repository root"

    with open(dockerfile_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Base image runtimes
    assert "FROM node:22-alpine" in content, "Must use Node 22-alpine LTS"
    assert "FROM python:3.12-slim" in content, "Must use Python 3.12-slim LTS"

    # Multi-stage targets
    assert "AS frontend-builder" in content
    assert "AS console" in content
    assert "AS python-base" in content
    assert "AS worker" in content
    assert "AS test-runner" in content

    # Health check directive
    assert "HEALTHCHECK" in content
    assert "/health/ready" in content


def test_docker_compose_structure():
    """Verifies docker-compose.yml defines all required services and networks."""
    compose_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docker-compose.yml")
    assert os.path.exists(compose_path), "docker-compose.yml must exist at repository root"

    with open(compose_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Core required enterprise services
    required_services = ["postgres:", "temporal:", "temporal-ui:", "worker:", "console:"]
    for svc in required_services:
        assert svc in content, f"docker-compose.yml must define service {svc}"

    # Verify ports and dependencies
    assert "7233:7233" in content, "Temporal gRPC port 7233 must be exposed"
    assert "8000:8000" in content, "Python worker health API port 8000 must be exposed"
    assert "3000:3000" in content, "Next.js console port 3000 must be exposed"
    assert "postgres_data:" in content, "PostgreSQL data volume must be declared"


def test_requirements_and_pyproject_python312_pinning():
    """Verifies requirements.txt and pyproject.toml pin Python 3.12 LTS and Pydantic V2."""
    root_dir = os.path.dirname(os.path.dirname(__file__))
    req_path = os.path.join(root_dir, "requirements.txt")
    pyproject_path = os.path.join(root_dir, "pyproject.toml")

    assert os.path.exists(req_path), "requirements.txt must exist"
    assert os.path.exists(pyproject_path), "pyproject.toml must exist"

    with open(req_path, "r", encoding="utf-8") as f:
        req_content = f.read()

    with open(pyproject_path, "r", encoding="utf-8") as f:
        pyproject_content = f.read()

    # Check Pydantic V2 pinning
    assert "pydantic>=2." in req_content
    assert "pydantic>=2." in pyproject_content

    # Check Python 3.12 LTS specification
    assert ">=3.12" in pyproject_content

    # Check key enterprise libraries
    for lib in ["ortools", "temporalio", "langchain-google-genai", "docling", "fastapi"]:
        assert lib in req_content, f"requirements.txt missing {lib}"


def test_health_scheduler_endpoint(client: TestClient):
    """Verifies /health/scheduler executes OR-Tools CP-SAT constraint problem and returns healthy."""
    response = client.get("/health/scheduler")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["subsystem"] == "ortools_cpsat_scheduler"
    assert isinstance(data["latency_ms"], (int, float))
    assert data["scheduled_slot"]["courtroom"] == "CR-101"


def test_health_ledger_endpoint(client: TestClient):
    """Verifies /health/ledger computes deterministic SHA-256 hash and validates ledger integrity."""
    response = client.get("/health/ledger")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["subsystem"] == "cryptographic_audit_ledger"
    assert data["chain_verified"] is True
    assert len(data["current_hash"]) == 64


def test_health_gemini_endpoint(client: TestClient):
    """Verifies /health/gemini evaluates Gemini API configuration readiness."""
    response = client.get("/health/gemini")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["subsystem"] == "gemini_api_gateway"
    assert data["model"] == "gemini-2.5-flash"


def test_health_ready_aggregate_endpoint(client: TestClient):
    """Verifies /health/ready reports aggregate readiness of all court administration subsystems."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "lexis-ops-court-administration"
    assert data["runtime"] == "Python 3.12 LTS"
    assert "subsystems" in data
    assert data["subsystems"]["scheduler"]["status"] == "healthy"
    assert data["subsystems"]["audit_ledger"]["status"] == "healthy"
    assert data["subsystems"]["gemini_gateway"]["status"] == "healthy"


def test_health_liveness_endpoints(client: TestClient):
    """Verifies /health and /healthz basic liveness probes."""
    for path in ["/health", "/healthz"]:
        res = client.get(path)
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"


def test_caption_layout_descriptor_clean_vs_unstructured_pro_se():
    """Verifies CaptionLayoutDescriptor encapsulates layout detection and calibrated confidence scoring."""
    from lexis_ops.schemas.state import CaptionLayoutDescriptor, FilingPartyType

    clean_text = (
        "IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT\n"
        "CASE NO: 2026-CV-001234\n"
        "ACME CORP v. BETA LLC\n"
        "MOTION TO DISMISS\n"
        "/s/ Jane Attorney, Esq."
    )
    clean_desc = CaptionLayoutDescriptor.from_raw_text(clean_text)
    assert clean_desc.case_number == "2026-CV-001234"
    assert clean_desc.has_formal_caption is True
    assert clean_desc.is_pro_se is False
    assert clean_desc.confidence_score >= 0.98

    messy_text = (
        "Dear Clerk of Court:\n"
        "I am writing pro se because I cannot pay the court fees and landlord wants to evict.\n"
        "/s/ Carlos Gomez"
    )
    messy_desc = CaptionLayoutDescriptor.from_raw_text(messy_text)
    assert messy_desc.case_number is None
    assert messy_desc.is_pro_se is True
    assert messy_desc.is_informal_or_handwritten is True
    assert messy_desc.confidence_score < 0.70
    assert messy_desc.confidence_score == 0.64

