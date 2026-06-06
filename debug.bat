@echo off
:: ============================================================
::  debug.bat  —  Lance I2AO avec la console visible
::  Utiliser si l'app ne demarre pas pour voir les erreurs.
:: ============================================================
title I2AO - Mode Debug

setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "APP=%ROOT%\src\i2ao\app.py"

echo === DEBUG I2AO ===
echo ROOT    : %ROOT%
echo PYTHON  : %PYTHON%
echo APP     : %APP%
echo.

if not exist "%PYTHON%" (
    echo [ERREUR] Python venv introuvable : %PYTHON%
    echo Lance setup.bat d'abord !
    pause & exit /b 1
)

if not exist "%APP%" (
    echo [ERREUR] app.py introuvable : %APP%
    pause & exit /b 1
)

echo [OK] Demarrage de Streamlit sur http://127.0.0.1:8513
echo Ferme cette fenetre pour arreter l'application.
echo.

"%PYTHON%" -m streamlit run "%APP%" ^
    --server.port 8513 ^
    --server.address 127.0.0.1 ^
    --server.headless false ^
    --browser.gatherUsageStats false

pause
endlocal
