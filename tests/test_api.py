import itertools
import json

import pytest
from fastapi.testclient import TestClient

from simulator.api import (
    config_from_dict,
    config_to_dict,
    monte_carlo_payload,
    simulate_payload,
)
from simulator.engine import calculate_scenarios
from simulator.models import MonteCarloConfig
from simulator.regions import get_region, list_regions
from simulator.server import app
from tests.test_models import make_config

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_regions_endpoint() -> None:
    response = client.get("/api/regions")
    assert response.status_code == 200
    regions = response.json()
    assert len(regions) == 5
    assert regions[0]["id"] == "us"


def test_simulate_endpoint_happy_path() -> None:
    response = client.post("/api/simulate", json=config_to_dict(make_config()))
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"]["winner"] in ("buy", "rent")
    assert len(body["series"]["netBuy"]) == 121


def test_simulate_endpoint_validation_error_is_422() -> None:
    payload = {**config_to_dict(make_config()), "downPaymentPct": 3}
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 422
    assert "down_payment_pct" in response.json()["detail"]


def test_simulate_endpoint_unknown_field_is_422() -> None:
    response = client.post("/api/simulate", json={"bogusField": 1})
    assert response.status_code == 422
    assert "Unknown config field" in response.json()["detail"]


def test_monte_carlo_endpoint_happy_path() -> None:
    response = client.post("/api/monte-carlo", json=config_to_dict(make_config()))
    assert response.status_code == 200
    body = response.json()
    assert 0.0 <= body["buyWinsPct"] <= 100.0
    assert body["nSimulations"] == 500


def test_config_roundtrips_through_camel_case() -> None:
    config = make_config(monthly_rent=2100)
    assert config_from_dict(config_to_dict(config)) == config


def test_config_from_dict_applies_dataclass_defaults() -> None:
    config = config_from_dict(
        {
            "horizonYears": 8,
            "propertyPrice": 450000,
            "downPaymentPct": 25,
            "mortgageRateAnnual": 5.9,
            "propertyAppreciationAnnual": 2.5,
            "equityGrowthAnnual": 6.5,
            "monthlyRent": 1900,
        }
    )
    assert config.horizon_years == 8
    assert config.mortgage_term_years == 30  # dataclass default


def test_config_from_dict_rejects_unknown_field() -> None:
    with pytest.raises(ValueError, match="Unknown config field"):
        config_from_dict({"horizonYears": 8, "bogusField": 1})


def test_config_from_dict_propagates_validation() -> None:
    with pytest.raises(ValueError, match="down_payment_pct"):
        config_from_dict({**config_to_dict(make_config()), "downPaymentPct": 3})


def test_simulate_payload_matches_engine_truth() -> None:
    config = make_config()
    payload = simulate_payload(config)
    results = calculate_scenarios(config)

    assert payload["verdict"]["difference"] == results.final_difference
    expected_winner = "buy" if results.final_difference > 0 else "rent"
    assert payload["verdict"]["winner"] == expected_winner
    assert payload["verdict"]["horizonYears"] == config.horizon_years
    assert payload["breakevenYear"] == results.breakeven_year
    assert payload["monthlyMortgagePayment"] == results.monthly_mortgage_payment
    assert payload["monthlyCostBuyYear1"] == results.monthly_cost_buy_year1
    assert payload["monthlyCostRentYear1"] == results.monthly_cost_rent_year1

    series = payload["series"]
    assert len(series["year"]) == config.horizon_years * 12 + 1
    assert series["netBuy"][-1] == results.final_net_buy
    assert series["netRent"][-1] == results.final_net_rent


def test_simulate_payload_outflows_monotonic() -> None:
    series = simulate_payload(make_config())["series"]
    for key in ("outflowBuy", "outflowRent"):
        values = series[key]
        assert all(b >= a for a, b in itertools.pairwise(values))


def test_simulate_payload_is_json_serializable() -> None:
    payload = simulate_payload(make_config())
    assert json.loads(json.dumps(payload)) == payload


def test_monte_carlo_payload_shape_and_determinism() -> None:
    config = make_config()
    mc = MonteCarloConfig(n_simulations=30, seed=7)
    first = monte_carlo_payload(config, mc)
    second = monte_carlo_payload(config, mc)

    assert first == second  # fixed seed → identical payloads
    assert 0.0 <= first["buyWinsPct"] <= 100.0
    assert first["nSimulations"] == 30

    fan = first["differencePercentiles"]
    assert len(fan) == len(first["percentileLevels"])
    assert len(fan[0]) == len(first["yearAxis"]) == config.horizon_years * 12 + 1

    tornado = first["tornado"]
    assert len(tornado["params"]) == len(tornado["low"]) == len(tornado["high"])
    assert isinstance(tornado["base"], float)

    assert json.loads(json.dumps(first)) == first


def test_regions_us_available_others_disabled() -> None:
    regions = {r["id"]: r for r in list_regions()}
    assert set(regions) == {"us", "fr", "de", "nl", "uk"}

    us = regions["us"]
    assert us["available"] is True
    assert us["currencySymbol"] == "$"
    assert us["typical"]["propertyPrice"] == 500000
    assert us["typical"]["monthlyRent"] == 2400
    assert us["taxPrimitives"]["marginalTaxRatePct"] == 24.0
    assert us["taxPrimitives"]["saleCgRegime"] == "exempt_amount"

    for rid in ("fr", "de", "nl", "uk"):
        assert regions[rid]["available"] is False
        assert regions[rid]["typical"] is None
        assert regions[rid]["taxPrimitives"] is None


def test_get_region_unknown_raises_key_error() -> None:
    with pytest.raises(KeyError):
        get_region("xx")
