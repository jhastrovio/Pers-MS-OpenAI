# PowerShell script to set up development environment

$ErrorActionPreference = "Stop"

Write-Host "Setting up development environment..." -ForegroundColor Green

# Check if Python is installed
try {
    python --version
} catch {
    Write-Host "Python is not installed or not in PATH. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
pip install -r requirements-test.txt

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "To activate the virtual environment in the future, run: .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "To deactivate, run: deactivate" -ForegroundColor Cyan
Write-Host "To run the local server, use: uvicorn app:app --reload" -ForegroundColor Cyan 