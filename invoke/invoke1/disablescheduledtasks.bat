@ECHO OFF
SET ThisScriptsDirectory=%~dp0
SET PowerShellScriptDirectory=%ThisScriptsDirectory%\material
SET PowerShellScriptPath=%PowerShellScriptDirectory%\disablescheduledtasks.ps1

PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%PowerShellScriptPath%'"


