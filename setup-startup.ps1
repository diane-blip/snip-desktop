# Optional shortcuts only. Does not install packages or start Snip.
[CmdletBinding(SupportsShouldProcess)]
param([switch]$Remove, [string]$Directory = '')
$ErrorActionPreference = 'Stop'
$appDir = $PSScriptRoot
$python = Join-Path $appDir '.venv\Scripts\pythonw.exe'
$script = Join-Path $appDir 'capture.py'
$legacyLauncher = Join-Path $appDir 'start-capture.vbs'
if (-not $Remove -and -not (Test-Path -LiteralPath $python)) {
    throw 'Run setup-machine.ps1 before creating shortcuts.'
}
$shell = New-Object -ComObject WScript.Shell
$destinations = if ($Directory) {
    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { throw 'Shortcut directory does not exist.' }
    @((Resolve-Path -LiteralPath $Directory).Path)
} else {
    @([Environment]::GetFolderPath('Startup'), [Environment]::GetFolderPath('Desktop'))
}
$shortcuts = foreach ($folder in $destinations) {
    $path = Join-Path $folder 'Snip Desktop.lnk'
    $shortcut = $shell.CreateShortcut($path)
    $exists = Test-Path -LiteralPath $path
    $ours = ($shortcut.TargetPath -eq $python -and $shortcut.Arguments -eq ('"' + $script + '"')) -or $shortcut.TargetPath -eq $legacyLauncher -or (
        $shortcut.TargetPath -eq (Join-Path $env:WINDIR 'System32\wscript.exe') -and
        $shortcut.Arguments -eq ('"' + $legacyLauncher + '"')
    )
    if ($exists -and -not $ours) {
        throw "A Snip shortcut from another installation exists at $path. No shortcuts were changed."
    }
    [pscustomobject]@{ Path = $path; Shortcut = $shortcut; Exists = $exists }
}
# Validate every destination before changing any of them.
foreach ($entry in $shortcuts) {
    if ($Remove) {
        if ($entry.Exists -and $PSCmdlet.ShouldProcess($entry.Path, 'Remove shortcut')) {
            Remove-Item -LiteralPath $entry.Path
        }
    } elseif ($PSCmdlet.ShouldProcess($entry.Path, 'Create shortcut')) {
        $shortcut = $entry.Shortcut
        $shortcut.TargetPath = $python
        $shortcut.Arguments = '"' + $script + '"'
        $shortcut.WorkingDirectory = $appDir
        $shortcut.IconLocation = (Join-Path $appDir 'capture.ico') + ',0'
        $shortcut.Description = 'Snip: screen capture'
        $shortcut.Save()
    }
}
