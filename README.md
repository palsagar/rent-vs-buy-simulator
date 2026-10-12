# Rent or Buy?

**Should you buy a home, or rent and invest the money you would have put into it?** Rent or Buy? simulates both choices over the years you plan to stay. It tells you which one leaves you wealthier, by how much, and how sure you can be.

Try it at **[rent-or-buy-sim.com](https://rent-or-buy-sim.com/)**. It opens in any web browser and needs no account.

![Rent or Buy? with the verdict at the top and the net value of buying and renting drawn year by year below it](https://raw.githubusercontent.com/palsagar/rent-vs-buy-simulator/main/src/simulator/static/screenshots/decision-chart.png)

## What it shows you

- **The verdict.** The headline says which choice comes out ahead at the end of your stay and by how much. Below it are the breakeven year and the share of simulated futures in which that choice wins. When the two choices end close together, the app says the answer is too close to call instead of picking a side.
- **The decision chart.** It draws the net value of buying and of renting for every year of your stay. Net value is what you would walk away with, minus everything you put in.
- **How sure is this?** A fan chart shows the spread of outcomes across the simulated futures, where growth and inflation vary from year to year.
- **What could change the answer?** A tornado chart tests one number at a time, lower and higher than yours. A sentence above it names the single changes that would flip the verdict. Each bar end prints the value that was tested. A side that stops at a slider limit is marked (min) or (max).
- **Region presets.** The United States, France (Lyon), Germany (Köln), the Netherlands and the United Kingdom (England and Northern Ireland) each set local tax rules, buying costs, typical prices and the currency.
- **First-time-buyer relief.** In regions that offer it, this is on by default. Where the law caps the price that qualifies, it switches itself off above that cap.
- **Market outlook.** Pick conservative, historical or optimistic assumptions for home prices, investment returns and rent increases.
- **Advanced settings in plain language.** Groups at the end of the inputs panel cover buying and selling costs, the yearly costs of owning, tax relief on the mortgage, tax when you sell the home, and tax on investments. Each group shows a one-line summary. A dot marks any value you changed from the region default, and you can reset a group to those defaults.
- **Shareable links.** The address bar always holds your exact scenario, and the Share button copies or shares it.
- **Help when you need it.** A guided tour is offered on your first visit, and the Guide explains the ideas behind the numbers. You can replay the tour from the Guide.

You can also see how much cash each choice costs you over time, read every figure in a year-by-year table, and download that table as CSV.

![The spread of simulated futures, and the tornado chart that shows which single change could flip the verdict](https://raw.githubusercontent.com/palsagar/rent-vs-buy-simulator/main/src/simulator/static/screenshots/fan-tornado.png)

## Get started

### Install from PyPI

You need Python 3.12 or newer.

```bash
pip install rent-vs-buy-simulator
rent-vs-buy
```

Open http://localhost:8501. To use another port, set `PORT`, for example `PORT=9000 rent-vs-buy`.

### Run from a clone

You need [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/palsagar/rent-vs-buy-simulator.git
cd rent-vs-buy-simulator
uv run uvicorn simulator.server:app --reload --port 8501
```

Open http://localhost:8501.

## Develop

```bash
uv venv --seed && uv pip install -e .        # set up
uv run pytest                                # Python tests
npm install && npx playwright install chromium
npx playwright test                          # browser tests
uv run ruff check src/ tests/                # lint
uv run ruff format src/ tests/               # format
uv run ty check src/                         # type check
```

The frontend has no build step. The browser loads the ES modules in `src/simulator/static/` as they are.

## Learn more

- [docs/README.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/docs/README.md): the index of all documentation.
- [docs/architecture.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/docs/architecture.md): how the server, the engine and the frontend fit together.
- [docs/formulas.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/docs/formulas.md): the math behind net value, the Monte Carlo simulation and the taxes.
- [docs/adr/README.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/docs/adr/README.md): the design decisions and why they were made.
- [CONTEXT.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/CONTEXT.md): the words the project uses and what each one means.
- [DEPLOYMENT.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/DEPLOYMENT.md): running the app in Docker and wiring up analytics.
- [CHANGELOG.md](https://github.com/palsagar/rent-vs-buy-simulator/blob/main/CHANGELOG.md): what changed in each release.
