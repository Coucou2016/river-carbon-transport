@echo off
setlocal
cd /d "%~dp0"
py -3.12 --version || exit /b 1
py -3.12 -m venv .venv
call .venv\Scripts\python.exe -m pip install --upgrade pip
call .venv\Scripts\pip.exe install -i https://pypi.org/simple -r requirements.txt
call .venv\Scripts\pip.exe install -i https://pypi.org/simple geopandas openpyxl dataretrieval
echo Environment ready. Activate with: .venv\Scripts\activate.bat
