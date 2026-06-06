@echo off
:: ============================================================
:: I2AO — Installateur Windows
:: Crée le venv, installe les dépendances, compile le lanceur,
:: crée le raccourci bureau.
:: Double-cliquer pour installer. Relancer pour mettre à jour.
:: ============================================================

title I2AO — Installation

setlocal EnableDelayedExpansion
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "VENV=%ROOT%\.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "PIP=%VENV%\Scripts\pip.exe"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   I2AO — Installation / Mise a jour     ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── 1. Vérifie Python ──────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Telecharge Python 3.12+ sur https://www.python.org
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] %PYVER% detecte

:: ── 2. Crée ou réutilise le venv ───────────────────────────
if not exist "%VENV%\Scripts\activate.bat" (
    echo [INFO] Creation de l'environnement virtuel...
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERREUR] Impossible de creer le venv.
        pause & exit /b 1
    )
    echo [OK] Environnement cree
) else (
    echo [OK] Environnement virtuel existant reutilise
)

:: ── 3. Met à jour pip ───────────────────────────────────────
echo [INFO] Mise a jour de pip...
"%PYTHON%" -m pip install --upgrade pip --quiet

:: ── 4. Installe les dépendances ────────────────────────────
echo [INFO] Installation des dependances (peut prendre quelques minutes)...
"%PIP%" install -e "%ROOT%" --quiet
if errorlevel 1 (
    echo [ERREUR] L'installation des dependances a echoue.
    echo Verifiez votre connexion internet et relancez.
    pause & exit /b 1
)

:: Installe pyinstaller dans le venv
"%PIP%" install pyinstaller --quiet
echo [OK] Dependances installees

:: ── 5. Compile le lanceur .exe ─────────────────────────────
echo [INFO] Compilation du lanceur I2AO.exe...
"%VENV%\Scripts\pyinstaller.exe" "%ROOT%\i2ao.spec" --distpath "%ROOT%\dist" --workpath "%ROOT%\build" --noconfirm --clean >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] La compilation du lanceur a echoue.
    echo Le raccourci utilisera le script Python directement.
    set "EXE_PATH=%VENV%\Scripts\pythonw.exe"
    set "EXE_ARGS=%ROOT%\launcher.pyw"
    goto :create_shortcut
)

set "EXE_PATH=%ROOT%\dist\I2AO.exe"
set "EXE_ARGS="
echo [OK] I2AO.exe compile dans dist\

:: ── 6. Crée le raccourci bureau ────────────────────────────
:create_shortcut
echo [INFO] Creation du raccourci bureau...

set "SHORTCUT=%USERPROFILE%\Desktop\I2AO.lnk"
set "ICON_PATH=%ROOT%\assets\icon.ico"

:: Utilise PowerShell pour créer le raccourci
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s  = $ws.CreateShortcut('%SHORTCUT%'); ^
   $s.TargetPath    = '%EXE_PATH%'; ^
   $s.Arguments     = '%EXE_ARGS%'; ^
   $s.WorkingDirectory = '%ROOT%'; ^
   $s.WindowStyle   = 1; ^
   $s.Description   = 'I2AO - Analyse Appels d Offres Structures'; ^
   if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%' }; ^
   $s.Save()"

if errorlevel 1 (
    echo [AVERT] Raccourci non cree - lancez manuellement dist\I2AO.exe
) else (
    echo [OK] Raccourci cree sur le Bureau
)

:: ── 7. Message final ───────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Installation terminee avec succes  !  ║
echo  ║                                          ║
echo  ║   Double-cliquez sur I2AO sur le         ║
echo  ║   bureau pour lancer l'application.      ║
echo  ║                                          ║
echo  ║   L'application fonctionne entierement   ║
echo  ║   en local — aucune connexion internet   ║
echo  ║   requise (hors appels API Gemini).      ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Propose de lancer immédiatement
set /p LAUNCH="Lancer I2AO maintenant ? [O/n] : "
if /i "!LAUNCH!" neq "n" (
    if exist "%ROOT%\dist\I2AO.exe" (
        start "" "%ROOT%\dist\I2AO.exe"
    ) else (
        start "" "%VENV%\Scripts\pythonw.exe" "%ROOT%\launcher.pyw"
    )
)

endlocal
