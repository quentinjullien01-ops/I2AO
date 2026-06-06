"""
I2AO — Lanceur (mode compilé PyInstaller ou mode script)
=========================================================
Fonctionne dans les deux cas :
  - Double-clic sur I2AO.exe (PyInstaller one-folder)
  - python launcher.pyw / pythonw launcher.pyw (développement)
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path


APP_TITLE = "I2AO — Analyse d'Appels d'Offres"
APP_PORT  = 8512


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def _root() -> Path:
    """Racine du projet selon le contexte d'exécution."""
    if getattr(sys, "frozen", False):
        # Mode PyInstaller : l'exe est dans dist/I2AO/, les données dans _internal/
        return Path(sys.executable).parent
    return Path(__file__).parent


def _app_path(root: Path) -> Path:
    return root / "src" / "i2ao" / "app.py"


def _free_port(start: int = 8512) -> int:
    for p in range(start, start + 80):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    return start


def _wait_ready(port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def _find_browser() -> tuple[str, list[str]] | None:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for p in candidates:
        if Path(p).exists():
            return p, ["--app={url}", "--window-size=1440,900", "--disable-extensions"]
    return None


def _msgbox(msg: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, APP_TITLE, 0x10)
    except Exception:
        print(msg)


# ---------------------------------------------------------------------------
# Démarrage Streamlit
# ---------------------------------------------------------------------------

def _start_streamlit_frozen(app_py: Path, port: int) -> None:
    """
    Mode PyInstaller : Streamlit est dans sys.path, on l'appelle directement
    dans un thread (évite de relancer un exe séparé).
    """
    os.environ.setdefault("STREAMLIT_SERVER_PORT", str(port))
    os.environ.setdefault("STREAMLIT_SERVER_ADDRESS", "127.0.0.1")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    from streamlit.web import bootstrap  # noqa: PLC0415
    bootstrap.run(str(app_py), "", [], {})


def _start_streamlit_subprocess(root: Path, app_py: Path, port: int) -> subprocess.Popen:
    """Mode développement : lance Streamlit comme sous-processus."""
    venv_python = root / ".venv" / "Scripts" / "python.exe"
    python = str(venv_python) if venv_python.exists() else sys.executable

    CREATE_NO_WINDOW = 0x08000000
    return subprocess.Popen(
        [
            python, "-m", "streamlit", "run", str(app_py),
            "--server.port", str(port),
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--logger.level", "error",
        ],
        cwd=str(root),
        creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    root   = _root()
    app_py = _app_path(root)

    if not app_py.exists():
        _msgbox(
            f"Fichier introuvable :\n{app_py}\n\n"
            "Vérifiez que le dossier I2AO est complet."
        )
        return

    port = _free_port(APP_PORT)
    proc = None

    if getattr(sys, "frozen", False):
        # ── Mode compilé : Streamlit dans un thread daemon ──
        t = threading.Thread(
            target=_start_streamlit_frozen,
            args=(app_py, port),
            daemon=True,
        )
        t.start()
    else:
        # ── Mode développement : sous-processus ──
        proc = _start_streamlit_subprocess(root, app_py, port)

    # Attend que le serveur réponde
    if not _wait_ready(port, timeout=60):
        if proc:
            proc.terminate()
        _msgbox(
            "L'application n'a pas démarré dans les temps.\n"
            "Relancez. Si le problème persiste, vérifiez\n"
            "votre antivirus ou lancez debug.bat."
        )
        return

    # Ouvre la fenêtre navigateur en mode app
    url     = f"http://127.0.0.1:{port}"
    browser = _find_browser()

    if browser:
        exe, args = browser
        cmd = [exe] + [a.replace("{url}", url) for a in args]
        browser_proc = subprocess.Popen(cmd)
        browser_proc.wait()
    else:
        import webbrowser
        webbrowser.open(url)

    # Arrêt propre
    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    # En mode frozen le thread daemon s'arrête automatiquement à la fin du process


if __name__ == "__main__":
    main()
