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
if ($manifest.schema -ne 1 -or $manifest.revision -notin @(5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27) -or $manifest.fixture_tests_passed -lt 6 -or -not $manifest.variable_length_resources) { throw 'Unsupported or untested package.' }
$supportedMatches = @($supports | Where-Object exe_sha256 -eq $manifest.exe_sha256)
if ($supportedMatches.Count -ne 1) { throw 'Unknown or ambiguous supported game build.' }
$support = $supportedMatches[0]
foreach ($key in @('exe_sha256','master_sha256','pamt_sha256')) {
    if ($manifest.$key -ne $support.$key) { throw "Package is not pinned to the supported game build: $key" }
}
if ($manifest.revision -in @(15,16,17,18,19,20,21,22,23,24,25,26,27)) {
    if ($manifest.fixture_tests_passed -lt 7) { throw 'Requirement-label package needs the shrinking-buffer fixture.' }
    if (-not $manifest.experimental_shop -or -not $support.PSObject.Properties['shop_requirements'] -or
        -not $manifest.PSObject.Properties['extra_indexes']) { throw 'Missing requirement-label compatibility pins.' }
    $indexes = @($manifest.extra_indexes.PSObject.Properties)
    if ($indexes.Count -ne 1 -or $indexes[0].Name -cne $support.shop_requirements.index_path -or
        $indexes[0].Value -cne $support.shop_requirements.index_sha256) { throw 'Localization index pin differs from supported build.' }
}
if ($manifest.revision -in @(25,26,27)) {
    if (-not $manifest.PSObject.Properties['experimental_refinement'] -or -not $manifest.experimental_refinement -or
        -not $support.PSObject.Properties['refinement_assets']) { throw 'Missing refinement compatibility pins.' }
    $refinementPins = $support.refinement_assets
    if ($manifest.revision -eq 26) {
        if ($manifest.fixture_tests_passed -lt 8 -or -not $manifest.PSObject.Properties['refinement_runtime'] -or
            -not $support.PSObject.Properties['refinement_revisions'] -or
            -not $support.refinement_revisions.PSObject.Properties['26']) { throw 'Missing tested refinement badge filter.' }
        $refinementPins = $support.refinement_revisions.'26'
        foreach ($key in @('state_rva','state_prefix')) {
            if ($manifest.refinement_runtime.$key -cne $support.refinement_runtime.$key) { throw "Refinement runtime pin mismatch: $key" }
        }
        foreach ($key in @('description_vtable','list_vtable','root_vtable')) {
            if ($manifest.refinement_runtime.$key.rva -ne $support.refinement_runtime.$key.rva -or
                $manifest.refinement_runtime.$key.type -cne $support.refinement_runtime.$key.type) { throw "Refinement owner pin mismatch: $key" }
        }
    }
    if ($manifest.revision -eq 27) {
        if ($manifest.fixture_tests_passed -lt 8 -or -not $manifest.PSObject.Properties['refinement_runtime'] -or
            -not $support.PSObject.Properties['refinement_runtime_revisions'] -or
            -not $support.refinement_revisions.PSObject.Properties['27']) { throw 'Missing tested refinement class filter.' }
        $refinementPins = $support.refinement_revisions.'27'
        $runtimePins = $support.refinement_runtime_revisions.'27'
        if ($manifest.refinement_runtime.hidden_atom_rva -ne $runtimePins.hidden_atom_rva) { throw 'Refinement hidden-class atom pin mismatch.' }
        foreach ($key in @('refresh','add_class','sort_classes')) {
            if ($manifest.refinement_runtime.methods.$key.rva -ne $runtimePins.methods.$key.rva -or
                $manifest.refinement_runtime.methods.$key.prefix -cne $runtimePins.methods.$key.prefix) { throw "Refinement method pin mismatch: $key" }
        }
        foreach ($key in @('description_vtable','list_vtable','root_vtable')) {
            if ($manifest.refinement_runtime.$key.rva -ne $runtimePins.$key.rva -or
                $manifest.refinement_runtime.$key.type -cne $runtimePins.$key.type) { throw "Refinement owner pin mismatch: $key" }
        }
    }
    foreach ($pin in $refinementPins.PSObject.Properties) {
        $found = @($manifest.payloads | Where-Object path -CEQ $pin.Name)
        if ($found.Count -ne 1 -or $found[0].original_sha256 -cne $pin.Value.original_sha256 -or
            $found[0].replacement_sha256 -cne $pin.Value.replacement_sha256 -or
            $found[0].size -ne $found[0].replacement_size) { throw "Refinement payload pin mismatch: $($pin.Name)" }
    }
}
$prior = $null
if ($PreviousPackage) {
    $PreviousPackage = (Resolve-Path -LiteralPath $PreviousPackage).Path
    $prior = Get-Content -LiteralPath (Join-Path $PreviousPackage 'manifest.json') -Raw | ConvertFrom-Json
}
if (-not $BackupRoot) { $BackupRoot = Join-Path (Split-Path -Parent $Package) 'rollback' }
Invoke-GridChange -Action $Action -Game $Game -Package $Package -Manifest $manifest -PreviousPackage $PreviousPackage -PreviousManifest $prior -BackupRoot $BackupRoot
