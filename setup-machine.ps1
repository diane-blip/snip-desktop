# Creates a local environment; never starts Snip or adds startup persistence.
[CmdletBinding()]
param([string]$Python = '')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        if ($Python) { & $Python -m venv .venv } else { & py -3.12 -m venv .venv }
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 with its py launcher first.' }
    }
    & .\.venv\Scripts\python.exe -c "import sys,struct; assert sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8, 'Use 64-bit Python 3.12 for this release'"
    if ($LASTEXITCODE -ne 0) { throw 'The existing .venv is not Python 3.12.' }
    & .\.venv\Scripts\python.exe -m pip install pip==26.2.1
    if ($LASTEXITCODE -ne 0) { throw 'Package installer update failed.' }
    & .\.venv\Scripts\python.exe -m pip install --only-binary=:all: --require-hashes -r requirements.lock
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & .\.venv\Scripts\python.exe -m pip check
    if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed.' }
    $previousBrowserPath = $env:PLAYWRIGHT_BROWSERS_PATH
    try {
        $env:PLAYWRIGHT_BROWSERS_PATH = '0'
        & .\.venv\Scripts\python.exe -m playwright install chromium
        if ($LASTEXITCODE -ne 0) { throw 'Capture browser installation failed.' }
    } finally {
        if ($null -eq $previousBrowserPath) { Remove-Item Env:PLAYWRIGHT_BROWSERS_PATH -ErrorAction SilentlyContinue }
        else { $env:PLAYWRIGHT_BROWSERS_PATH = $previousBrowserPath }
    }
    if (-not (Test-Path -LiteralPath 'config.local.toml')) {
        Set-Content -LiteralPath 'config.local.toml' -Encoding ascii -Value '# Override settings from config.toml here.'
    }
    Write-Host 'Installed. Run .\.venv\Scripts\python.exe capture.py'
} finally {
    Pop-Location
}
