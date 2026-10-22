param([switch]$Elevated, [switch]$NoElevation)
$ErrorActionPreference = 'Stop'
function Invoke-ElevatedStop {
    if ($Elevated -or $NoElevation) { throw 'Windows is hiding this process or denying access. Administrator permission is required to stop it. Run Stop-Host.cmd as administrator once.' }
    Write-Host 'Windows needs administrator permission to stop the previously elevated host.'
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'), '-Elevated')
    try { $helper = Start-Process powershell.exe -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -PassThru -Wait }
    catch { throw 'Administrator permission was not granted. The host was left running. Run Stop-Host.cmd as administrator once.' }
    if ($helper.ExitCode -ne 0) { throw 'The administrator stop did not complete. Run Stop-Host.cmd as administrator to see the error.' }
    Write-Host 'GoldHEN host stopped.'
}
try {
    $statePath = Join-Path $PSScriptRoot '.runtime/server.json'
    if (-not (Test-Path -LiteralPath $statePath)) { Write-Host 'GoldHEN host is already stopped (no saved process).'; exit 0 }
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    $scriptPath = Join-Path $PSScriptRoot 'server.py'
    $exePath = Join-Path $PSScriptRoot 'GoldHEN-Server.exe'
    $packaged = $state.executable -eq $exePath
    if (-not $packaged -and $state.server -ne $scriptPath) { throw 'Saved server path does not match this folder. No process was stopped.' }
    if ([int]$state.pid -le 0) { throw 'Saved process ID is invalid.' }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$state.pid)"
    if (-not $process) {
        Remove-Item -LiteralPath $statePath
        Write-Host 'GoldHEN host is already stopped. Cleared its stale process record.'
        exit 0
    }
    if (($packaged -and -not $process.ExecutablePath) -or (-not $packaged -and -not $process.CommandLine)) {
        Invoke-ElevatedStop
        exit 0
    }
    if ($packaged) { $matches = $process.ExecutablePath -eq $exePath }
    else { $matches = $process.CommandLine.IndexOf(('"' + $scriptPath + '"'), [StringComparison]::OrdinalIgnoreCase) -ge 0 }
    if (-not $matches) { throw 'The saved process ID belongs to another command. It was left running.' }
    $running = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
    if ($state.startedUtc -and $running -and $running.StartTime.ToUniversalTime().ToString('o') -ne $state.startedUtc) {
        throw 'The saved process ID has been reused. No process was stopped.'
    }
    try { Stop-Process -Id $state.pid -ErrorAction Stop }
    catch {
        if (Get-Process -Id $state.pid -ErrorAction SilentlyContinue) { Invoke-ElevatedStop; exit 0 }
    }
    Wait-Process -Id $state.pid -Timeout 10 -ErrorAction SilentlyContinue
    $remaining = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
    if ($remaining -and -not $remaining.HasExited) { throw 'The host has not exited yet. Its process record was retained.' }
    Remove-Item -LiteralPath $statePath
    Write-Host 'GoldHEN host stopped.'
    exit 0
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
