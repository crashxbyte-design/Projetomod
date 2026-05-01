:: DISABLING POWERSAVING by amit (versão corrigida)

:: Lista de funcionalidades de economia de energia a serem desabilitadas
set "power_settings=EnhancedPowerManagementEnabled AllowIdleIrpInD3 EnableSelectiveSuspend DeviceSelectiveSuspended SelectiveSuspendEnabled SelectiveSuspendOn EnumerationRetryCount ExtPropDescSemaphore WaitWakeEnabled D3ColdSupported WdfDirectedPowerTransitionEnable EnableIdlePowerManagement IdleInWorkingState"

:: Percorre o registro e desabilita as funcionalidades de economia de energia
for %%a in (%power_settings%) do (
    for /f "delims=" %%b in ('reg query "HKLM\SYSTEM\CurrentControlSet\Enum" /s /f "%%a" ^| findstr "HKEY"') do (
        :: Verifica se o dispositivo não é um adaptador de rede
        echo %%b | findstr /i "USB" > NUL 2>&1
        if %errorlevel% equ 0 (
            reg.exe add "%%b" /v "%%a" /t REG_DWORD /d "0" /f > NUL 2>&1
        )
    )
)

echo Funcionalidades de economia de energia desabilitadas com sucesso (exceto adaptadores de rede).