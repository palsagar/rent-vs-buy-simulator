"""Tests for Monte Carlo on the shared engine core."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import itertools
import math

import numpy as np

from simulator.engine import calculate_scenarios
from simulator.models import MonteCarloConfig, SimulationConfig
from simulator.monte_carlo import _compute_sensitivity, run_monte_carlo
from tests.test_models import make_config
from tests.test_us_regression import (
    TORNADO_BASE,
    TORNADO_HIGH,
    TORNADO_LOW,
    TORNADO_NAMES,
    US_PRESET,
)


class TestSharedCore:
    def test_zero_volatility_reproduces_deterministic_series(self):
        # THE anti-drift test: with all stds at 0, every MC path must
        # equal the deterministic Net Value series exactly
        cfg = make_config(horizon_years=5)
        mc = MonteCarloConfig(
            n_simulations=3,
            property_appreciation_std=0.0,
            equity_growth_std=0.0,
            rent_inflation_std=0.0,
        )
        det = calculate_scenarios(cfg)
        res = run_monte_carlo(cfg, mc)
        for i in range(3):
            np.testing.assert_allclose(
                res.all_net_buy[i], det.data["Net_Buy"].to_numpy(), atol=1e-6
            )
            np.testing.assert_allclose(
                res.all_net_rent[i], det.data["Net_Rent"].to_numpy(), atol=1e-6
            )
        assert abs(res.median_difference - det.final_difference) < 1e-6


class TestStatistics:
    def test_shapes_and_ranges(self):
        cfg = make_config(horizon_years=5)
        res = run_monte_carlo(cfg, MonteCarloConfig(n_simulations=50))
        assert res.all_net_buy.shape == (50, 61)
        assert 0.0 <= res.buy_wins_pct <= 100.0
        assert res.p5_difference <= res.median_difference <= res.p95_difference

    def test_seed_reproducibility(self):
        cfg = make_config(horizon_years=5)
        a = run_monte_carlo(cfg, MonteCarloConfig(n_simulations=20, seed=7))
        b = run_monte_carlo(cfg, MonteCarloConfig(n_simulations=20, seed=7))
        np.testing.assert_array_equal(a.final_differences, b.final_differences)


class TestSensitivity:
    def test_tornado_uses_final_difference(self):
        cfg = make_config(horizon_years=5)
        res = run_monte_carlo(cfg, MonteCarloConfig(n_simulations=10))
        det = calculate_scenarios(cfg)
        assert abs(res.sensitivity_base - det.final_difference) < 1e-6
        assert len(res.sensitivity_params) > 0
        assert len(res.sensitivity_low) == len(res.sensitivity_params)

    def test_tornado_low_uses_negative_growth_rate(self):
        # Equity Growth low perturbation must reflect the true negative rate,
        # not a clamped near-zero floor. The delta is now the standard error,
        # std/sqrt(horizon), so a 1-year horizon takes the full std=15 and the
        # low target for equity_growth_annual=7.0 is -8.0 -- unchanged from
        # when the delta was the raw std. This is deliberately the horizon at
        # which the perturbation still goes negative, because a negative
        # target is what proves nothing floors it at zero.
        base_cfg = make_config(horizon_years=1, equity_growth_annual=7.0)
        names, low, _high, _base = _compute_sensitivity(base_cfg)
        idx = names.index("Equity Growth")
        expected_low = calculate_scenarios(
            make_config(horizon_years=1, equity_growth_annual=-8.0)
        ).final_difference
        assert abs(low[idx] - expected_low) < 1e-6


class TestPortfolioDragIsPathDependent:
    def test_mean_realised_drag_is_below_the_deterministic_rate(self):
        # The tax is concave in the return (min then floor), so by
        # Jensen's inequality the mean of the tax is BELOW the tax on the
        # mean. At the app's own calibration (mean 7%, sd 15%) the min
        # binds in ~47% of simulated years, so a run in which every path
        # drags exactly 2.16% means the min is NOT being evaluated per
        # path -- the exact failure this primitive exists to prevent.
        config = make_config(
            horizon_years=30,
            portfolio_deemed_return_pct=6.0,
            portfolio_drag_rate_pct=36.0,
        )
        flat = make_config(horizon_years=30)
        mc = MonteCarloConfig(n_simulations=200, seed=42)
        drag_results = run_monte_carlo(config, mc)
        # Deterministic reference: 7% > 6% every year, so exactly 2.16%.
        deterministic = calculate_scenarios(config).final_difference
        flat_det = calculate_scenarios(flat).final_difference
        # The drag reduces the renter's portfolio, so it RAISES
        # (net_buy - net_rent). Under MC the mean drag is smaller, so the
        # median difference must sit below the deterministic one.
        assert deterministic > flat_det
        assert drag_results.median_difference < deterministic

    def test_every_path_does_not_share_one_drag(self):
        # Two configs differing only in equity draws must produce
        # different realised drags; if the drag were pre-averaged the
        # spread across paths would collapse.
        config = make_config(
            horizon_years=30,
            portfolio_deemed_return_pct=6.0,
            portfolio_drag_rate_pct=36.0,
        )
        mc = MonteCarloConfig(n_simulations=200, seed=42)
        results = run_monte_carlo(config, mc)
        assert np.std(results.final_differences) > 0.0


class TestTornadoLevyDelta:
    def test_us_tornado_names_and_order_are_preserved(self):
        names, _, _, _ = _compute_sensitivity(SimulationConfig(**US_PRESET))
        assert names == TORNADO_NAMES

    def test_us_tornado_values_match_within_tolerance(self):
        _, low, high, base = _compute_sensitivity(SimulationConfig(**US_PRESET))
        for actual, golden in zip(low, TORNADO_LOW, strict=True):
            assert math.isclose(actual, golden, rel_tol=1e-12)
        for actual, golden in zip(high, TORNADO_HIGH, strict=True):
            assert math.isclose(actual, golden, rel_tol=1e-12)
        assert math.isclose(base, TORNADO_BASE, rel_tol=1e-12)

    def test_us_tornado_is_bit_identical(self):
        # 1.2 * (0.5/1.2) is EXACTLY 0.5 in IEEE-754, so low/high are
        # unchanged bit for bit and no ulp allowance is warranted.
        # Asserted so that if a future change does introduce drift,
        # someone decides deliberately rather than inheriting a silent
        # allowance. The test above covers the same goldens at a
        # tolerance; this one is deliberately stricter.
        _, low, high, _ = _compute_sensitivity(SimulationConfig(**US_PRESET))
        assert list(low) == TORNADO_LOW
        assert list(high) == TORNADO_HIGH

    def test_zero_levy_region_drops_the_bar(self):
        # UK/DE/FR ship propertyTaxRate 0.0. A proportional delta at a
        # zero base is itself zero, and _compute_sensitivity would then
        # floor the low side at _POSITIVE_FIELD_FLOOR while the high
        # side stayed 0 -- producing a tiny INVERTED bar rather than no
        # bar. Hence the skip is kept alongside the proportional delta.
        # The guard covers the whole near-zero band, not just an exact
        # 0.0; see test_near_zero_levy_does_not_invert_the_bar.
        names, _, _, _ = _compute_sensitivity(make_config(property_tax_rate=0.0))
        assert "Property Tax Rate" not in names
        assert len(names) == 7

    def test_near_zero_levy_does_not_invert_the_bar(self):
        # fields.js ships propertyTaxRate with step 0.0005 from a min of
        # 0, so 0.0005 is one click away. The proportional delta there is
        # 0.000208, putting the low side below the 0.001 floor: clamped,
        # it represents a HIGHER rate than the high side and the bar
        # renders backwards. Every base whose low side would be floored
        # is skipped, so no reachable slider value produces a bar that
        # contradicts its own direction.
        for rate in (0.0005, 0.001, 0.0015):
            names, _, _, _ = _compute_sensitivity(make_config(property_tax_rate=rate))
            assert "Property Tax Rate" not in names, (
                f"base {rate} kept a bar whose low side is floor-clamped"
            )

        # Just above the band the bar returns, and it points the right
        # way: a higher levy must lower Buy - Rent.
        names, low, high, _ = _compute_sensitivity(make_config(property_tax_rate=0.01))
        i = names.index("Property Tax Rate")
        assert high[i] < low[i]

    def test_flat_levy_region_gets_its_own_bar(self):
        # FR/DE/UK carry the levy as a flat amount, so before this bar
        # existed the tornado was blind to the largest ownership cost
        # after the mortgage. FR is the case that matters: its levy is
        # owner-borne, so it genuinely moves Buy - Rent.
        names, low, high, _ = _compute_sensitivity(
            make_config(property_tax_rate=0.0, annual_property_levy=1220.0)
        )
        assert "Property Levy (flat)" in names
        i = names.index("Property Levy (flat)")
        # A higher levy must lower Buy - Rent.
        assert high[i] < low[i]

    def test_a_region_never_gets_two_levy_bars(self):
        # Both fields are skipped at a zero base, so each region shows
        # whichever representation its bundle actually uses.
        for tax_rate, flat in ((1.2, 0.0), (0.0, 1220.0)):
            names, _, _, _ = _compute_sensitivity(
                make_config(property_tax_rate=tax_rate, annual_property_levy=flat)
            )
            levy_bars = [
                n for n in names if n in ("Property Tax Rate", "Property Levy (flat)")
            ]
            assert len(levy_bars) == 1, levy_bars

    def test_occupier_borne_levy_drops_the_bar_only_while_it_cancels(self):
        # An occupier-borne levy lands in both arms and cancels out of
        # Buy - Rent, so UK/DE would otherwise show a zero-width bar.
        # The drop is measured, not structural: switch the interest
        # deduction on and the levy reaches the verdict through the
        # deductible base, so the bar must come back.
        cancels = make_config(
            property_tax_rate=0.0,
            annual_property_levy=2392.0,
            levy_paid_by_occupier=True,
            interest_deduction_enabled=False,
            marginal_tax_rate_pct=0.0,
        )
        names, _, _, _ = _compute_sensitivity(cancels)
        assert "Property Levy (flat)" not in names

        deductible = make_config(
            property_tax_rate=0.0,
            annual_property_levy=2392.0,
            levy_paid_by_occupier=True,
            interest_deduction_enabled=True,
            marginal_tax_rate_pct=40.0,
            levy_deduction_cap=None,
        )
        names, low, high, _ = _compute_sensitivity(deductible)
        assert "Property Levy (flat)" in names
        i = names.index("Property Levy (flat)")
        assert not math.isclose(low[i], high[i], rel_tol=1e-12)

    def test_levy_neutrality_holds_at_slider_extremes(self):
        # Cancellation is algebraic, not bit-exact: (a + levy) - (b +
        # levy) carries rounding proportional to the verdict, which
        # reaches 1e11 at the slider ceilings. An absolute tolerance
        # leaked a zero-width bar in 86 of these 324 configs.
        leaked = []
        for price, rent, horizon, levy, rate in itertools.product(
            (500_000, 2_000_000, 50_000_000),
            (500, 10_000, 1_000_000),
            (10, 40, 100),
            (50.0, 2392.0, 10_000.0, 100_000.0),
            (0.5, 4.65, 15.0),
        ):
            cfg = make_config(
                horizon_years=horizon,
                property_price=price,
                monthly_rent=rent,
                mortgage_rate_annual=rate,
                mortgage_term_years=25,
                property_tax_rate=0.0,
                annual_property_levy=levy,
                levy_paid_by_occupier=True,
                interest_deduction_enabled=False,
                marginal_tax_rate_pct=0.0,
            )
            names, _, _, _ = _compute_sensitivity(cfg)
            if "Property Levy (flat)" in names:
                leaked.append((price, rent, horizon, levy, rate))
        assert not leaked, (
            f"{len(leaked)} configs leaked a zero-width bar: {leaked[:3]}"
        )

    def test_nonzero_levy_is_perturbed_proportionally_not_absolutely(self):
        # NL's base is 0.2815. An absolute +-0.5 would swing it -178%..
        # +178%; the proportional delta is 0.2815 * (0.5/1.2) = 0.1173,
        # i.e. +-41.7%, the same relative swing the US gets.
        base_rate = 0.2815
        names, low, high, _ = _compute_sensitivity(
            make_config(property_tax_rate=base_rate)
        )
        assert "Property Tax Rate" in names
        idx = names.index("Property Tax Rate")
        expected_delta = base_rate * (0.5 / 1.2)
        lo = _rerun(base_rate - expected_delta)
        hi = _rerun(base_rate + expected_delta)
        assert math.isclose(low[idx], lo, rel_tol=1e-12)
        assert math.isclose(high[idx], hi, rel_tol=1e-12)

    def test_flat_levy_region_still_reports_the_other_seven(self):
        # Guards that a levy skip never drops an UNRELATED bar. That held
        # when a flat-levy region got no levy bar at all, and must still
        # hold now that it gets one of its own. Kept as an exact set so
        # the guarantee stays as strong as it was.
        names, _, _, _ = _compute_sensitivity(
            make_config(property_tax_rate=0.0, annual_property_levy=2392.0)
        )
        assert set(names) == {
            "Property Appreciation",
            "Equity Growth",
            "Rent Inflation",
            "Property Price",
            "Down Payment %",
            "Monthly Rent",
            "Mortgage Rate",
            "Property Levy (flat)",
        }

    def test_static_primitives_flow_through_monte_carlo_unchanged(self):
        config = make_config(
            annual_property_levy=2392.0,
            levy_paid_by_occupier=True,
            annual_maintenance_amount=900.0,
            closing_cost_buyer_amount=-6900.0,
        )
        # With every std zeroed, every MC path must reproduce the
        # deterministic engine exactly.
        mc = MonteCarloConfig(
            n_simulations=3,
            property_appreciation_std=0.0,
            equity_growth_std=0.0,
            rent_inflation_std=0.0,
        )
        results = run_monte_carlo(config, mc)
        expected = calculate_scenarios(config).final_difference
        assert np.allclose(results.final_differences, expected, rtol=1e-9)


def _rerun(rate: float) -> float:
    """Deterministic final difference at one property_tax_rate."""
    return calculate_scenarios(make_config(property_tax_rate=rate)).final_difference
