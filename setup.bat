@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title LexMaroc - Installation

echo.
echo  +==================================================+
echo  ^|          LEXMAROC - Installation Windows         ^|
echo  ^|      Chatbot Juridique IA - Lois Marocaines      ^|
echo  +==================================================+
echo.

REM === [1/6] Verification Python 3.11.6 ===
echo [1/6] Verification de Python 3.11.6...

set PYTHON_CMD=
set PYVER=

py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('py -3.11 --version 2^>^&1') do set PYVER=%%v
    set PYTHON_CMD=py -3.11
    goto :python_found
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
    set PYTHON_CMD=python
    goto :python_found
)

echo.
echo  ERREUR : Python introuvable.
echo  Telechargez Python 3.11.6 ici :
echo  https://www.python.org/downloads/release/python-3116/
echo  IMPORTANT : Cochez "Add Python to PATH" lors de l'installation.
echo.
pause
exit /b 1

:python_found
echo  Python !PYVER! detecte (commande : !PYTHON_CMD!)

echo !PYVER! | findstr /b "3.11" >nul
if %errorlevel% neq 0 (
    echo.
    echo  ERREUR : Python !PYVER! detecte, mais 3.11.6 est requis.
    echo  https://www.python.org/downloads/release/python-3116/
    echo.
    pause
    exit /b 1
)
echo  OK - Python 3.11.x confirme.

REM === [2/6] Creation venv ===
echo.
echo [2/6] Creation de l'environnement virtuel .venv...
if exist .venv (
    echo  .venv deja existant, reutilisation.
) else (
    !PYTHON_CMD! -m venv .venv
    if !errorlevel! neq 0 (
        echo  ERREUR : Echec creation du venv.
        pause
        exit /b 1
    )
    echo  OK - Environnement virtuel cree.
)

REM === [3/6] Installation dependances ===
echo.
echo [3/6] Installation des dependances Python (peut prendre 5-10 min)...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo  ERREUR : Echec installation des dependances.
    pause
    exit /b 1
)
echo  OK - Dependances installees.

REM === [4/6] Verification Ollama ===
echo.
echo [4/6] Verification d'Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ATTENTION : Ollama n'est pas installe.
    echo  Telechargez Ollama pour Windows :
    echo  https://ollama.com/download/windows
    echo  Apres installation, relancez setup.bat
    echo.
    pause
    exit /b 1
)
echo  OK - Ollama detecte.

REM === [5/6] Telechargement modele ===
echo.
echo [5/6] Telechargement du modele LLaMA 3 8B-Q4...
echo  (Cette etape peut prendre 10-20 minutes selon votre connexion)
ollama pull llama3:8b-q4
if %errorlevel% neq 0 (
    echo  ATTENTION : Impossible de telecharger llama3:8b-q4.
    echo  Si vous manquez de RAM, modifiez LLM_MODEL dans .env :
    echo    LLM_MODEL=gemma2:2b      (recommande, ~1.6 Go)
    echo    LLM_MODEL=tinyllama      (leger, ~600 Mo)
    echo  Puis relancez : ollama pull gemma2:2b
)

REM === [6/6] Configuration ===
echo.
echo [6/6] Configuration finale...
if not exist data mkdir data
if not exist chroma_db mkdir chroma_db
if not exist .env (
    echo MONGO_URI=mongodb://localhost:27017 > .env
    echo OLLAMA_BASE_URL=http://localhost:11434 >> .env
    echo LLM_MODEL=llama3:8b-q4 >> .env
    echo OLLAMA_NUM_CTX=4096 >> .env
    echo CHROMA_PERSIST_DIR=.\chroma_db >> .env
    echo TOP_K_RESULTS=5 >> .env
    echo  OK - Fichier .env cree.
) else (
    echo  .env deja existant.
)

echo.
echo  +==================================================+
echo  ^|              INSTALLATION TERMINEE               ^|
echo  +--------------------------------------------------+
echo  ^|  1. Vos PDFs sont dans .\data\  (deja en place) ^|
echo  ^|  2. Double-cliquez sur run.bat                   ^|
echo  ^|  3. Ouvrez : http://localhost:8501               ^|
echo  ^|  4. Cliquez "Indexer" dans l'interface           ^|
echo  +==================================================+
echo.
pause
