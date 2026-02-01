#!/usr/bin/env python3
"""Quick start script for the simulator application."""

import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import numpy
        import pandas
        import plotly
        import streamlit
        import numpy_financial
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\n💡 Please install dependencies first:")
        print("   pip install -e .")
        return False


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
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", str(app_path)
    ])


if __name__ == "__main__":
    main()
