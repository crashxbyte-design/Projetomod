reg.exe ADD HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer /v SmartScreenEnabled /t REG_SZ /d off /f

reg.exe ADD HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppContainer\Storage\microsoft.microsoftedge_8wekyb3d8bbwe\MicrosoftEdge\PhishingFilter /v EnabledV9 /t REG_DWORD /d 0 /f

reg.exe ADD HKCU\Software\Microsoft\Windows\CurrentVersion\AppHost /v EnableWebContentEvaluation /t REG_DWORD /d 0 /f
