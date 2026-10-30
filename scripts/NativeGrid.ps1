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
$support = Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\nativegrid\supported_build.json') -Raw | ConvertFrom-Json
$manifest = Get-Content -LiteralPath (Join-Path $Package 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.schema -ne 1 -or $manifest.revision -ne 5 -or $manifest.fixture_tests_passed -lt 6 -or -not $manifest.variable_length_resources) { throw 'Unsupported or untested package.' }
foreach ($key in @('exe_sha256','master_sha256','pamt_sha256')) {
    if ($manifest.$key -ne $support.$key) { throw "Package is not pinned to the supported game build: $key" }
}
$prior = $null
if ($PreviousPackage) {
    $PreviousPackage = (Resolve-Path -LiteralPath $PreviousPackage).Path
    $prior = Get-Content -LiteralPath (Join-Path $PreviousPackage 'manifest.json') -Raw | ConvertFrom-Json
}
if (-not $BackupRoot) { $BackupRoot = Join-Path (Split-Path -Parent $Package) 'rollback' }
Invoke-GridChange -Action $Action -Game $Game -Package $Package -Manifest $manifest -PreviousPackage $PreviousPackage -PreviousManifest $prior -BackupRoot $BackupRoot
