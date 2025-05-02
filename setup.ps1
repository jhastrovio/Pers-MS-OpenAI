# PowerShell script to set up development environment

# Stop on first error
$ErrorActionPreference = "Stop"

Write-Host "Setting up development environment..." -ForegroundColor Green

# Check if Python is installed
try {
    python --version
} catch {
    Write-Host "Python is not installed or not in PATH. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
pip install -r requirements-test.txt

# Create config directory if it doesn't exist
if (-not (Test-Path "config")) {
    Write-Host "Creating config directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "config"
}

# Create secrets.json from template if it doesn't exist
if (-not (Test-Path "config\secrets.json")) {
    Write-Host "Creating secrets.json template..." -ForegroundColor Yellow
    Copy-Item "config\secrets.json.template" "config\secrets.json"
    Write-Host "Please update config\secrets.json with your credentials" -ForegroundColor Red
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "To activate the virtual environment in the future, run: .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "To deactivate, run: deactivate" -ForegroundColor Cyan 