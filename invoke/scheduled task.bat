@echo off
:: Script para desabilitar tarefas agendadas, exceto Microsoft Store, Windows Defender, Windows Update, luz noturna, HVCI e rede

:: Lista de tarefas que NÃO serão desabilitadas
set "excluded_tasks=Microsoft\Windows\Windows Defender Microsoft\Windows\WindowsUpdate Microsoft\Windows\UpdateOrchestrator Microsoft\XblGameSave Microsoft\Windows\WindowsColorSystem Microsoft\Windows\Display Microsoft\Windows\DeviceSetup Microsoft\Windows\StorageTiers Microsoft\Windows\StorageTiersManagement Microsoft\Windows\Hyper-V Microsoft\Windows\DeviceDirectoryClient Microsoft\Windows\NlaSvc Microsoft\Windows\NetTrace Microsoft\Windows\NetworkProfile Microsoft\Windows\WwanSvc Microsoft\Windows\WcmSvc"

:: Desabilita tarefas agendadas, exceto as excluídas
for /f "tokens=*" %%a in ('schtasks /query /fo list /v ^| findstr "TaskName:"') do (
    set "task=%%a"
    set "task=!task:TaskName: =!"
    set "skip_task=0"
    
    :: Verifica se a tarefa está na lista de exclusão
    for %%b in (%excluded_tasks%) do (
        echo !task! | findstr /i "%%b" >nul 2>&1
        if !errorlevel! equ 0 set "skip_task=1"
    )
    
    :: Desabilita a tarefa se não estiver na lista de exclusão
    if !skip_task! equ 0 (
        schtasks /change /tn "!task!" /disable >nul 2>&1
        echo Tarefa desabilitada: !task!
    ) else (
        echo Tarefa mantida: !task!
    )
)

echo Todas as tarefas foram processadas, exceto Microsoft Store, Windows Defender, Windows Update, luz noturna, HVCI e rede.