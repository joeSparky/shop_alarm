[CmdletBinding()]
param(
    [string]$ProjectPath = "C:\Projects\shop_alarm"
)

$ErrorActionPreference = "Stop"

Write-Host "Setting up the Python environment in $ProjectPath"

if (-not (Test-Path -LiteralPath $ProjectPath -PathType Container)) {
    throw "Project folder not found: $ProjectPath"
}

Set-Location -LiteralPath $ProjectPath

$PythonCommand = Get-Command py -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    throw "Python launcher 'py' was not found. Install Python and select 'Add Python to PATH'."
}

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    Write-Host "Creating .venv..."
    & py -3 -m venv .venv
}
else {
    Write-Host ".venv already exists; keeping it."
}

$VenvPython = Join-Path $ProjectPath ".venv\Scripts\python.exe"

Write-Host "Updating pip..."
& $VenvPython -m pip install --upgrade pip

if (Test-Path -LiteralPath "requirements.txt" -PathType Leaf) {
    Write-Host "Installing packages from requirements.txt..."
    & $VenvPython -m pip install -r requirements.txt
}
else {
    Write-Host "requirements.txt was not found; installing the alarm-test packages..."
    & $VenvPython -m pip install pytest requests python-dotenv
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Activate it with:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "Then run the tests with:"
Write-Host "  pytest -v"

