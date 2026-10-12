# Contributing

Thanks for helping. This guide covers how to set up, run, test and submit changes. For how the app is built, read
[docs/architecture.md](docs/architecture.md) first; this file does not repeat it.

## Set up

You need [uv](https://docs.astral.sh/uv/) (it installs the right Python for you), Python 3.12 or newer, and Node.js 22 or newer
for the browser tests.

```bash
git clone https://github.com/palsagar/rent-vs-buy-simulator.git
cd rent-vs-buy-simulator
uv sync                                  # Python dependencies and the package, in .venv
npm ci                                   # Playwright
npx playwright install chromium          # the browser the tests use (add --with-deps on Linux)
uv tool install pre-commit && pre-commit install   # optional but recommended: lint and format on every commit
```

## Run the app

```bash
uv run uvicorn simulator.server:app --reload --port 8501
```

Open http://localhost:8501. The frontend has no build step: edit files under `src/simulator/static/` and reload the page.
The page loads Plotly.js from a CDN, so charts need an internet connection.

## Test

```bash
uv run pytest tests/                       # Python tests
uv run pytest --cov --cov-report=term      # with coverage; the build fails under 80%
npx playwright test                        # browser tests
npx playwright test tests/verdict.spec.js  # one browser spec
```

`npx playwright test` starts its own app servers on ports 8323 and 8324, so you do not need to start the app first. Make sure
nothing else is using those ports. CI runs pytest on Python 3.12, 3.13 and 3.14, and the Playwright suite on Chromium.

## Lint, format and type check

```bash
uv run ruff check src/ tests/        # lint (add --fix to apply safe fixes)
uv run ruff format src/ tests/       # format
uv run ty check src/                 # type check
```

Ruff is the only linter and formatter. It includes security rules (the `S` set). If one fires on code that is safe on purpose,
add a `# noqa: S###` with a short reason. Do not blanket-disable the rule. The pre-commit hook runs ruff and a few whitespace checks;
it does not run tests.

## Branches and pull requests

- Branch from `main` and name the branch `feat/...`, `fix/...` or `chore/...`.
- Open the pull request against `main`. Keep it to one change.
- Give the pull request a conventional title: `type: short description`, for example `fix: round the breakeven year down`.
  We squash-merge, so the PR title becomes the commit message on `main`.

### How the title drives releases

[release-please](https://github.com/googleapis/release-please) reads the commit messages on `main`, keeps one open
"chore: release X.Y.Z" pull request, and builds the version and `CHANGELOG.md` from them. You never edit the version by hand.

| Title starts with | Effect |
|---|---|
| `feat:` | minor version bump, listed under Features |
| `fix:` | patch version bump, listed under Bug Fixes |
| `perf:`, `revert:` | listed in the changelog |
| `feat!:` or `fix!:` (the `!`) | major version bump |
| `docs:`, `chore:`, `ci:`, `test:`, `refactor:`, `style:`, `build:` | no release, hidden from the changelog |

Merging the release pull request tags the version, creates the GitHub Release and publishes to PyPI. Dependabot pull requests use
`chore(deps)` and `ci(deps)` titles, so they do not trigger a release on their own.

## Changing the financial model

The numbers are the product, so changes to them need more care:

1. Update [docs/formulas.md](docs/formulas.md) in the same pull request so the math on paper matches the code.
2. If you change a modeling convention (how net value is measured, how a tax is treated, what a strategy includes), add a decision record
   in [docs/adr/](docs/adr/README.md): copy the shape of an existing one, use the next number, and add it to the table in `docs/adr/README.md`.
3. Add a test that checks the result against a hand calculation. Put the arithmetic in a comment or docstring so a reader can
   redo it. Use a tolerance for floats, never `==` (`_FLOAT_TOLERANCE = 1e-9` in the tests).
4. Test the edges: 0% rates, a down payment of 100%, a one-year horizon, region limits.
5. Use the terms in [CONTEXT.md](CONTEXT.md) in code, UI text and docs.

## Code style

See the Code Conventions in [CLAUDE.md](CLAUDE.md): type annotations on every signature, NumPy-style docstrings, comments that explain
intent, 88-character lines.

## Troubleshooting

**"Address already in use" / the app will not start.** Another process holds the port. Find it with `lsof -i :8501`, stop it, or pick
another port: `uv run uvicorn simulator.server:app --port 8502`. The installed command takes the port from the environment:
`PORT=9000 rent-vs-buy`.

**Playwright says a port is already used** (`http://127.0.0.1:8323/api/health is already used`). A previous test run left a server
behind. Stop whatever listens on 8323 and 8324 (`lsof -i :8323 -i :8324`) and run again. The config never reuses a running server on purpose.

**Playwright says "Executable doesn't exist" or the browser is missing.** Install the browser: `npx playwright install chromium`.
On a fresh Linux machine use `npx playwright install --with-deps chromium`. Do this again after a Playwright upgrade.

**`ModuleNotFoundError: No module named 'simulator'`.** You ran Python outside the project environment. Use `uv run ...` (it installs the
package in editable mode for you), or run `uv sync` and activate `.venv`. If you manage your own environment, `uv pip install -e .` does the same.

**Charts are empty or the page looks unstyled offline.** Plotly.js comes from a CDN. Connect to the internet; the Playwright tests need it too.

**CI fails on `uv sync --frozen` or on the lockfile.** You changed dependencies in `pyproject.toml` without updating `uv.lock`.
Run `uv lock` and commit the result.

**pre-commit changed files and the commit stopped.** That is intended: the hooks fixed formatting or whitespace. Review the changes,
`git add` them and commit again. Skip once with `git commit --no-verify` only if you must; CI runs the same ruff checks.

**Coverage fails under 80%.** Run `uv run pytest --cov --cov-report=term-missing` to see which lines no test reaches.
