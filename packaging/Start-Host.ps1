param([int]$Port = 0)
$ErrorActionPreference = 'Stop'
try {
    $runtimeDirectory = Join-Path $PSScriptRoot '.runtime'
    $statePath = Join-Path $runtimeDirectory 'server.json'
    $scriptPath = Join-Path $PSScriptRoot 'server.py'
    $exePath = Join-Path $PSScriptRoot 'GoldHEN-Server.exe'
    $packaged = Test-Path -LiteralPath $exePath
    $state = $null
    if (Test-Path -LiteralPath $statePath) {
        try { $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json } catch { }
    }
    if ($Port -eq 0) {
        $settings = Join-Path $PSScriptRoot 'settings.json'
        if (Test-Path -LiteralPath $settings) { $Port = [int]((Get-Content -LiteralPath $settings -Raw | ConvertFrom-Json).port) }
        else { $Port = 8088 }
    }
    if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Choose a port between 1024 and 65535.' }
    $health = $null
    try { $health = Invoke-RestMethod "http://127.0.0.1:$Port/__health" -TimeoutSec 2 } catch { }
    if ($health.app -eq 'goldhen-local') {
        $existing = Get-CimInstance Win32_Process -Filter "ProcessId = $([int]$health.pid)"
        $matches = $false
        if ($packaged) { $matches = $existing.ExecutablePath -eq $exePath }
        elseif ($existing.CommandLine) { $matches = $existing.CommandLine.IndexOf(('"' + $scriptPath + '"'), [StringComparison]::OrdinalIgnoreCase) -ge 0 }
        # Elevated processes may hide metadata. Preserve only a matching saved target/PID.
        if (-not $matches -and $state.pid -eq $health.pid) {
            $matches = ($state.server -eq $scriptPath -and -not $packaged) -or ($state.executable -eq $exePath -and $packaged)
        }
        if (-not $matches) { throw "Port $Port belongs to another host. Stop that copy or use a different port." }
        Write-Host 'GoldHEN is already running.'
        $serverPid = [int]$health.pid
    } else {
        if ($state -and $state.port -ne $Port) {
            $previous = $null
            try { $previous = Invoke-RestMethod "http://127.0.0.1:$($state.port)/__health" -TimeoutSec 1 } catch { }
            if ($previous.app -eq 'goldhen-local' -and $previous.pid -eq $state.pid) {
                throw "This copy is already running on port $($state.port). Stop it before changing ports."
            }
        }
        New-Item -ItemType Directory -Force -Path $runtimeDirectory | Out-Null
        if ($packaged) {
            $program = $exePath
            $arguments = @('--port', $Port)
            & $program --check
        } else {
            $program = (Get-Command python -ErrorAction Stop).Source
            $arguments = @(('"' + $scriptPath + '"'), '--port', $Port)
            & $program $scriptPath --check
        }
        if ($LASTEXITCODE -ne 0) { throw 'File verification failed. See the message above; no server was started.' }
        $process = Start-Process -FilePath $program -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDirectory 'server.log') -RedirectStandardError (Join-Path $runtimeDirectory 'requests.log') -PassThru
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            Start-Sleep -Milliseconds 200
            $process.Refresh()
            if ($process.HasExited) {
                $detail = (Get-Content -LiteralPath (Join-Path $runtimeDirectory 'requests.log') -Tail 3 -ErrorAction SilentlyContinue) -join ' '
                throw "Server failed to start on port $Port. $detail"
            }
            try { $health = Invoke-RestMethod "http://127.0.0.1:$Port/__health" -TimeoutSec 1 } catch { continue }
            if ($health.app -eq 'goldhen-local' -and $health.pid -eq $process.Id) { break }
        }
        if ($health.pid -ne $process.Id) {
            Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
            throw 'The server did not become ready. See .runtime\requests.log.'
        }
        $serverPid = $process.Id
    }
    New-Item -ItemType Directory -Force -Path $runtimeDirectory | Out-Null
    $record = @{pid=$serverPid; port=$Port}
    if ($packaged) { $record.executable = $exePath } else { $record.server = $scriptPath }
    $running = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
    if ($running -and $running.StartTime) { $record.startedUtc = $running.StartTime.ToUniversalTime().ToString('o') }
    $record | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
    $addresses = @("This PC: http://localhost:$Port/g2all/")
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' -and $_.AddressState -eq 'Preferred' } |
        ForEach-Object { $addresses += "PS4 network ($($_.InterfaceAlias)): http://$($_.IPAddress):$Port/g2all/" }
    $addresses | ForEach-Object { Write-Host $_ }
    $addresses | Set-Content -LiteralPath (Join-Path $runtimeDirectory 'addresses.txt') -Encoding UTF8
    Write-Host 'The host runs in the background. Use Stop-Host.cmd to stop it.'
    exit 0
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
