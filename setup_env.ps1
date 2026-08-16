# River carbon transport - Windows environment setup
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Error "Python launcher 'py' not found. Install Python 3.12 from python.org."
}
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
# Use pypi.org if mirror fails (IncompleteRead on some mirrors)
.\.venv\Scripts\pip.exe install -i https://pypi.org/simple -r requirements.txt
.\.venv\Scripts\pip.exe install -i https://pypi.org/simple geopandas openpyxl dataretrieval
Write-Host "Environment ready. Activate with: .\.venv\Scripts\Activate.ps1"
