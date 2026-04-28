@echo off
chcp 65001 >nul
cls
echo.
echo ============================================================
echo   AGENTE DE PROSPECÇÃO IA — SETUP AUTOMÁTICO
echo ============================================================
echo.

:: Tentar localizar Python via py launcher (Windows Store / installer)
set PYTHON=
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=py -3
    goto :python_ok
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=python
    goto :python_ok
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=python3
    goto :python_ok
)

echo [ERRO] Python nao encontrado no PATH!
echo Execute no CMD: py install 3.12
echo Depois execute este arquivo novamente.
pause
exit /b 1

:python_ok

echo [OK] Python encontrado.
%PYTHON% --version
echo.

:: Criar ambiente virtual
echo [1/4] Criando ambiente virtual...
if exist venv (
    echo     venv ja existe, pulando...
) else (
    %PYTHON% -m venv venv 2>&1
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
)
echo [OK] Ambiente virtual pronto.
echo.

:: Ativar venv e instalar dependências
echo [2/4] Instalando dependências (pode demorar alguns minutos)...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERRO] Falha na instalação de dependências.
    pause
    exit /b 1
)
echo [OK] Dependências instaladas.
echo.

:: Criar pastas necessárias
echo [3/4] Criando estrutura de pastas...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist data\templates mkdir data\templates
echo [OK] Pastas criadas.
echo.

:: Configuração do .env
echo [4/4] Verificando configurações...
if not exist .env (
    echo [AVISO] Arquivo .env não encontrado! Criando modelo...
    copy .env.example .env >nul 2>&1
)
echo.
echo ============================================================
echo   SETUP CONCLUÍDO COM SUCESSO!
echo ============================================================
echo.
echo PRÓXIMOS PASSOS:
echo.
echo  1. Abra o arquivo .env e preencha:
echo     - EVOLUTION_API_URL  (URL da sua Evolution API)
echo     - EVOLUTION_API_KEY  (sua chave de API)
echo     - EVOLUTION_INSTANCE (nome da instância)
echo     - ANTHROPIC_API_KEY  (opcional, para mensagens IA)
echo     - NICHO_BUSCA        (ex: restaurantes, salões, etc.)
echo     - CIDADE_BUSCA       (sua cidade)
echo.
echo  2. Execute: iniciar.bat
echo.
pause
