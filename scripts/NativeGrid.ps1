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
if ($manifest.schema -ne 1 -or $manifest.revision -notin @(5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39) -or $manifest.fixture_tests_passed -lt 6 -or -not $manifest.variable_length_resources) { throw 'Unsupported or untested package.' }
$supportedMatches = @($supports | Where-Object exe_sha256 -eq $manifest.exe_sha256)
if ($supportedMatches.Count -ne 1) { throw 'Unknown or ambiguous supported game build.' }
$support = $supportedMatches[0]
foreach ($key in @('exe_sha256','master_sha256','pamt_sha256')) {
    if ($manifest.$key -ne $support.$key) { throw "Package is not pinned to the supported game build: $key" }
}
if ($manifest.revision -in @(15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39)) {
    if ($manifest.fixture_tests_passed -lt 7) { throw 'Requirement-label package needs the shrinking-buffer fixture.' }
    if (-not $manifest.experimental_shop -or -not $support.PSObject.Properties['shop_requirements'] -or
        -not $manifest.PSObject.Properties['extra_indexes']) { throw 'Missing requirement-label compatibility pins.' }
    $indexes = @($manifest.extra_indexes.PSObject.Properties)
    if ($indexes.Count -ne 1 -or $indexes[0].Name -cne $support.shop_requirements.index_path -or
        $indexes[0].Value -cne $support.shop_requirements.index_sha256) { throw 'Localization index pin differs from supported build.' }
}
if ($manifest.revision -in @(25,26,27,28,29,30,31,32,33,34,35,36,37,38,39)) {
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
    if ($manifest.revision -in @(27,28,29,30,31,32,33,34,35,36,37,38,39)) {
        $refinementRevision = if ($manifest.revision -in @(31,32,33,34,35,36,37,38,39)) { '30' } else { [string]$manifest.revision }
        if ($manifest.fixture_tests_passed -lt 8 -or -not $manifest.PSObject.Properties['refinement_runtime'] -or
            -not $support.PSObject.Properties['refinement_runtime_revisions'] -or
            -not $support.refinement_revisions.PSObject.Properties[$refinementRevision]) { throw 'Missing tested refinement class filter.' }
        $refinementPins = $support.refinement_revisions.($refinementRevision)
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
if ($manifest.revision -in @(31,32,33,34,35,36,37,38,39)) {
    if (-not $manifest.PSObject.Properties['experimental_crafting'] -or -not $manifest.experimental_crafting -or
        -not $support.PSObject.Properties['crafting_revisions'] -or
        -not $support.crafting_revisions.PSObject.Properties['31']) { throw 'Missing crafting compatibility pins.' }
    foreach ($pin in $support.crafting_revisions.'31'.PSObject.Properties) {
        $found = @($manifest.payloads | Where-Object path -CEQ $pin.Name)
        if ($found.Count -ne 1 -or $found[0].original_sha256 -cne $pin.Value.original_sha256 -or
            $found[0].replacement_sha256 -cne $pin.Value.replacement_sha256 -or
            $found[0].size -ne $found[0].replacement_size) { throw "Crafting payload pin mismatch: $($pin.Name)" }
    }
}
if ($manifest.revision -in @(32,33,34,35,36,37,38,39)) {
    $extractionRevision = if ($manifest.revision -in @(34,35,36,37,38,39)) { '34' } else { '32' }
    if ($manifest.revision -in @(34,35,36,37,38,39) -and (-not $manifest.PSObject.Properties['experimental_extraction_scroll'] -or
        -not $manifest.experimental_extraction_scroll)) { throw 'Missing extraction scrollbar flag.' }
    if (-not $manifest.PSObject.Properties['experimental_extraction'] -or -not $manifest.experimental_extraction -or
        -not $support.PSObject.Properties['extraction_revisions'] -or
        -not $support.extraction_revisions.PSObject.Properties[$extractionRevision]) { throw 'Missing extraction compatibility pins.' }
    foreach ($pin in $support.extraction_revisions.$extractionRevision.PSObject.Properties) {
        $found = @($manifest.payloads | Where-Object path -CEQ $pin.Name)
        if ($found.Count -ne 1 -or $found[0].original_sha256 -cne $pin.Value.original_sha256 -or
            $found[0].replacement_sha256 -cne $pin.Value.replacement_sha256 -or
            $found[0].size -ne $found[0].replacement_size) { throw "Extraction payload pin mismatch: $($pin.Name)" }
    }
}
if ($manifest.revision -in @(35,36,37,38,39)) {
    if ($manifest.revision -in @(36,37,38,39) -and (-not $manifest.PSObject.Properties['crafting_nested_layout'] -or
        -not $manifest.crafting_nested_layout)) { throw 'Missing nested Crafting layout repair.' }
    if (-not $manifest.PSObject.Properties['experimental_crafting_icons'] -or
        -not $manifest.experimental_crafting_icons -or $manifest.fixture_tests_passed -lt 9 -or
        -not $manifest.PSObject.Properties['crafting_runtime'] -or
        -not $support.PSObject.Properties['crafting_runtime_revisions']) { throw 'Missing tested crafting icon repair.' }
    $craftingRuntime = $support.crafting_runtime_revisions.'35'
    foreach ($key in @('layout','background_size','background_position')) {
        foreach ($field in @('rva','prefix','size','sha256')) {
            if ($manifest.crafting_runtime.methods.$key.$field -cne $craftingRuntime.methods.$key.$field) {
                throw "Crafting method pin mismatch: $key.$field"
            }
        }
    }
    foreach ($key in @('description_vtable','card_vtable','list_vtable','root_vtable')) {
        if ($manifest.crafting_runtime.$key.rva -ne $craftingRuntime.$key.rva -or
            $manifest.crafting_runtime.$key.type -cne $craftingRuntime.$key.type) { throw "Crafting owner pin mismatch: $key" }
    }
}
if ($manifest.revision -in @(33,34,35,36,37,38,39)) {
    if (-not $manifest.PSObject.Properties['experimental_buy_labels'] -or -not $manifest.experimental_buy_labels -or
        -not $support.PSObject.Properties['buy_label_revisions'] -or
        -not $support.buy_label_revisions.PSObject.Properties['33']) { throw 'Missing buy-label compatibility pins.' }
    foreach ($pin in $support.buy_label_revisions.'33'.PSObject.Properties) {
        $expected = $pin.Value
        if ($manifest.revision -in @(38,39) -and $pin.Name -ceq 'ui/xml/gamemain/title/itemicon.css') {
            if (-not $support.PSObject.Properties['shop_count_assets_revisions'] -or
                -not $support.shop_count_assets_revisions.PSObject.Properties['38']) { throw 'Missing shop count asset pins.' }
            $expected = $support.shop_count_assets_revisions.'38'.'ui/xml/gamemain/title/itemicon.css'
        }
        $found = @($manifest.payloads | Where-Object path -CEQ $pin.Name)
        if ($found.Count -ne 1 -or $found[0].original_sha256 -cne $expected.original_sha256 -or
            $found[0].replacement_sha256 -cne $expected.replacement_sha256 -or
            $found[0].size -ne $found[0].replacement_size) { throw "Buy-label payload pin mismatch: $($pin.Name)" }
    }
}
if ($manifest.revision -in @(37,38,39)) {
    if (-not $manifest.PSObject.Properties['experimental_shop_counts'] -or -not $manifest.experimental_shop_counts -or
        $manifest.fixture_tests_passed -lt 10 -or -not $manifest.PSObject.Properties['shop_count_runtime'] -or
        -not $support.PSObject.Properties['shop_count_runtime_revisions'] -or
        -not $support.shop_count_runtime_revisions.PSObject.Properties['37']) { throw 'Missing tested shop count repair.' }
    $countRuntime = $support.shop_count_runtime_revisions.'37'
    if ($manifest.shop_count_runtime.negative_atom_rva -ne $countRuntime.negative_atom_rva) { throw 'Shop requirement atom mismatch.' }
    foreach ($method in @('remove_property','negative_atom_initializer')) {
        foreach ($field in @('rva','size','prefix','sha256')) {
            if ($manifest.shop_count_runtime.$method.$field -cne $countRuntime.$method.$field) { throw "Shop count method mismatch: $method.$field" }
        }
    }
    foreach ($owner in @('description_vtable','list_vtable','root_vtable')) {
        if ($manifest.shop_count_runtime.$owner.rva -ne $countRuntime.$owner.rva -or
            $manifest.shop_count_runtime.$owner.type -cne $countRuntime.$owner.type) { throw "Shop count owner mismatch: $owner" }
    }
}
if ($manifest.revision -in @(38,39)) {
    if (-not $manifest.PSObject.Properties['shop_count_translation_reset'] -or
        -not $manifest.shop_count_translation_reset -or
        -not $support.PSObject.Properties['shop_count_assets_revisions'] -or
        -not $support.shop_count_assets_revisions.PSObject.Properties['38']) { throw 'Missing shop count translation reset.' }
    $countPins = $support.shop_count_assets_revisions.'38'
    foreach ($asset in $countPins.PSObject.Properties) {
        $records = @($manifest.payloads | Where-Object path -CEQ $asset.Name)
        if ($records.Count -ne 1 -or $records[0].original_sha256 -cne $asset.Value.original_sha256 -or
            $records[0].replacement_sha256 -cne $asset.Value.replacement_sha256) { throw 'Shop count translation asset mismatch.' }
    }
}
if ($manifest.revision -eq 39) {
    if (-not $manifest.PSObject.Properties['experimental_comrades'] -or -not $manifest.experimental_comrades -or
        -not $support.PSObject.Properties['comrades_revisions'] -or
        -not $support.comrades_revisions.PSObject.Properties['39']) { throw 'Missing comrades compatibility pins.' }
    if ($manifest.comrades_columns -ne 5 -or $manifest.comrades_rows -ne 3 -or
        $manifest.comrades_tile_width -ne 124 -or $manifest.comrades_tile_height -ne 108) { throw 'Unexpected comrades dimensions.' }
    foreach ($pin in $support.comrades_revisions.'39'.PSObject.Properties) {
        $found = @($manifest.payloads | Where-Object path -CEQ $pin.Name)
        if ($found.Count -ne 1 -or $found[0].original_sha256 -cne $pin.Value.original_sha256 -or
            $found[0].replacement_sha256 -cne $pin.Value.replacement_sha256 -or
            $found[0].size -ne $found[0].replacement_size) { throw "Comrades payload pin mismatch: $($pin.Name)" }
    }
}
$prior = $null
if ($PreviousPackage) {
    $PreviousPackage = (Resolve-Path -LiteralPath $PreviousPackage).Path
    $prior = Get-Content -LiteralPath (Join-Path $PreviousPackage 'manifest.json') -Raw | ConvertFrom-Json
}
if (-not $BackupRoot) { $BackupRoot = Join-Path (Split-Path -Parent $Package) 'rollback' }
Invoke-GridChange -Action $Action -Game $Game -Package $Package -Manifest $manifest -PreviousPackage $PreviousPackage -PreviousManifest $prior -BackupRoot $BackupRoot
