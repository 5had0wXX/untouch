@echo off
setlocal

python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

pyinstaller --onefile --noconsole --name "Untouch-P3" app.py

echo.
echo Build complete. Find Untouch-P3.exe in the dist\ folder.
endlocal
