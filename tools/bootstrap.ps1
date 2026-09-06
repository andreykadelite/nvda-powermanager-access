$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot '.venv'
if (-not (Test-Path -LiteralPath (Join-Path $venvPath 'Scripts\python.exe'))) {
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed' }
}
& (Join-Path $venvPath 'Scripts\python.exe') -m pip install -r (Join-Path $projectRoot 'requirements-dev.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
Write-Output "Ready: $venvPath"
