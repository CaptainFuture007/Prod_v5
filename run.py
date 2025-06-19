#!/usr/bin/env python3
"""
Quick launcher for the PDF Processing Pipeline
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch the Streamlit application"""
    app_path = Path(__file__).parent / "app.py"
    
    print("🚀 Starting PDF Processing Pipeline v5...")
    print("📄 This will open in your web browser at http://localhost:8501")
    print("💡 Use Ctrl+C to stop the application")
    print("-" * 60)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except FileNotFoundError:
        print("❌ Error: Streamlit not found. Please install requirements:")
        print("   pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

if __name__ == "__main__":
    main()