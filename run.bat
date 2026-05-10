@echo off
chcp 65001 >nul
title LexMaroc - Chatbot Juridique IA

echo.
echo  Demarrage de LexMaroc...
echo.

if not exist .venv (
    echo  ERREUR : Environnement virtuel introuvable.
    echo  Lancez d'abord setup.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo  Ouverture de http://localhost:8501 ...
echo  (Appuyez sur Ctrl+C pour arreter)
echo.
streamlit run app.py
pause
