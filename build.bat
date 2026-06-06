@echo off
:: ============================================================
::  build.bat  —  Compile I2AO en application Windows autonome
::
::  Résultat : dist\I2AO\I2AO.exe  (+ tout le reste dans dist\I2AO\)
::  Copier le dossier dist\I2AO\ où vous voulez et lancer I2AO.exe
::
::  Prérequis : avoir lancé setup.bat au moins une fois
:: ============================================================

title I2AO - Compilation

setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "PYINST=%ROOT%\.venv\Scripts\pyinstaller.exe"

echo.
echo  ==========================================
echo   I2AO  --  Compilation application
echo  ==========================================
echo.

:: ---- Vérifie le venv ------------------------------------------
if not exist "%PYTHON%" (
    echo [ERREUR] Environnement introuvable.
    echo Lance setup.bat d'abord !
    pause & exit /b 1
)

:: ---- Installe PyInstaller si absent ---------------------------
"%PYTHON%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installation de PyInstaller...
    "%ROOT%\.venv\Scripts\pip.exe" install pyinstaller --quiet
)

:: ---- Nettoie les anciens builds -------------------------------
echo [INFO] Nettoyage des builds precedents...
if exist "%ROOT%\build" rmdir /s /q "%ROOT%\build"
if exist "%ROOT%\dist"  rmdir /s /q "%ROOT%\dist"

:: ---- Compilation ----------------------------------------------
echo [INFO] Compilation en cours (5-10 minutes, soyez patient)...
echo.

"%PYINST%" "%ROOT%\i2ao.spec" ^
    --distpath "%ROOT%\dist" ^
    --workpath "%ROOT%\build" ^
    --noconfirm

if errorlevel 1 (
    echo.
    echo [ERREUR] La compilation a echoue.
    echo Consultez les messages ci-dessus pour identifier le probleme.
    echo Si un module est manquant, ajoutez-le dans hiddenimports dans i2ao.spec
    pause & exit /b 1
)

:: ---- Vérifie que l'exe est bien là ----------------------------
if not exist "%ROOT%\dist\I2AO\I2AO.exe" (
    echo [ERREUR] I2AO.exe n'a pas ete genere.
    pause & exit /b 1
)

:: ---- Affiche la taille du dossier ----------------------------
echo.
for /f "tokens=3" %%a in ('dir /s /q "%ROOT%\dist\I2AO" ^| find "File(s)"') do set SIZE=%%a
echo [OK] Application compilee :
echo      Dossier : %ROOT%\dist\I2AO\
echo      Taille  : %SIZE% octets

:: ---- Raccourci bureau vers l'exe compilé ---------------------
echo.
echo [INFO] Creation du raccourci bureau...
set "EXE=%ROOT%\dist\I2AO\I2AO.exe"
set "SHORTCUT=%USERPROFILE%\Desktop\I2AO.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$ws = New-Object -ComObject WScript.Shell; ^
 $s  = $ws.CreateShortcut('%SHORTCUT%'); ^
 $s.TargetPath      = '%EXE%'; ^
 $s.WorkingDirectory = '%ROOT%\dist\I2AO'; ^
 $s.Description     = 'I2AO - Analyse Appels d Offres Structures'; ^
 $s.Save()"

echo [OK] Raccourci bureau cree

:: ---- Message final -------------------------------------------
echo.
echo  ==========================================
echo   Compilation reussie !
echo.
echo   Pour distribuer l'application :
echo     Copier le dossier dist\I2AO\ sur le PC cible
echo     Double-cliquer I2AO.exe
echo.
echo   Aucune installation Python requise
echo   sur le PC cible.
echo  ==========================================
echo.

set /p GO="Tester I2AO.exe maintenant ? [O/n] : "
if /i "%GO%" neq "n" (
    start "" "%ROOT%\dist\I2AO\I2AO.exe"
)

endlocal
