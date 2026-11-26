"""Tests for Country-Aware Dynamic KPIs in the Central Observatory."""

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

def test_survey_country_signals_structure():
    path = ROOT / "data/processed/survey_country_signals.json"
    assert path.exists(), "survey_country_signals.json must exist"

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "_BENCHMARK" in data, "Must contain _BENCHMARK"
    bench = data["_BENCHMARK"]
    assert bench["rural_outage_pct"] == 82.5
    assert bench["personal_data_pct"] == 39.3
    assert bench["offline_pct"] == 31.7
    assert bench["donor_risk_pct"] == 85.0
    assert bench["teachers_n"] == 600

    focus_isos = ["KEN", "RWA", "TZA", "GHA", "NGA", "ZMB", "MUS"]
    for iso in focus_isos:
        assert iso in data, f"{iso} must be present in survey_country_signals.json"
        entry = data[iso]
        assert entry["teachers_n"] > 0
        assert entry["rural_n"] > 0
        assert entry["rural_outage_pct"] is not None
        assert 0 <= entry["rural_outage_pct"] <= 100
        assert entry["personal_data_pct"] is not None
        assert 0 <= entry["personal_data_pct"] <= 100
        assert entry["providers_n"] > 0
        assert entry["experts_n"] > 0

def test_index_html_country_aware_integration():
    index_path = ROOT / "index.html"
    assert index_path.exists()
    html = index_path.read_text(encoding="utf-8")

    assert "id=\"discrepancy-active-country-badge\"" in html
    assert "function updateSurveyDiscrepancyCards(" in html
    assert "updateSurveyDiscrepancyCards(iso)" in html
    assert "updateSurveyDiscrepancyCards(_activeIso || 'KEN')" in html
    assert "const SURVEY_COUNTRY_SIGNALS = {" in html
