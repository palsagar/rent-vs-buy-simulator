"""CLI entry point for the rent-vs-buy simulator.

Serves the web app locally via uvicorn.

Examples
--------
After installing the package:

.. code-block:: bash

    rent-vs-buy          # http://localhost:8000
    PORT=9000 rent-vs-buy
"""

import os


def main() -> None:
    """Launch the web app on ``$PORT`` (default 8000)."""
    import uvicorn

    uvicorn.run(
        "simulator.server:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
