@echo off
:: ============================================================
::  lancer.bat  —  Demarre I2AO (appele par I2AO.vbs)
::  Ne pas double-cliquer directement (fenetre console visible).
::  Utiliser I2AO.vbs ou le raccourci bureau.
:: ============================================================

setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "APP=%ROOT%\src\i2ao\app.py"
set "PORT=8512"

:: ---- Verifie l'environnement -----
if not exist "%PYTHON%" (
    msg * "Environnement non installe. Lance setup.bat d'abord."
    exit /b 1
)

:: ---- Trouve un port libre (essaie jusqu'à +10) ---------------
:FIND_PORT
netstat -an | find ":%PORT% " >nul 2>&1
if not errorlevel 1 (
    set /a PORT=%PORT%+1
    if %PORT% LSS 8525 goto FIND_PORT
)

:: ---- Lance Streamlit (hérite de la fenêtre cachée du VBS) ----
start /B "" "%PYTHON%" -m streamlit run "%APP%" ^
    --server.port %PORT% ^
    --server.address 127.0.0.1 ^
    --server.headless true ^
    --browser.gatherUsageStats false ^
    --logger.level error

:: ---- Attend que le serveur soit pret (max 40s) ----
set /a TRIES=0
:WAIT
ping -n 2 127.0.0.1 >nul
set /a TRIES=%TRIES%+1
powershell -NoProfile -Command ^
  "try { $r=(Invoke-WebRequest 'http://127.0.0.1:%PORT%' -UseBasicParsing -TimeoutSec 1).StatusCode; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    if %TRIES% LSS 20 goto WAIT
    msg * "I2AO n'a pas demarre (timeout). Relancez l'application."
    exit /b 1
)

:: ---- Ouvre dans Edge en mode app (sans barre d'adresse) ----
set "URL=http://127.0.0.1:%PORT%"
set "EDGE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"

if exist "%EDGE%" (
    start "" "%EDGE%" --app="%URL%" --window-size=1440,900
) else (
    :: Fallback Chrome
    set "CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe"
    if exist "%CHROME%" (
        start "" "%CHROME%" --app="%URL%" --window-size=1440,900
    ) else (
        :: Fallback navigateur par defaut
        start "" "%URL%"
    )
)

endlocal
