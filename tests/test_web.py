from __future__ import annotations

import re

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _payload() -> dict[str, str]:
    return {
        "client_name": "Ava Smith",
        "chronological_age_years": "39",
        "sex": "male",
        "sbp_mmHg": "122",
        "dbp_mmHg": "79",
        "pwv_m_per_s": "",
        "height_cm": "178",
        "weight_kg": "80",
        "bmi": "",
        "waist_cm": "91",
        "smoking_status": "never",
        "alcohol_use": "light",
        "drug_use": "none",
        "caffeine_use": "low",
        "sleep_hours": "7.2",
        "sleep_quality": "good",
        "sleep_consistency": "regular",
    }


def test_get_index() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Client Name" in response.text
    assert "ⓘ" in response.text
    assert "/static/js/form.js" in response.text
    disclaimer = "Educational guidance only. These results are not a diagnosis or treatment plan. Discuss personal decisions with a qualified healthcare professional."
    assert response.text.count(disclaimer) == 1


def test_calculate_and_artifacts_routes() -> None:
    response = client.post("/calculate", data=_payload())
    assert response.status_code == 200
    assert "Biological Age" in response.text
    assert "Age Delta" in response.text

    disclaimer = "Educational guidance only. These results are not a diagnosis or treatment plan. Discuss personal decisions with a qualified healthcare professional."
    assert response.text.count(disclaimer) == 1

    match = re.search(r'data-run-id="([^"]+)"', response.text)
    assert match is not None
    run_id = match.group(1)

    report_response = client.get(f"/runs/{run_id}/report")
    assert report_response.status_code == 200
    assert "Prepared for:</strong> Ava Smith" in report_response.text

    download_response = client.get(f"/runs/{run_id}/download/report.html")
    assert download_response.status_code == 200


def test_invalid_sbp_preserves_values_and_renders_field_errors() -> None:
    payload = _payload()
    payload["sbp_mmHg"] = "999"

    response = client.post("/calculate", data=payload)
    assert response.status_code == 200
    assert "Please correct the highlighted fields" in response.text
    assert "vitals.sbp_mmHg must be between 70 and 260" in response.text
    assert 'name="client_name" required value="Ava Smith"' in response.text
    assert 'name="height_cm" value="178"' in response.text
    assert "input-error" in response.text
