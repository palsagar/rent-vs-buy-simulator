# The frontend migrates from Streamlit to a FastAPI + static JavaScript stack

The Streamlit UI was the last pre-redesign surface: clunky rerun-everything interactions, no shareable URLs, and a look that diverged from the author's other public apps (webgpu-fluid-solver, webgpu-gray-scott), which share a hand-rolled GitHub-dark static stack. With the engine model stable after the Phase 1 rewrite (ADRs 0001–0005), the porting risk ADR-0006 cited is gone. The frontend is now a static ES-module app (Plotly.js via CDN) served by FastAPI, calling a JSON API that wraps the unchanged Python engine; Streamlit, Kaleido, and Python-Plotly leave the dependency tree. The page implements the redesign spec's narrative (verdict hero → decision chart → confidence → money flows → numbers) in the GitHub-dark token system with Buy #f0883e / Rent #58a6ff.

## Considered Options

- Port the engine to TypeScript (fully client-side): rejected — the tested NumPy engine would need re-implementation and re-validation, and the PyPI package would lose its purpose.
- Pyodide (Python engine in the browser): rejected — multi-MB WASM/NumPy first load and an exotic toolchain for zero correctness gain.
- Keep Streamlit and re-theme: rejected — the interaction ceiling (full-page reruns, widget model) was the motivating problem.

## Consequences

- ADR-0006 is superseded; the redesign spec §4 light-editorial theme is replaced by the dark token system, and §5's "recorded future path" is closed in a shape it did not predict (Python stays server-side).
- The `rent-vs-buy` CLI and Docker images serve uvicorn on port 8000 (was Streamlit on 8501); Coolify needs only the port change.
- The verdict, breakeven, and confidence are computed only server-side from the same Net Value series — the ADR-0001 invariant now extends across the wire by construction.
- Share URLs replace save/compare; the no-storage privacy stance is preserved.
