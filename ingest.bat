@echo off
chcp 65001 >nul
title LexMaroc - Ingestion des documents

echo.
echo  Ingestion des PDFs juridiques depuis .\data\ ...
echo.

if not exist .venv (
    echo  ERREUR : Lancez d'abord setup.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m backend.ingestion.ingest
echo.
echo  Ingestion terminee. Lancez run.bat pour demarrer.
pause
