$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$pythonExecutable = Join-Path $projectRoot ".venv\Scripts\python.exe"
$outputExecutable = Join-Path $projectRoot "dist\KeysPro.exe"

if (-not (Test-Path -LiteralPath $pythonExecutable -PathType Leaf)) {
    throw "Virtual environment Python was not found at $pythonExecutable"
}

& $pythonExecutable -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) {
    throw "Automated tests failed. Build stopped."
}

& $pythonExecutable -m ruff check src tests
if ($LASTEXITCODE -ne 0) {
    throw "Static code checks failed. Build stopped."
}

& $pythonExecutable -m PyInstaller --noconfirm --clean KeysPro.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path -LiteralPath $outputExecutable -PathType Leaf)) {
    throw "PyInstaller finished without creating $outputExecutable"
}

Write-Host "Build complete: $outputExecutable"
