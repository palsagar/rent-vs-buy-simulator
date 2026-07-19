# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A FastAPI + static JavaScript web app that compares buying property vs. renting and investing in equities. Users configure financial parameters in a dark GitHub-style UI (the same visual system as the author's WebGPU apps) and see Plotly.js charts comparing two strategies: Buy and Rent & Invest. The simulation engine is Python/NumPy behind a JSON API.

## Commands

```bash
# Run the app
uv run uvicorn simulator.server:app --reload --port 8501
# Open http://localhost:8501

# Type check
uv run ty check src/

# Tests
uv run pytest tests/                        # all tests
uv run pytest tests/test_engine_core.py      # single file
uv run pytest tests/test_engine_core.py::TestClassName::test_name  # single test
uv run pytest --cov --cov-report=term        # with coverage (80% min enforced)

# Lint & format
uv run ruff check src/ tests/         # lint
uv run ruff check --fix src/ tests/   # lint + autofix
uv run ruff format src/ tests/        # format

# Setup
uv venv --seed && uv pip install -e .
```

## Architecture

**Data flow:** `Browser (src/simulator/static/js) → FastAPI (src/simulator/server.py) → api.py → SimulationConfig (models.py) → calculate_scenarios (engine.py) / run_monte_carlo (monte_carlo.py) → JSON → Plotly.js`

- **`src/simulator/server.py`** — FastAPI app + static mount.
- **`src/simulator/api.py`** — camelCase wire codec + payload serialization.
- **`src/simulator/regions.py`** — Region preset bundles as data.
- **`src/simulator/static/`** — Hand-rolled frontend: `index.html`, `css/style.css`, `js/` ES modules, Plotly.js via CDN.
- **`src/simulator/models.py`** — `SimulationConfig` and `SimulationResults` dataclasses. Validation in `__post_init__`.
- **`src/simulator/engine.py`** — Pure calculation engine. `calculate_scenarios(config)` returns `SimulationResults`. All time-series math uses NumPy vectorized arrays (no Python loops). Uses `numpy_financial.pmt()` for mortgage amortization.
- **`src/simulator/monte_carlo.py`** — Stochastic paths over the same `_net_value_series` core, plus the tornado sensitivity (one-at-a-time on the *deterministic* engine, not the MC paths).

## Git Workflow

- **Base branch:** `main` — all PRs target `main`
- **Branch naming:** `feat/`, `fix/`, `chore/` prefixes
- **Create a PR:** use `/pr-description` skill first to generate the title/body, then:
  ```bash
  git push -u origin <branch>
  gh pr create --base main --title "..." --body "$(cat <<'EOF'
  ...
  EOF
  )"
  ```
- **Check if already pushed:** `git push -u origin <branch>` is idempotent — safe to run even if the branch is already on remote

## Code Conventions

- **Type annotations** on all function/method signatures (use `typing` and `collections.abc`)
- **NumPy-style docstrings** with `.rst` code blocks showing usage examples
- **Inline comments** explain intent ("what"), not implementation ("how")
- **Line length:** 88 chars (Ruff/Black convention)
- **Float comparisons** use `_FLOAT_TOLERANCE = 1e-9` — never use `==` for floats
- **Ruff** is the sole linter/formatter (no flake8/black/isort)
