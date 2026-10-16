' Launches Capture silently (no console window) using the local venv.
Dim shell, appDir
Set shell = CreateObject("WScript.Shell")
appDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
shell.CurrentDirectory = appDir
shell.Run """" & appDir & ".venv\Scripts\pythonw.exe"" """ & appDir & "capture.py""", 0, False
