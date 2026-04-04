"""CLI entry point for the rent-vs-buy simulator.

Launches the Streamlit app in the user's default browser.

Examples
--------
After installing the package:

.. code-block:: bash

    rent-vs-buy
"""

import sys
from pathlib import Path


def main() -> None:
    """Launch the Streamlit simulator app."""
    from streamlit.web.cli import main_run

    app_path = str(Path(__file__).parent / "app.py")
    sys.argv = ["streamlit", "run", app_path, "--server.headless=false"]
    main_run(args=[app_path, "--server.headless=false"])
