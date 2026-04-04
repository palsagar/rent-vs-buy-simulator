# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Streamlit web app that compares buying property vs. renting and investing in equities. Users configure financial parameters and see interactive Plotly charts comparing three scenarios: Buy, Rent & Invest (down payment), and Rent & Invest (monthly savings).

## Commands

```bash
# Run the app
streamlit run src/simulator/app.py

# Tests
uv run pytest tests/                        # all tests
uv run pytest tests/test_engine.py           # single file
uv run pytest tests/test_engine.py::TestClassName::test_name  # single test
uv run pytest --cov --cov-report=term        # with coverage (80% min enforced)

# Lint & format
uv run ruff check src/ tests/         # lint
uv run ruff check --fix src/ tests/   # lint + autofix
uv run ruff format src/ tests/        # format

# Setup
uv venv --seed && uv pip install -e .
```

## Architecture

**Data flow:** `User Input (src/simulator/app.py) → SimulationConfig (models.py) → calculate_scenarios (engine.py) → SimulationResults (models.py) → Visualization (visualization.py) / PDF (utils.py)`

- **`src/simulator/app.py`** — Streamlit UI entry point. Sidebar inputs, chart rendering, scenario management. Uses `st.session_state` for state.
- **`src/simulator/models.py`** — `SimulationConfig` and `SimulationResults` dataclasses. Validation in `__post_init__`.
- **`src/simulator/engine.py`** — Pure calculation engine. `calculate_scenarios(config)` returns `SimulationResults`. All time-series math uses NumPy vectorized arrays (no Python loops). Uses `numpy_financial.pmt()`/`pv()` for mortgage amortization.
- **`src/simulator/visualization.py`** — Plotly chart builders (asset growth, cumulative outflows, net value).
- **`src/simulator/scenario_manager.py`** — Save/load/compare up to 5 scenarios.
- **`src/simulator/utils.py`** — PDF report generation via fpdf2.

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
