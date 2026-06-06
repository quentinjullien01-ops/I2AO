@echo off
:: ============================================================
::  I2AO — Setup  (a lancer UNE FOIS pour installer)
:: ============================================================
title I2AO - Installation

setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

echo.
echo  ==========================================
echo   I2AO  --  Installation
echo  ==========================================
echo.

:: ---- 1. Python present ? ----------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python est introuvable dans le PATH.
    echo.
    echo  Installe Python 3.12 depuis https://www.python.org
    echo  IMPORTANT : coche "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)
echo [OK] Python detecte :
python --version

:: ---- 2. Creer le venv -------------------------------------
if not exist "%ROOT%\.venv\Scripts\python.exe" (
    echo.
    echo [INFO] Creation de l'environnement virtuel...
    python -m venv "%ROOT%\.venv"
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer le venv.
        pause & exit /b 1
    )
    echo [OK] Venv cree
) else (
    echo [OK] Venv deja present
)

:: ---- 3. Mise a jour pip -----------------------------------
echo.
echo [INFO] Mise a jour de pip...
"%ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --no-warn-script-location
echo [OK] pip a jour

:: ---- 4. Installation des dependances ---------------------
echo.
echo [INFO] Installation des dependances (2-5 minutes selon connexion)...
"%ROOT%\.venv\Scripts\pip.exe" install -e "%ROOT%" --quiet --no-warn-script-location
if errorlevel 1 (
    echo.
    echo [ERREUR] L'installation a echoue. Details :
    "%ROOT%\.venv\Scripts\pip.exe" install -e "%ROOT%"
    pause & exit /b 1
)
echo [OK] Toutes les dependances sont installees

:: ---- 5. Raccourci bureau ----------------------------------
echo.
echo [INFO] Creation du raccourci sur le Bureau...

set "SHORTCUT=%USERPROFILE%\Desktop\I2AO.lnk"
set "VBS_LAUNCHER=%ROOT%\I2AO.vbs"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$ws = New-Object -ComObject WScript.Shell; ^
 $s  = $ws.CreateShortcut('%SHORTCUT%'); ^
 $s.TargetPath      = 'wscript.exe'; ^
 $s.Arguments       = '\"%VBS_LAUNCHER%\"'; ^
 $s.WorkingDirectory = '%ROOT%'; ^
 $s.Description     = 'I2AO - Analyse Appels d Offres'; ^
 $s.Save()"

if errorlevel 1 (
    echo [AVERT] Raccourci non cree automatiquement.
    echo  Clic droit sur I2AO.vbs > Envoyer vers > Bureau (raccourci)
) else (
    echo [OK] Raccourci I2AO cree sur le Bureau
)

:: ---- 6. Fin -----------------------------------------------
echo.
echo  ==========================================
echo   Installation terminee !
echo.
echo   Double-cliquez sur "I2AO" sur le Bureau.
echo   (ou sur I2AO.vbs dans ce dossier)
echo  ==========================================
echo.

set /p GO="Lancer I2AO maintenant ? [O/n] : "
if /i "%GO%" neq "n" (
    wscript "%ROOT%\I2AO.vbs"
)

endlocal
