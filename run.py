#!/usr/bin/env python3
"""Quick start script for the simulator application."""

import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    import importlib.util

    dependencies = [
        "numpy",
        "pandas",
        "plotly",
        "streamlit",
        "numpy_financial",
    ]

    for dep in dependencies:
        if importlib.util.find_spec(dep) is None:
            print(f"❌ Missing dependency: {dep}")
            print("\n💡 Please install dependencies first:")
            print("   pip install -e .")
            return False

    return True


def main():
    """Main entry point."""
    print("🏠 Real Estate vs. Equity Simulator")
    print("=" * 50)

    if not check_dependencies():
        sys.exit(1)

    print("✅ All dependencies installed")
    print("🚀 Starting Streamlit application...")
    print("\nPress Ctrl+C to stop the server\n")

    # Get the path to app.py
    app_path = Path(__file__).parent / "app.py"

    # Run streamlit
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)])


if __name__ == "__main__":
    main()
