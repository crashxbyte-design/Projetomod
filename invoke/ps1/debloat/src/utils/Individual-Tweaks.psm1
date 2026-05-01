Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\Get-HardwareInfo.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\New-Shortcut.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\Title-Templates.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\debloat-helper\Remove-ItemVerified.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\debloat-helper\Remove-ItemPropertyVerified.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\debloat-helper\Set-CapabilityState.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\debloat-helper\Set-ItemPropertyVerified.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\debloat-helper\Set-OptionalFeatureState.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\debloat-helper\Set-ScheduledTaskState.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\debloat-helper\Set-ServiceStartup.psm1"
Import-Module -DisableNameChecking "$PSScriptRoot\..\lib\package-managers\Manage-Software.psm1"

$MouseAccelerationCode = @'
[DllImport("user32.dll", EntryPoint = "SystemParametersInfo")]
 public static extern bool SystemParametersInfo(uint uiAction, uint uiParam, int[] pvParam, uint fWinIni);
'@

Add-Type $MouseAccelerationCode -name Win32 -NameSpace System

$DesktopPath = [Environment]::GetFolderPath("Desktop");
$PathToCUClipboard = "HKCU:\Software\Microsoft\Clipboard"
$PathToCUOnlineSpeech = "HKCU:\SOFTWARE\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy"
$PathToCUPoliciesCloudContent = "HKCU:\SOFTWARE\Policies\Microsoft\Windows\CloudContent"
$PathToCUThemes = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
$PathToCUXboxGameBar = "HKCU:\Software\Microsoft\GameBar"
$PathToCUMouse = "HKCU:\Control Panel\Mouse"
$PathToCUNewsAndInterest = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Feeds"
$PathToLMPoliciesCloudContent = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent"
$PathToLMPoliciesAppGameDVR = "HKLM:\SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR"
$PathToLMPoliciesCortana = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search"
$PathToLMPoliciesGameDVR = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\GameDVR"
$PathToLMPoliciesLocationAndSensors = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors"
$PathToLMPoliciesNewsAndInterest = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds"
$PathToLMPoliciesSystem = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System"
$PathToLMPoliciesWindowsUpdate = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"

# Funções que NÃO devem ser removidas ou alteradas:

function Enable-DarkTheme() {
    Write-Status -Types "+", "Personal" -Status "Enabling Dark Theme..."
    Set-ItemPropertyVerified -Path "$PathToCUThemes" -Name "AppsUseLightTheme" -Type DWord -Value 0
    Set-ItemPropertyVerified -Path "$PathToCUThemes" -Name "SystemUsesLightTheme" -Type DWord -Value 0
}

function Enable-HyperV() {
    Write-Status -Types "+", "Performance" -Status "Enabling Hyper-V..."
    Set-OptionalFeatureState -State 'Enabled' -OptionalFeatures @("Microsoft-Hyper-V-All")
}

function Enable-WindowsUpdate() {
    Write-Status -Types "*", "WU" -Status "Enabling Automatic Download and Installation of Windows Updates..."
    Remove-ItemPropertyVerified -Path "$PathToLMPoliciesWindowsUpdate" -Name "AUOptions"
    Remove-ItemPropertyVerified -Path "$PathToLMPoliciesWindowsUpdate" -Name "NoAutoUpdate"
    Remove-ItemPropertyVerified -Path "$PathToLMPoliciesWindowsUpdate" -Name "ScheduledInstallDay"
    Remove-ItemPropertyVerified -Path "$PathToLMPoliciesWindowsUpdate" -Name "ScheduledInstallTime"
}

function Enable-WindowsDefender() {
    Write-Status -Types "+", "Security" -Status "Enabling Windows Defender..."
    Set-ServiceStartup -State 'Automatic' -Services "WinDefend"
    Start-Service "WinDefend"
}

function Enable-MicrosoftStore() {
    Write-Status -Types "+", "App" -Status "Enabling Microsoft Store..."
    Set-ItemPropertyVerified -Path "HKLM:\SOFTWARE\Policies\Microsoft\WindowsStore" -Name "RemoveWindowsStore" -Type DWord -Value 0
}

# Funções que devem ser removidas ou modificadas:

# Removida a função Disable-DarkTheme
# Removida a função Disable-HyperV
# Removida a função Disable-WindowsUpdate
# Removida a função Disable-WindowsDefender
# Removida a função Disable-MicrosoftStore

# Outras funções que não interferem nas funcionalidades críticas:

function Disable-ClipboardHistory() {
    Write-Status -Types "-", "Privacy" -Status "Disabling Clipboard History (requires reboot!)..."
    Remove-ItemPropertyVerified -Path "$PathToLMPoliciesSystem" -Name "AllowClipboardHistory"
    Remove-ItemPropertyVerified -Path "$PathToCUClipboard" -Name "EnableClipboardHistory"
}

function Enable-ClipboardHistory() {
    Write-Status -Types "*", "Privacy" -Status "Enabling Clipboard History (requires reboot!)..."
    Set-ItemPropertyVerified -Path "$PathToLMPoliciesSystem" -Name "AllowClipboardHistory" -Type DWord -Value 1
    Set-ItemPropertyVerified -Path "$PathToCUClipboard" -Name "EnableClipboardHistory" -Type DWord -Value 1
}

function Disable-Cortana() {
    Write-Status -Types "-", "Privacy" -Status "Disabling Cortana..."
    Set-ItemPropertyVerified -Path "$PathToLMPoliciesCortana" -Name "AllowCortana" -Type DWord -Value 0
    Set-ItemPropertyVerified -Path "$PathToLMPoliciesCortana" -Name "AllowCloudSearch" -Type DWord -Value 0
    Set-ItemPropertyVerified -Path "$PathToLMPoliciesCortana" -Name "ConnectedSearchUseWeb" -Type DWord -Value 0
    Set-ItemPropertyVerified -Path "$PathToLMPoliciesCortana" -Name "DisableWebSearch" -Type DWord -Value 1
}

function Enable-Cortana() {
    Write-Status -Types "*", "Privacy" -Status "Enabling Cortana..."
    Set-ItemPropertyVerified -Path "$PathToLMPoliciesCortana" -Name "AllowCortana" -Type DWord -Value 1
    Set-ItemPropertyVerified -Path "$PathToLMPoliciesCortana" -Name "AllowCloudSearch" -Type DWord -Value 1
    Set-ItemPropertyVerified -Path "$PathToLMPoliciesCortana" -Name "ConnectedSearchUseWeb" -Type DWord -Value 1
    Set-ItemPropertyVerified -Path "$PathToLMPoliciesCortana" -Name "DisableWebSearch" -Type DWord -Value 0
}