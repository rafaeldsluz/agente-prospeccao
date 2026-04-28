@echo off
chcp 65001 >nul
cls
echo.
echo ============================================================
echo   AGENTE DE PROSPECÇÃO IA — INICIANDO...
echo ============================================================
echo.

if not exist venv (
    echo [ERRO] Ambiente virtual nao encontrado.
    echo Execute setup.bat primeiro!
    pause
    exit /b 1
)

set VENV_PYTHON=%~dp0venv\Scripts\python.exe

if not exist "%VENV_PYTHON%" (
    echo [ERRO] Python do venv nao encontrado em: %VENV_PYTHON%
    pause
    exit /b 1
)

echo [OK] Usando Python: %VENV_PYTHON%
echo.
echo Abrindo interface em http://localhost:8501
echo Pressione Ctrl+C para encerrar o agente.
echo.

"%VENV_PYTHON%" -m streamlit run app/main.py --server.port=8501 --server.headless=false --browser.gatherUsageStats=false --theme.base=dark --theme.primaryColor=#4f8ef7 --theme.backgroundColor=#0e1117 --theme.secondaryBackgroundColor=#1e2130
pause
