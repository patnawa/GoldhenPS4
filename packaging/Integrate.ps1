param([Parameter(Mandatory=$true)][string]$InstallDirectory, [switch]$Desktop)
$ErrorActionPreference = 'Stop'
$group = Join-Path ([Environment]::GetFolderPath('Programs')) 'GoldHEN Local Host'
New-Item -ItemType Directory -Path $group -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
$links = @{
    'Start GoldHEN Host' = 'Start-Host.cmd'; 'Stop GoldHEN Host' = 'Stop-Host.cmd';
    'Allow PS4 Network Access' = 'Allow-PS4-Network.cmd'; 'Remove Network Access' = 'Remove-Network-Access.cmd';
    'Check Files' = 'Check-Files.cmd'; 'Read Me' = 'README.txt'; 'Uninstall GoldHEN Local Host' = 'Uninstall.cmd'
}
foreach ($name in $links.Keys) {
    $shortcut = $shell.CreateShortcut((Join-Path $group ($name + '.lnk')))
    $shortcut.TargetPath = Join-Path $InstallDirectory $links[$name]
    $shortcut.WorkingDirectory = $InstallDirectory
    $shortcut.IconLocation = Join-Path $InstallDirectory 'GoldHEN-Server.exe'
    $shortcut.Save()
}
if ($Desktop) {
    $shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Start GoldHEN Host.lnk'))
    $shortcut.TargetPath = Join-Path $InstallDirectory 'Start-Host.cmd'
    $shortcut.WorkingDirectory = $InstallDirectory
    $shortcut.IconLocation = Join-Path $InstallDirectory 'GoldHEN-Server.exe'
    $shortcut.Save()
}
