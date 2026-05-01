@echo off
:: Habilita Descoberta de Rede
netsh advfirewall firewall set rule group="Network Discovery" new enable=Yes

:: Ajustes de TCP/IP
netsh int tcp set heuristics disabled
netsh int tcp set supp internet congestionprovider=ctcp
netsh int tcp set global rss=enabled
netsh int tcp set global chimney=enabled
netsh int tcp set global ecncapability=enabled
netsh int tcp set global timestamps=enabled  :: Mantém timestamps habilitado
netsh int tcp set global initialRto=2000
netsh int tcp set global rsc=disabled
netsh int tcp set global nonsackttresiliency=disabled
netsh int tcp set global MaxSynRetransmissions=2
netsh int tcp set global fastopen=enabled
netsh int tcp set global fastopenfallback=enabled
netsh int tcp set global pacingprofile=off
netsh int tcp set global hystart=disabled
netsh int tcp set global dca=enabled
netsh int tcp set global netdma=enabled
netsh int 6to4 set state state=enabled
netsh int udp set global uro=enabled
netsh winsock set autotuning on
netsh int tcp set supplemental template=custom icw=10
netsh interface teredo set state enterprise
netsh int tcp set security mpp=disabled
netsh int tcp set security profiles=disabled

:: Define MTU para interfaces de rede
netsh interface ipv4 set subinterface "Wi-Fi" mtu=1500 store=persistent
netsh interface ipv4 set subinterface Ethernet mtu=1500 store=persistent

:: Ajustes de registro para interfaces de rede
for /f %%r in ('reg query "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces" /f "1" /d /s^|Findstr HKEY_') do (
    reg add %%r /v "NonBestEffortLimit" /t reg_DWORD /d "0" /f
    reg add %%r /v "DeadGWDetectDefault" /t reg_DWORD /d "1" /f
    reg add %%r /v "PerformRouterDiscovery" /t reg_DWORD /d "1" /f
    reg add %%r /v "TCPNoDelay" /t reg_DWORD /d "1" /f
    reg add %%r /v "TcpAckFrequency" /t reg_DWORD /d "1" /f
    reg add %%r /v "TcpInitialRTT" /t reg_DWORD /d "2" /f
    reg add %%r /v "TcpDelAckTicks" /t reg_DWORD /d "0" /f
    reg add %%r /v "MTU" /t reg_DWORD /d "1500" /f
    reg add %%r /v "UseZeroBroadcast" /t reg_DWORD /d "0" /f
)

echo Configurações de rede aplicadas com sucesso.