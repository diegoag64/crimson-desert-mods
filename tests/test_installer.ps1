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
# Additional archive inputs must be checked before any owned file changes.
[IO.Directory]::CreateDirectory((Join-Path $game '0020')) | Out-Null
$extraPath = Join-Path $game '0020\0.pamt'
[IO.File]::WriteAllText($extraPath, 'synthetic localization index')
$manifest | Add-Member -NotePropertyName extra_indexes -NotePropertyValue ([pscustomobject]@{'0020/0.pamt'=(Get-GridHash $extraPath)})
Invoke-GridChange -Action Verify @options -PreviousPackage $previous -PreviousManifest $prior
[IO.File]::WriteAllText($extraPath, 'changed localization index')
Assert-Throws { Invoke-GridChange -Action Install @options -PreviousPackage $previous -PreviousManifest $prior } 'changed localization index refuses mutation'
$manifest.extra_indexes = [pscustomobject]@{'../0.pamt'=('a' * 64)}
Assert-Throws { Invoke-GridChange -Action Verify @options -PreviousPackage $previous -PreviousManifest $prior } 'unsafe extra index path refused'
$manifest.PSObject.Properties.Remove('extra_indexes')
[IO.File]::WriteAllText((Join-Path $game '0012\0.pamt'), 'changed index')
Assert-Throws { Invoke-GridChange -Action Install @options -PreviousPackage $previous -PreviousManifest $prior } 'changed game index refuses mutation'
Write-Output "Synthetic installer fixtures retained at $root"

# Exercise the public revision gate using isolated support metadata and fake game files.
$wrapper = Join-Path $root 'wrapper'
foreach ($dir in @('scripts','nativegrid','nativegrid\builds')) { [IO.Directory]::CreateDirectory((Join-Path $wrapper $dir)) | Out-Null }
foreach ($file in @('NativeGrid.ps1','GridFiles.psm1')) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot ('..\scripts\' + $file)) -Destination (Join-Path $wrapper ('scripts\' + $file)) }
$support = Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\nativegrid\builds\26329202.json') -Raw | ConvertFrom-Json
$support.exe_sha256 = Get-GridHash (Join-Path $game 'bin64\CrimsonDesert.exe')
$support.master_sha256 = Get-GridHash (Join-Path $game 'meta\0.papgt')
$support.pamt_sha256 = Get-GridHash (Join-Path $game '0012\0.pamt')
$support.shop_requirements.index_sha256 = Get-GridHash $extraPath
$support | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $wrapper 'nativegrid\supported_build.json')
$candidate = New-Manifest $package
$candidate | Add-Member -NotePropertyMembers @{
    schema=1; revision=26; fixture_tests_passed=8; variable_length_resources=$true
    experimental_shop=$true; experimental_refinement=$true
    refinement_runtime=$support.refinement_runtime
    extra_indexes=[pscustomobject]@{'0020/0.pamt'=$support.shop_requirements.index_sha256}
    payloads=@($support.refinement_revisions.'26'.PSObject.Properties | ForEach-Object {
        [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
    })
}
$prior | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $previous 'manifest.json')
function Invoke-WrapperVerify {
    $candidate | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $package 'manifest.json')
    & (Join-Path $wrapper 'scripts\NativeGrid.ps1') -Action Verify -Game $game -Package $package -PreviousPackage $previous
}
Invoke-WrapperVerify
Write-Output 'PASS: revision 26 public wrapper accepts exact runtime and asset pins'
$candidate.refinement_runtime = ($support.refinement_runtime | ConvertTo-Json -Depth 10 | ConvertFrom-Json)
$candidate.refinement_runtime.state_prefix = '00' * 24
Assert-Throws { Invoke-WrapperVerify } 'changed refinement method pin refused'
$candidate.refinement_runtime = ($support.refinement_runtime | ConvertTo-Json -Depth 10 | ConvertFrom-Json)
$candidate.refinement_runtime.root_vtable.rva++
Assert-Throws { Invoke-WrapperVerify } 'changed refinement owner pin refused'
$candidate.refinement_runtime = $support.refinement_runtime
$candidate.payloads[2].replacement_sha256 = '0' * 64
Assert-Throws { Invoke-WrapperVerify } 'changed refinement CSS pin refused'
$candidate.revision = 27
$candidate.refinement_runtime = $support.refinement_runtime_revisions.'27'
$candidate.payloads = @($support.refinement_revisions.'27'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
Invoke-WrapperVerify
Write-Output 'PASS: revision 27 accepts class-refresh hook and original refinement owner pins'
foreach ($key in @('refresh','add_class','sort_classes')) {
    $candidate.refinement_runtime = ($support.refinement_runtime_revisions.'27' | ConvertTo-Json -Depth 10 | ConvertFrom-Json)
    $candidate.refinement_runtime.methods.$key.prefix = '00' * 24
    Assert-Throws { Invoke-WrapperVerify } "changed refinement $key method refused"
}
$candidate.refinement_runtime = ($support.refinement_runtime_revisions.'27' | ConvertTo-Json -Depth 10 | ConvertFrom-Json)
$candidate.refinement_runtime.hidden_atom_rva++
Assert-Throws { Invoke-WrapperVerify } 'changed hidden-class atom refused'
$candidate.revision = 25
$candidate.fixture_tests_passed = 7
$candidate.payloads = @($support.refinement_assets.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
$candidate.PSObject.Properties.Remove('refinement_runtime')
Invoke-WrapperVerify
Write-Output 'PASS: revision 25 rollback still accepts its original asset pins without new hook'
