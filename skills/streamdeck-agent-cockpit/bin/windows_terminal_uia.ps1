[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$TabTitle
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class AgentCockpitWindowApi {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
'@

$processes = Get-Process -Name 'WindowsTerminal' -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 }

foreach ($process in $processes) {
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
    if ($null -eq $root) { continue }

    $condition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::TabItem
    )
    $items = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
    foreach ($item in $items) {
        if ($item.Current.Name -cne $TabTitle) { continue }
        $pattern = $item.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
        $pattern.Select()
        [AgentCockpitWindowApi]::ShowWindow($process.MainWindowHandle, 9) | Out-Null
        [AgentCockpitWindowApi]::SetForegroundWindow($process.MainWindowHandle) | Out-Null
        Write-Output "focused"
        exit 0
    }
}

Write-Error "No Windows Terminal tab matched the exact title: $TabTitle"
exit 3
