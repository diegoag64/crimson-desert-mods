param(
    [ValidateSet('Verify','Install','Uninstall')][string]$Action = 'Verify',
    [Parameter(Mandatory=$true)][string]$Game,
    [Parameter(Mandatory=$true)][string]$Package,
    [string]$PreviousPackage,
    [string]$BackupRoot
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'GridFiles.psm1') -Force
$Game = (Resolve-Path -LiteralPath $Game).Path
$Package = (Resolve-Path -LiteralPath $Package).Path
$supports = @((Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\nativegrid\supported_build.json') -Raw | ConvertFrom-Json))
$supports += @(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot '..\nativegrid\builds') -Filter '*.json' -File | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json })
$manifest = Get-Content -LiteralPath (Join-Path $Package 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.schema -ne 1 -or $manifest.revision -notin @(5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20) -or $manifest.fixture_tests_passed -lt 6 -or -not $manifest.variable_length_resources) { throw 'Unsupported or untested package.' }
$supportedMatches = @($supports | Where-Object exe_sha256 -eq $manifest.exe_sha256)
if ($supportedMatches.Count -ne 1) { throw 'Unknown or ambiguous supported game build.' }
$support = $supportedMatches[0]
foreach ($key in @('exe_sha256','master_sha256','pamt_sha256')) {
    if ($manifest.$key -ne $support.$key) { throw "Package is not pinned to the supported game build: $key" }
}
if ($manifest.revision -in @(15,16,17,18,19,20)) {
    if ($manifest.fixture_tests_passed -lt 7) { throw 'Requirement-label package needs the shrinking-buffer fixture.' }
    if (-not $manifest.experimental_shop -or -not $support.PSObject.Properties['shop_requirements'] -or
        -not $manifest.PSObject.Properties['extra_indexes']) { throw 'Missing requirement-label compatibility pins.' }
    $indexes = @($manifest.extra_indexes.PSObject.Properties)
    if ($indexes.Count -ne 1 -or $indexes[0].Name -cne $support.shop_requirements.index_path -or
        $indexes[0].Value -cne $support.shop_requirements.index_sha256) { throw 'Localization index pin differs from supported build.' }
}
$prior = $null
if ($PreviousPackage) {
    $PreviousPackage = (Resolve-Path -LiteralPath $PreviousPackage).Path
    $prior = Get-Content -LiteralPath (Join-Path $PreviousPackage 'manifest.json') -Raw | ConvertFrom-Json
}
if (-not $BackupRoot) { $BackupRoot = Join-Path (Split-Path -Parent $Package) 'rollback' }
Invoke-GridChange -Action $Action -Game $Game -Package $Package -Manifest $manifest -PreviousPackage $PreviousPackage -PreviousManifest $prior -BackupRoot $BackupRoot
