param([switch]$Remove, [switch]$Elevated)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    if ($Elevated) { throw 'Administrator rights are required for the firewall rule.' }
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'), '-Elevated')
    if ($Remove) { $arguments += '-Remove' }
    $process = Start-Process powershell.exe -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw 'Windows did not apply the firewall change.' }
    exit 0
}
$exe = Join-Path $PSScriptRoot 'GoldHEN-Server.exe'
$digest = [System.Security.Cryptography.SHA256]::Create()
$hash = [BitConverter]::ToString($digest.ComputeHash([Text.Encoding]::UTF8.GetBytes($exe.ToLowerInvariant()))).Replace('-', '').Substring(0, 16)
$rule = 'GoldHENLocal-' + $hash
if ($Remove) {
    Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Write-Host 'Removed this installation''s firewall rule.'
} else {
    $port = [int]((Get-Content -LiteralPath (Join-Path $PSScriptRoot 'settings.json') -Raw | ConvertFrom-Json).port)
    if ($port -lt 1024 -or $port -gt 65535) { throw 'Invalid port in settings.json.' }
    Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    New-NetFirewallRule -Name $rule -DisplayName 'GoldHEN Local Host (private LAN)' -Direction Inbound -Action Allow -Program $exe -Protocol TCP -LocalPort $port -Profile Private -RemoteAddress LocalSubnet | Out-Null
    Write-Host 'Allowed this host on Private networks for devices on the local subnet.'
    Write-Host 'Use a trusted home network marked Private in Windows network settings.'
}
