@ECHO OFF
SET ThisScriptsDirectory=%~dp0
SET Invokedirectory=%ThisScriptsDirectory%\invoke\ps1\debloat\src\scripts

rem Muda para a pasta onde os scripts .ps1 estão
cd /d "%Invokedirectory%"

rem Executa todos os arquivos .ps1 na pasta
for %%f in (*.ps1) do (
    rem Muda a cor para verde (32)
    echo ^[[32mExecutando %%f...^[[0m

    rem Executa o script PowerShell
    PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%cd%\%%f'"
    
    rem Espera 2 segundos antes de continuar
    timeout /t 2 /nobreak >nul
)

echo Todos os arquivos .ps1 foram executados.
pause
