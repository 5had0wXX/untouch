@echo off
setlocal

python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

pyinstaller --onefile --noconsole --name "P3-Recon" main.py

echo.
echo Build complete. Find P3-Recon.exe in the dist\ folder.
endlocal
