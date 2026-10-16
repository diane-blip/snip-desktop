# Creates a Start-with-Windows shortcut for Capture. Run once per machine.
$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "Capture.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $appDir "start-capture.vbs"
$shortcut.WorkingDirectory = $appDir
$shortcut.Description = "Capture - screen capture hotkeys"
$shortcut.Save()

Write-Host "Startup shortcut created: $shortcutPath"
