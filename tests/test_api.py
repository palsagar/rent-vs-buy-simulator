"""Tests for the HTTP API layer and FastAPI server."""

import pytest

from simulator.api import config_from_dict, config_to_dict
from tests.test_models import make_config


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
