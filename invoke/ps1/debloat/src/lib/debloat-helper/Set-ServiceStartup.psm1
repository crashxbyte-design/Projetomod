Import-Module -DisableNameChecking "$PSScriptRoot\..\Title-Templates.psm1"

function Set-ServiceStartup() {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [ValidateSet('Automatic', 'Boot', 'Disabled', 'Manual', 'System')]
        [String]      $State,
        [Parameter(Mandatory = $true)]
        [String[]]    $Services,
        [String[]]    $Filter
    )

    Begin {
        $Script:SecurityFilterOnEnable = @("RemoteAccess", "RemoteRegistry")
        $Script:CriticalServices = @(
            "WinDefend",          # Windows Defender
            "WdNisSvc",            # Windows Defender Network Inspection Service
            "Sense",               # Windows Defender Advanced Threat Protection Service
            "wuauserv",            # Windows Update
            "UsoSvc",              # Update Orchestrator Service
            "WaaSMedicSvc",        # Windows Update Medic Service
            "AppXSvc",             # Microsoft Store Install Service
            "InstallService"       # Microsoft Store Install Service
        )
        $Script:TweakType = "Service"
    }

    Process {
        ForEach ($Service in $Services) {
            If (!(Get-Service $Service -ErrorAction SilentlyContinue)) {
                Write-Status -Types "?", $TweakType -Status "The `"$Service`" service was not found." -Warning
                Continue
            }

            # Verifica se o serviço é crítico e impede a desabilitação
            If ($State -eq 'Disabled' -and ($CriticalServices -contains $Service)) {
                Write-Status -Types "?", $TweakType -Status "The $Service service is critical and will not be disabled." -Warning
                Continue
            }

            If (($Service -in $SecurityFilterOnEnable) -and (($State -eq 'Automatic') -or ($State -eq 'Manual'))) {
                Write-Status -Types "?", $TweakType -Status "Skipping $Service ($((Get-Service $Service).DisplayName)) to avoid a security vulnerability..." -Warning
                Continue
            }

            If ($Service -in $Filter) {
                Write-Status -Types "?", $TweakType -Status "The $Service ($((Get-Service $Service).DisplayName)) will be skipped as set on Filter..." -Warning
                Continue
            }

            Write-Status -Types "@", $TweakType -Status "Setting $Service ($((Get-Service $Service).DisplayName)) as '$State' on Startup..."
            Get-Service -Name "$Service" -ErrorAction SilentlyContinue | Set-Service -StartupType $State
        }
    }
}