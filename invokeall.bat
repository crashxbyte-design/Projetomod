@ECHO OFF
SET ThisScriptsDirectory=%~dp0
SET Invokedirectory=%ThisScriptsDirectory%\invoke

rem Muda para a pasta onde os arquivos .bat estão
cd /d "%Invokedirectory%"

rem Executa todos os arquivos .bat na pasta
for %%f in (*.bat) do (
    rem Muda a cor para verde (32)
    echo ^[[32mExecutando %%f...^[[0m

    rem Executa o arquivo .bat
    call "%%f"
    
    rem Espera 2 segundos antes de continuar
    timeout /t 2 /nobreak >nul
)

echo Todos os arquivos .bat foram executados.
pause
