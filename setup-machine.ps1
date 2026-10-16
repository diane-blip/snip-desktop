# Install or repair Capture on this Windows machine.
$ErrorActionPreference = "Stop"
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $appDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    $systemPython = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    if (-not (Test-Path -LiteralPath $systemPython)) {
        throw "Python 3.12 is not installed in the expected user location."
    }
    & $systemPython -m venv (Join-Path $appDir ".venv")
}

& $venvPython -m pip install -r (Join-Path $appDir "requirements.txt")
& $venvPython -m playwright install chromium
& (Join-Path $appDir "setup-startup.ps1")

Write-Host "Capture is installed. Launch start-capture.vbs once to use it now."
