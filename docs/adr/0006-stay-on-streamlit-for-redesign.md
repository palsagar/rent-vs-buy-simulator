# The redesign ships on Streamlit; a client-side rewrite is deferred, not rejected

**Status:** Superseded by [ADR-0008](0008-fastapi-static-frontend.md) (2026-07-17) — the deferred client-side path arrived, in a different shape than predicted (Python engine behind an API, not a TS/Pyodide port).

The redesign (ADRs 0001–0005) is implemented in the existing Streamlit app via full theming (config.toml palette/fonts, injected CSS for the verdict hero, one shared Plotly template) rather than a frontend rewrite. Rationale: every high-impact change in the redesign is stack-independent, the engine is changing in the same release (porting it to TypeScript now would mean porting twice), and Streamlit theming lands in days rather than weeks.

A static client-side app (engine in TypeScript or Pyodide) remains the recorded future path if the project outgrows Streamlit — its concrete wins are instant slider feedback without server round-trips, real mobile polish, and static hosting. Revisit once the engine model is stable.
