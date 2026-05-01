@ECHO OFF
SET ThisScriptsDirectory=%~dp0
SET PowerShellScriptDirectory=%ThisScriptsDirectory%\material
SET PowerShellScriptPath=%PowerShellScriptDirectory%\clearlastfolder.ps1

PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%PowerShellScriptPath%'"


