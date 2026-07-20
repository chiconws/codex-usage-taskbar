$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Create the virtual environment first: python -m venv .venv"
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name CodexUsageTaskbar `
    --icon (Join-Path $PSScriptRoot "assets\codex_usage_icon.ico") `
    --add-data "$(Join-Path $PSScriptRoot 'assets\codex_usage_icon.ico');assets" `
    --paths (Join-Path $PSScriptRoot "src") `
    (Join-Path $PSScriptRoot "packaging_entry.py")
