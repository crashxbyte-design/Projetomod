Import-Module -DisableNameChecking "$PSScriptRoot\..\Title-Templates.psm1"

function Set-ScheduledTaskState() {
    [CmdletBinding()]
    param (
        [Parameter(Position = 0, Mandatory)]
        [ValidateSet('Disabled', 'Enabled')]
        [String] $State,
        [Parameter(Position = 1, Mandatory)]
        [String[]]  $ScheduledTasks,
        [Parameter(Position = 2)]
        [String[]]  $Filter
    )

    Begin {
        $Script:TweakType = "TaskScheduler"
        # Lista de tarefas críticas que não devem ser desabilitadas
        $Script:CriticalTasks = @(
            "*WindowsDefender*",
            "*MicrosoftStore*",
            "*WindowsUpdate*"
        )
    }

    Process {
        ForEach ($ScheduledTask in $ScheduledTasks) {
            If (!(Get-ScheduledTask -TaskName (Split-Path -Path $ScheduledTask -Leaf) -ErrorAction SilentlyContinue)) {
                Write-Status -Types "?", $TweakType -Status "The `"$ScheduledTask`" task was not found." -Warning
                Continue
            }

            # Verifica se a tarefa é crítica e impede a desabilitação
            If ($State -eq 'Disabled' -and ($CriticalTasks | Where-Object { $ScheduledTask -like $_ })) {
                Write-Status -Types "?", $TweakType -Status "The $ScheduledTask task is critical and will not be disabled." -Warning
                Continue
            }

            If ($ScheduledTask -in $Filter) {
                Write-Status -Types "?", $TweakType -Status "The $ScheduledTask ($((Get-ScheduledTask $ScheduledTask).TaskName)) will be skipped as set on Filter..." -Warning
                Continue
            }

            If ($State -eq 'Disabled') {
                Write-Status -Types "-", $TweakType -Status "Disabling the $ScheduledTask task..."
                Get-ScheduledTask -TaskName (Split-Path -Path $ScheduledTask -Leaf) | Where-Object State -Like "R*" | Disable-ScheduledTask # R* = Ready/Running
            } ElseIf ($State -eq 'Enabled') {
                Write-Status -Types "+", $TweakType -Status "Enabling the $ScheduledTask task..."
                Get-ScheduledTask -TaskName (Split-Path -Path $ScheduledTask -Leaf) | Where-Object State -Like "Disabled" | Enable-ScheduledTask
            }
        }
    }
}