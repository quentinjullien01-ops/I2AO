"""
I2AO — Lanceur bureau Windows
==============================
Script .pyw : s'exécute sans fenêtre console sur Windows.

Fonctionnement :
  1. Démarre Streamlit sur un port local libre
  2. Attend que le serveur soit prêt (polling HTTP)
  3. Ouvre l'interface dans Edge ou Chrome en mode "app" (fenêtre sans barre d'adresse)
  4. Quand la fenêtre navigateur se ferme, stoppe Streamlit proprement

Usage direct (sans compilation) :
    pythonw launcher.pyw
    python launcher.pyw   (avec console, pour debug)

Compilé en .exe via PyInstaller :
    pyinstaller i2ao.spec
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

APP_TITLE  = "I2AO — Analyse d'Appels d'Offres"
PORT_RANGE = range(8510, 8600)  # plage de ports pour éviter les conflits
STREAMLIT_MODULE = "src/i2ao/app.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _root() -> Path:
    """Racine du projet : chemin du .exe (PyInstaller) ou du script."""
    if getattr(sys, "frozen", False):
        # Mode PyInstaller : l'exe est dans dist/, le projet un niveau au-dessus
        return Path(sys.executable).parent.parent
    return Path(__file__).parent


def _find_free_port() -> int:
    for port in PORT_RANGE:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return 8510  # fallback


def _wait_for_server(port: int, timeout: float = 30.0) -> bool:
    """Attend que Streamlit réponde sur le port (max timeout secondes)."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def _find_browser() -> tuple[str, list[str]] | None:
    """
    Retourne (chemin_exe, args_app_mode) du premier navigateur trouvé.
    Priorité : Edge > Chrome > Firefox (Firefox ne supporte pas --app).
    """
    candidates = [
        # Microsoft Edge (toujours présent sur Windows 10/11)
        (
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            ["--app={url}", "--window-size=1400,900"],
        ),
        (
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ["--app={url}", "--window-size=1400,900"],
        ),
        # Google Chrome
        (
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            ["--app={url}", "--window-size=1400,900"],
        ),
        (
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ["--app={url}", "--window-size=1400,900"],
        ),
    ]
    for path, args in candidates:
        if Path(path).exists():
            return path, args
    return None


def _open_app_window(url: str) -> subprocess.Popen | None:
    """Ouvre l'app dans une fenêtre navigateur sans barre d'adresse."""
    browser = _find_browser()
    if browser:
        exe, args = browser
        cmd = [exe] + [a.replace("{url}", url) for a in args]
        return subprocess.Popen(cmd)
    # Fallback : navigateur par défaut (avec barre d'adresse)
    webbrowser.open(url)
    return None


def _show_error(msg: str) -> None:
    """Affiche une boîte de dialogue d'erreur Windows."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, APP_TITLE, 0x10)  # MB_ICONERROR
    except Exception:
        print(msg)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    root = _root()
    app_path = root / STREAMLIT_MODULE

    if not app_path.exists():
        _show_error(
            f"Impossible de trouver l'application :\n{app_path}\n\n"
            "Vérifiez que le dossier I2AO est complet."
        )
        return

    port = _find_free_port()
    url  = f"http://127.0.0.1:{port}"

    # Détermine le Python / streamlit à utiliser
    # Priorité : venv du projet > Python courant
    venv_python = root / ".venv" / "Scripts" / "python.exe"
    python_exe  = str(venv_python) if venv_python.exists() else sys.executable

    streamlit_cmd = [
        python_exe, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.headless", "true",
        "--server.address", "127.0.0.1",   # localhost uniquement — pas de réseau
        "--browser.gatherUsageStats", "false",
        "--logger.level", "error",
    ]

    # Lance Streamlit en arrière-plan (sans fenêtre console)
    CREATE_NO_WINDOW = 0x08000000
    try:
        proc = subprocess.Popen(
            streamlit_cmd,
            cwd=str(root),
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        _show_error(
            f"Python introuvable : {python_exe}\n\n"
            "Relancez installer.bat pour reconfigurer l'environnement."
        )
        return

    # Attend que le serveur soit prêt
    if not _wait_for_server(port, timeout=45):
        proc.terminate()
        _show_error(
            "Streamlit n'a pas démarré dans les temps (45 s).\n"
            "Relancez l'application. Si le problème persiste, \n"
            "vérifiez que le port n'est pas bloqué par un antivirus."
        )
        return

    # Ouvre la fenêtre applicative
    browser_proc = _open_app_window(url)

    # Attend la fermeture du navigateur (si on l'a lancé nous-mêmes)
    if browser_proc:
        browser_proc.wait()
    else:
        # Fallback webbrowser.open : on attend juste que l'utilisateur tue le process
        try:
            proc.wait()
        except KeyboardInterrupt:
            pass

    # Arrêt propre de Streamlit
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


if __name__ == "__main__":
    main()
