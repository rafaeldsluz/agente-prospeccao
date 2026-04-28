"""
Ponto de entrada principal. Inicia o Streamlit com o scheduler embutido.
Uso: python run.py
"""
import subprocess
import sys
import os

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "app/main.py",
        "--server.port=8501",
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
        "--theme.base=dark",
        "--theme.primaryColor=#4f8ef7",
        "--theme.backgroundColor=#0e1117",
        "--theme.secondaryBackgroundColor=#1e2130",
    ]
    subprocess.run(cmd)
