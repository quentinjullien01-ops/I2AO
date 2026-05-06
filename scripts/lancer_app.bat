@echo off
REM Lance l'application Streamlit I2AO
REM Usage : double-clic sur ce fichier ou execution depuis le terminal

cd /d "%~dp0\.."
.venv\Scripts\python.exe -m streamlit run src\i2ao\app.py
