param([switch]$Quiet)
$ErrorActionPreference = 'Stop'
$installRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$recordPath = Join-Path $installRoot 'installation.json'
if (-not (Test-Path -LiteralPath $recordPath)) { throw 'This is a portable folder. Stop the host, then remove the folder manually.' }
$record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
if ($record.app -ne 'GoldHENLocalHost' -or $record.directory -ne $installRoot) { throw 'Installation identity does not match this folder.' }
if (-not $Quiet) {
    Write-Host 'If you enabled network access, run Remove Network Access before uninstalling.'
    if ((Read-Host 'Remove GoldHEN Local Host? Type YES') -cne 'YES') { exit 0 }
}
& (Join-Path $installRoot 'Stop-Host.ps1')
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw 'Could not stop the host.' }
$shell = New-Object -ComObject WScript.Shell
$group = Join-Path ([Environment]::GetFolderPath('Programs')) 'GoldHEN Local Host'
$candidates = @()
if (Test-Path -LiteralPath $group) { $candidates += Get-ChildItem -LiteralPath $group -Filter '*.lnk' }
$desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Start GoldHEN Host.lnk'
if (Test-Path -LiteralPath $desktopLink) { $candidates += Get-Item -LiteralPath $desktopLink }
foreach ($link in $candidates) {
    $target = $shell.CreateShortcut($link.FullName).TargetPath
    if ($target.StartsWith($installRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $link.FullName
    }
}
if ((Test-Path -LiteralPath $group) -and @(Get-ChildItem -LiteralPath $group -Force).Count -eq 0) { Remove-Item -LiteralPath $group }
$registry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\GoldHENLocalHost'
$installed = Get-ItemProperty -LiteralPath $registry -ErrorAction SilentlyContinue
if ($installed.InstallLocation -eq $installRoot) { Remove-Item -LiteralPath $registry }
# Validate every path before removing any package file. Never recursively delete a supplied path.
$targets = @()
foreach ($name in $record.files) {
    $target = [IO.Path]::GetFullPath((Join-Path $installRoot $name))
    if (-not $target.StartsWith($installRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid path in installation inventory.' }
    if ($name -eq 'settings.json') { continue }
    $targets += $target
}
foreach ($target in $targets) { if (Test-Path -LiteralPath $target -PathType Leaf) { Remove-Item -LiteralPath $target } }
Remove-Item -LiteralPath $recordPath
$directories = Get-ChildItem -LiteralPath $installRoot -Directory -Recurse -Force | Sort-Object { $_.FullName.Length } -Descending
foreach ($directory in $directories) {
    if (@(Get-ChildItem -LiteralPath $directory.FullName -Force).Count -eq 0) { Remove-Item -LiteralPath $directory.FullName }
}
Write-Host 'GoldHEN Local Host removed. Custom settings and logs were retained.'
