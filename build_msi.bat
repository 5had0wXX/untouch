@echo off
setlocal

REM Requires WiX Toolset v3.11+ installed and on PATH (candle.exe, light.exe).

python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

pyinstaller --onefile --noconsole --name "Untouch-P3" app.py

candle installer.wxs -out installer.wixobj
light installer.wixobj -out Untouch-P3-Installer.msi

echo.
echo MSI build complete: Untouch-P3-Installer.msi
endlocal
