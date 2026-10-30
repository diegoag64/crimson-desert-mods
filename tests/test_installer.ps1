Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '..\scripts\GridFiles.psm1') -Force
$root = Join-Path $PSScriptRoot ('..\build\installer-publication-' + [Guid]::NewGuid().ToString('N'))
$game = Join-Path $root 'game'
$package = Join-Path $root 'package'
$previous = Join-Path $root 'previous'
$backup = Join-Path $root 'rollback'
foreach ($dir in @('game\bin64','game\meta','game\0012','package','previous')) { [IO.Directory]::CreateDirectory((Join-Path $root $dir)) | Out-Null }
foreach ($file in @('bin64\CrimsonDesert.exe','meta\0.papgt','0012\0.pamt')) { [IO.File]::WriteAllText((Join-Path $game $file), 'synthetic game input ' + $file) }
foreach ($name in @('NativeGrid.asi','winmm.dll','winmm.ini')) {
    [IO.File]::WriteAllText((Join-Path $package $name), 'synthetic new ' + $name)
    [IO.File]::WriteAllText((Join-Path $previous $name), 'synthetic old ' + $name)
}
function New-Manifest([string]$Folder) {
    [pscustomobject]@{
        exe_sha256=(Get-GridHash (Join-Path $game 'bin64\CrimsonDesert.exe'))
        master_sha256=(Get-GridHash (Join-Path $game 'meta\0.papgt'))
        pamt_sha256=(Get-GridHash (Join-Path $game '0012\0.pamt'))
        files=@(@('NativeGrid.asi','winmm.dll','winmm.ini') | ForEach-Object { [pscustomobject]@{name=$_; sha256=(Get-GridHash (Join-Path $Folder $_))} })
    }
}
$manifest = New-Manifest $package
$prior = New-Manifest $previous
$options = @{Game=$game; Package=$package; Manifest=$manifest; BackupRoot=$backup; Running={ $false }}
function Assert-Throws([scriptblock]$Code, [string]$Message) {
    $threw = $false
    try { & $Code | Out-Null } catch { $threw = $true }
    if (-not $threw) { throw "Expected refusal: $Message" }
    Write-Output "PASS: $Message"
}
$runningOptions = $options.Clone(); $runningOptions.Running = { $true }
Assert-Throws { Invoke-GridChange -Action Install @runningOptions } 'running game refuses install'
Invoke-GridChange -Action Verify @options
if (Test-Path -LiteralPath $backup) { throw 'Verify created backup files.' }
Invoke-GridChange -Action Install @options
foreach ($file in $manifest.files) { if ((Get-GridHash (Join-Path $game ('bin64\' + $file.name))) -ne $file.sha256) { throw 'Install did not match package.' } }
Write-Output 'PASS: fresh install and all owned hashes'
[IO.File]::WriteAllText((Join-Path $game 'bin64\NativeGrid.asi'), 'unowned change')
Assert-Throws { Invoke-GridChange -Action Uninstall @options } 'changed installed file refuses uninstall'
[IO.File]::WriteAllBytes((Join-Path $game 'bin64\NativeGrid.asi'), [IO.File]::ReadAllBytes((Join-Path $package 'NativeGrid.asi')))
Invoke-GridChange -Action Uninstall @options
foreach ($file in $manifest.files) { if (Test-Path -LiteralPath (Join-Path $game ('bin64\' + $file.name))) { throw 'Uninstall left owned file.' } }
Write-Output 'PASS: uninstall preserves rollback and removes owned files'
foreach ($file in $prior.files) { [IO.File]::Copy((Join-Path $previous $file.name), (Join-Path $game ('bin64\' + $file.name))) }
Assert-Throws { Invoke-GridChange -Action Install @options } 'upgrade requires verified previous package'
Invoke-GridChange -Action Install @options -PreviousPackage $previous -PreviousManifest $prior
$copies = @(Get-ChildItem -LiteralPath $backup -Recurse -File -Filter 'NativeGrid.asi' | Where-Object { (Get-GridHash $_.FullName) -eq $prior.files[0].sha256 })
if (-not $copies.Count) { throw 'Upgrade lost previous rollback copy.' }
Write-Output 'PASS: verified upgrade preserves previous bytes'
$rollbackOptions = $options.Clone(); $rollbackOptions.Package = $previous; $rollbackOptions.Manifest = $prior
Invoke-GridChange -Action Install @rollbackOptions -PreviousPackage $package -PreviousManifest $manifest
if ((Get-GridHash (Join-Path $game 'bin64\NativeGrid.asi')) -ne $prior.files[0].sha256) { throw 'Rollback did not restore previous bytes.' }
Write-Output 'PASS: explicit downgrade restores previous package'
[IO.File]::WriteAllText((Join-Path $game '0012\0.pamt'), 'changed index')
Assert-Throws { Invoke-GridChange -Action Install @options -PreviousPackage $previous -PreviousManifest $prior } 'changed game index refuses mutation'
Write-Output "Synthetic installer fixtures retained at $root"
