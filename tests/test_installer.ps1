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
$candidate.revision = 28
$candidate.refinement_runtime = $support.refinement_runtime_revisions.'27'
$candidate.payloads = @($support.refinement_revisions.'28'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
Invoke-WrapperVerify
Write-Output 'PASS: revision 28 accepts new styling with unchanged revision 27 runtime pins'
$candidate.payloads[2].replacement_sha256 = $support.refinement_revisions.'27'.'ui/xml/gamemain/play/itemenchantpanel.css'.replacement_sha256
Assert-Throws { Invoke-WrapperVerify } 'revision 28 refuses the previous stylesheet'
$candidate.revision = 29
$candidate.payloads = @($support.refinement_revisions.'29'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
Invoke-WrapperVerify
Write-Output 'PASS: revision 29 accepts inline-symbol alignment with unchanged runtime pins'
$candidate.payloads[2].replacement_sha256 = $support.refinement_revisions.'28'.'ui/xml/gamemain/play/itemenchantpanel.css'.replacement_sha256
Assert-Throws { Invoke-WrapperVerify } 'revision 29 refuses the previous stylesheet'
$candidate.revision = 30
$candidate.payloads = @($support.refinement_revisions.'30'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
Invoke-WrapperVerify
Write-Output 'PASS: revision 30 accepts whole-label alignment with unchanged runtime pins'
$candidate.payloads[2].replacement_sha256 = $support.refinement_revisions.'29'.'ui/xml/gamemain/play/itemenchantpanel.css'.replacement_sha256
Assert-Throws { Invoke-WrapperVerify } 'revision 30 refuses the previous stylesheet'
$candidate.revision = 31
$candidate | Add-Member -NotePropertyName experimental_crafting -NotePropertyValue $true
$candidate.payloads = @($support.refinement_revisions.'30'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
}) + @($support.crafting_revisions.'31'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
Invoke-WrapperVerify
Write-Output 'PASS: revision 31 accepts crafting with unchanged revision 30 refinement pins'
$candidate.experimental_crafting = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 31 requires explicit crafting flag'
$candidate.experimental_crafting = $true
$craftHash = $candidate.payloads[-1].replacement_sha256
$candidate.payloads[-1].replacement_sha256 = '0' * 64
Assert-Throws { Invoke-WrapperVerify } 'revision 31 refuses changed crafting stylesheet'
$candidate.payloads[-1].replacement_sha256 = $craftHash
$candidate.payloads[-1].replacement_size++
Assert-Throws { Invoke-WrapperVerify } 'revision 31 refuses resized crafting payload'
$candidate.payloads[-1].replacement_size--
$candidate.payloads = @($candidate.payloads | Select-Object -SkipLast 1)
Assert-Throws { Invoke-WrapperVerify } 'revision 31 refuses missing crafting payload'
# Restore the removed crafting payload before testing the combined extraction package.
$candidate.payloads = @($support.refinement_revisions.'30'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
}) + @($support.crafting_revisions.'31'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
}) + @($support.extraction_revisions.'32'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
$candidate.revision = 32
$candidate | Add-Member -NotePropertyName experimental_extraction -NotePropertyValue $true
Invoke-WrapperVerify
Write-Output 'PASS: revision 32 accepts extraction and preserved crafting/refinement pins'
$candidate.experimental_extraction = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 32 requires extraction flag'
$candidate.experimental_extraction = $true
$extractHash = $candidate.payloads[-1].replacement_sha256
$candidate.payloads[-1].replacement_sha256 = '0' * 64
Assert-Throws { Invoke-WrapperVerify } 'revision 32 refuses changed extraction stylesheet'
$candidate.payloads[-1].replacement_sha256 = $extractHash
$candidate.payloads[-1].replacement_size++
Assert-Throws { Invoke-WrapperVerify } 'revision 32 refuses resized extraction payload'
$candidate.payloads[-1].replacement_size--
$candidate.experimental_crafting = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 32 still requires crafting guards'
$candidate.experimental_crafting = $true
$candidate.payloads = @($candidate.payloads | Select-Object -SkipLast 1)
Assert-Throws { Invoke-WrapperVerify } 'revision 32 refuses missing extraction payload'
$candidate.payloads += @($support.extraction_revisions.'32'.PSObject.Properties | Select-Object -Last 1 | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
$candidate.payloads += @($support.buy_label_revisions.'33'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
$candidate.revision = 33
$candidate | Add-Member -NotePropertyName experimental_buy_labels -NotePropertyValue $true
Invoke-WrapperVerify
Write-Output 'PASS: revision 33 accepts scoped buy labels and prepared extraction pins'
$candidate.experimental_buy_labels = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 33 requires buy-label flag'
$candidate.experimental_buy_labels = $true
$labelHash = $candidate.payloads[-1].replacement_sha256
$candidate.payloads[-1].replacement_sha256 = '0' * 64
Assert-Throws { Invoke-WrapperVerify } 'revision 33 refuses changed buy-label payload'
$candidate.payloads[-1].replacement_sha256 = $labelHash
$candidate.payloads[-1].replacement_size++
Assert-Throws { Invoke-WrapperVerify } 'revision 33 refuses resized buy-label payload'
$candidate.payloads[-1].replacement_size--
$candidate.experimental_extraction = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 33 still requires extraction guards'
$candidate.experimental_extraction = $true
$candidate.payloads = @($candidate.payloads | Select-Object -SkipLast 1)
Assert-Throws { Invoke-WrapperVerify } 'revision 33 refuses missing buy-label payload'
$candidate.payloads += @($support.buy_label_revisions.'33'.PSObject.Properties | Select-Object -Last 1 | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
$candidate.revision = 34
$candidate | Add-Member -NotePropertyName experimental_extraction_scroll -NotePropertyValue $true
Assert-Throws { Invoke-WrapperVerify } 'revision 34 refuses the old extraction scrollbar payload'
$extractPath = 'ui/xml/gamemain/play/itemextractpanel.css'
$extractPayload = @($candidate.payloads | Where-Object path -CEQ $extractPath)[0]
$extractPayload.replacement_sha256 = $support.extraction_revisions.'34'.$extractPath.replacement_sha256
Invoke-WrapperVerify
Write-Output 'PASS: revision 34 accepts corrected extraction scrollbar and preserved prior payloads'
$candidate.experimental_extraction_scroll = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 34 requires scrollbar flag'
$candidate.experimental_extraction_scroll = $true
$extractPayload.replacement_size++
Assert-Throws { Invoke-WrapperVerify } 'revision 34 refuses resized extraction stylesheet'
$extractPayload.replacement_size--
$candidate.experimental_buy_labels = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 34 preserves buy-label guards'
$candidate.experimental_buy_labels = $true
$candidate.revision = 35
$candidate.fixture_tests_passed = 9
$candidate | Add-Member -NotePropertyName experimental_crafting_icons -NotePropertyValue $true
$candidate | Add-Member -NotePropertyName crafting_runtime -NotePropertyValue ($support.crafting_runtime_revisions.'35' | ConvertTo-Json -Depth 20 | ConvertFrom-Json)
Invoke-WrapperVerify
Write-Output 'PASS: revision 35 accepts guarded Crafting repair and all revision 34 payloads'
$candidate.revision = 36
Assert-Throws { Invoke-WrapperVerify } 'revision 36 refuses missing nested-layout marker'
$candidate | Add-Member -NotePropertyName crafting_nested_layout -NotePropertyValue $true
Invoke-WrapperVerify
Write-Output 'PASS: revision 36 accepts nested-layout repair with unchanged native pins'
$candidate.crafting_nested_layout = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 36 refuses disabled nested-layout repair'
$candidate.PSObject.Properties.Remove('crafting_nested_layout')
$candidate.revision = 35
$candidate.experimental_crafting_icons = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 35 requires icon repair flag'
$candidate.experimental_crafting_icons = $true
$candidate.fixture_tests_passed = 8
Assert-Throws { Invoke-WrapperVerify } 'revision 35 requires native cache fixture'
$candidate.fixture_tests_passed = 9
foreach ($method in @('layout','background_size','background_position')) {
    $candidate.crafting_runtime.methods.$method.rva++
    Assert-Throws { Invoke-WrapperVerify } "revision 35 rejects changed $method RVA"
    $candidate.crafting_runtime.methods.$method.rva--
    $prefix = $candidate.crafting_runtime.methods.$method.prefix
    $candidate.crafting_runtime.methods.$method.prefix = '00' * 24
    Assert-Throws { Invoke-WrapperVerify } "revision 35 rejects changed $method prefix"
    $candidate.crafting_runtime.methods.$method.prefix = $prefix
    $hash = $candidate.crafting_runtime.methods.$method.sha256
    $candidate.crafting_runtime.methods.$method.sha256 = '0' * 64
    Assert-Throws { Invoke-WrapperVerify } "revision 35 rejects changed $method body hash"
    $candidate.crafting_runtime.methods.$method.sha256 = $hash
}
foreach ($owner in @('description_vtable','card_vtable','list_vtable','root_vtable')) {
    $candidate.crafting_runtime.$owner.rva++
    Assert-Throws { Invoke-WrapperVerify } "revision 35 rejects changed $owner"
    $candidate.crafting_runtime.$owner.rva--
}
$candidate.experimental_extraction_scroll = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 35 preserves extraction scrollbar guards'
$candidate.experimental_extraction_scroll = $true
$candidate.PSObject.Properties.Remove('crafting_runtime')
Assert-Throws { Invoke-WrapperVerify } 'revision 35 rejects missing runtime metadata'
$candidate.PSObject.Properties.Remove('experimental_crafting_icons')
$candidate.PSObject.Properties.Remove('experimental_extraction_scroll')
$candidate.PSObject.Properties.Remove('experimental_buy_labels')
$candidate.PSObject.Properties.Remove('experimental_extraction')
$candidate.PSObject.Properties.Remove('experimental_crafting')
$candidate.revision = 25
$candidate.fixture_tests_passed = 7
$candidate.payloads = @($support.refinement_assets.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
$candidate.PSObject.Properties.Remove('refinement_runtime')
Invoke-WrapperVerify
Write-Output 'PASS: revision 25 rollback still accepts its original asset pins without new hook'

# A new game build must select its own methods, owners, indexes, and UI bytes.
$updated = Get-Content -LiteralPath (Join-Path $PSScriptRoot '..\nativegrid\builds\26345091.json') -Raw | ConvertFrom-Json
[IO.File]::WriteAllText((Join-Path $game 'bin64\CrimsonDesert.exe'), 'synthetic updated executable')
[IO.File]::WriteAllText($extraPath, 'synthetic updated localization')
$updated.exe_sha256 = Get-GridHash (Join-Path $game 'bin64\CrimsonDesert.exe')
$updated.master_sha256 = Get-GridHash (Join-Path $game 'meta\0.papgt')
$updated.pamt_sha256 = Get-GridHash (Join-Path $game '0012\0.pamt')
$updated.shop_requirements.index_sha256 = Get-GridHash $extraPath
$updated | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $wrapper 'nativegrid\builds\26345091.json')
$candidate = New-Manifest $package
$candidate | Add-Member -NotePropertyMembers @{
    schema=1; revision=35; fixture_tests_passed=9; variable_length_resources=$true
    experimental_shop=$true; experimental_refinement=$true; experimental_crafting=$true
    experimental_extraction=$true; experimental_buy_labels=$true; experimental_extraction_scroll=$true
    experimental_crafting_icons=$true
    refinement_runtime=($updated.refinement_runtime_revisions.'27' | ConvertTo-Json -Depth 20 | ConvertFrom-Json)
    crafting_runtime=($updated.crafting_runtime_revisions.'35' | ConvertTo-Json -Depth 20 | ConvertFrom-Json)
    extra_indexes=[pscustomobject]@{'0020/0.pamt'=$updated.shop_requirements.index_sha256}
    payloads=@(@($updated.refinement_revisions.'30', $updated.crafting_revisions.'31',
                  $updated.extraction_revisions.'34', $updated.buy_label_revisions.'33') | ForEach-Object {
        $_.PSObject.Properties | ForEach-Object {
            [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
        }
    })
}
Invoke-WrapperVerify
Write-Output 'PASS: build 26345091 accepts its separate revision 35 compatibility pins'
$candidate.crafting_runtime.methods.layout.rva = $support.crafting_runtime_revisions.'35'.methods.layout.rva
Assert-Throws { Invoke-WrapperVerify } 'new build refuses previous Crafting method address'
$candidate.crafting_runtime.methods.layout.rva = $updated.crafting_runtime_revisions.'35'.methods.layout.rva
$candidate.refinement_runtime.hidden_atom_rva = $support.refinement_runtime_revisions.'27'.hidden_atom_rva
Assert-Throws { Invoke-WrapperVerify } 'new build refuses previous hidden-class atom'
$candidate.refinement_runtime.hidden_atom_rva = $updated.refinement_runtime_revisions.'27'.hidden_atom_rva
$candidate.refinement_runtime.root_vtable.rva = $support.refinement_runtime_revisions.'27'.root_vtable.rva
Assert-Throws { Invoke-WrapperVerify } 'new build refuses previous Refinement owner'
$candidate.refinement_runtime.root_vtable.rva = $updated.refinement_runtime_revisions.'27'.root_vtable.rva
$componentPath = 'ui/bin__/itemicon_component_game.uibinary'
$component = @($candidate.payloads | Where-Object path -CEQ $componentPath)[0]
$component.original_sha256 = $support.buy_label_revisions.'33'.$componentPath.original_sha256
Assert-Throws { Invoke-WrapperVerify } 'new build refuses previous item-component original'
$component.original_sha256 = $updated.buy_label_revisions.'33'.$componentPath.original_sha256
$candidate.extra_indexes.'0020/0.pamt' = $support.shop_requirements.index_sha256
Assert-Throws { Invoke-WrapperVerify } 'new build refuses previous localization index'
$candidate.extra_indexes.'0020/0.pamt' = $updated.shop_requirements.index_sha256
$candidate.exe_sha256 = $support.exe_sha256
Assert-Throws { Invoke-WrapperVerify } 'updated game cannot use previous executable support'

# Revision 37 is an optional, separately audited addition to the working revision 36.
$candidate.exe_sha256 = $updated.exe_sha256
$candidate.revision = 37
$candidate.fixture_tests_passed = 10
$candidate | Add-Member -NotePropertyName crafting_nested_layout -NotePropertyValue $true
Assert-Throws { Invoke-WrapperVerify } 'revision 37 refuses absent shop runtime metadata'
$candidate | Add-Member -NotePropertyName experimental_shop_counts -NotePropertyValue $true
$candidate | Add-Member -NotePropertyName shop_count_runtime -NotePropertyValue ($updated.shop_count_runtime_revisions.'37' | ConvertTo-Json -Depth 20 | ConvertFrom-Json)
Invoke-WrapperVerify
Write-Output 'PASS: revision 37 accepts scoped shop count repair with preserved revision 36 payloads'
$candidate.experimental_shop_counts = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 37 requires count repair flag'
$candidate.experimental_shop_counts = $true
$candidate.fixture_tests_passed = 9
Assert-Throws { Invoke-WrapperVerify } 'revision 37 requires pooled-count native fixture'
$candidate.fixture_tests_passed = 10
$candidate.crafting_nested_layout = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 37 preserves working Crafting recursion guard'
$candidate.crafting_nested_layout = $true
foreach ($method in @('remove_property','negative_atom_initializer')) {
    foreach ($field in @('rva','size','prefix','sha256')) {
        $saved = $candidate.shop_count_runtime.$method.$field
        $candidate.shop_count_runtime.$method.$field = if ($field -in @('rva','size')) { $saved + 1 } else { '0' + $saved.Substring(1) + '0' }
        Assert-Throws { Invoke-WrapperVerify } "revision 37 rejects changed $method.$field"
        $candidate.shop_count_runtime.$method.$field = $saved
    }
}
$candidate.shop_count_runtime.negative_atom_rva++
Assert-Throws { Invoke-WrapperVerify } 'revision 37 rejects changed requirement atom'
$candidate.shop_count_runtime.negative_atom_rva--
foreach ($owner in @('description_vtable','list_vtable','root_vtable')) {
    $candidate.shop_count_runtime.$owner.rva++
    Assert-Throws { Invoke-WrapperVerify } "revision 37 rejects changed $owner"
    $candidate.shop_count_runtime.$owner.rva--
}

# Revision 38 changes only the compact stock translation stylesheet.
$candidate.revision = 38
Assert-Throws { Invoke-WrapperVerify } 'revision 38 rejects previous stylesheet'
$cssPath = 'ui/xml/gamemain/title/itemicon.css'
$css = @($candidate.payloads | Where-Object path -CEQ $cssPath)[0]
$css.replacement_sha256 = $updated.shop_count_assets_revisions.'38'.$cssPath.replacement_sha256
Assert-Throws { Invoke-WrapperVerify } 'revision 38 requires translation reset marker'
$candidate | Add-Member -NotePropertyName shop_count_translation_reset -NotePropertyValue $true
Invoke-WrapperVerify
Write-Output 'PASS: revision 38 accepts explicit stock translation reset'
$candidate.shop_count_translation_reset = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 38 refuses disabled translation reset'
$candidate.shop_count_translation_reset = $true
$candidate.shop_count_runtime.remove_property.rva++
Assert-Throws { Invoke-WrapperVerify } 'revision 38 retains native count guards'
$candidate.shop_count_runtime.remove_property.rva--
$css.original_sha256 = 'wrong'
Assert-Throws { Invoke-WrapperVerify } 'revision 38 retains original stylesheet guard'
$css.original_sha256 = $updated.shop_count_assets_revisions.'38'.$cssPath.original_sha256
$candidate.crafting_nested_layout = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 38 retains nested Crafting guard'
$candidate.crafting_nested_layout = $true
Invoke-WrapperVerify

# Revision 39 adds three exact-sized comrades assets and keeps all 38 guards.
$candidate.revision = 39
Assert-Throws { Invoke-WrapperVerify } 'revision 39 requires explicit comrades flag'
$candidate | Add-Member -NotePropertyMembers @{
    experimental_comrades=$true; comrades_columns=5; comrades_rows=3
    comrades_tile_width=124; comrades_tile_height=108
}
Assert-Throws { Invoke-WrapperVerify } 'revision 39 rejects missing comrades assets'
$candidate.payloads += @($updated.comrades_revisions.'39'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
Invoke-WrapperVerify
Write-Output 'PASS: revision 39 accepts comrades cards and preserved revision 38'
$candidate.comrades_columns = 1
Assert-Throws { Invoke-WrapperVerify } 'revision 39 rejects list dimensions'
$candidate.comrades_columns = 5
foreach ($pin in $updated.comrades_revisions.'39'.PSObject.Properties) {
    $payload = @($candidate.payloads | Where-Object path -CEQ $pin.Name)[0]
    $saved = $payload.replacement_sha256
    $payload.replacement_sha256 = 'wrong'
    Assert-Throws { Invoke-WrapperVerify } "revision 39 rejects changed comrades asset $($pin.Name)"
    $payload.replacement_sha256 = $saved
    $payload.replacement_size++
    Assert-Throws { Invoke-WrapperVerify } "revision 39 rejects resized comrades asset $($pin.Name)"
    $payload.replacement_size--
}
$candidate.shop_count_translation_reset = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 39 retains working shop-count reset'
$candidate.shop_count_translation_reset = $true
Invoke-WrapperVerify

# Revision 40 adds scoped component styles; all six comrades payloads are required.
$candidate.revision = 40
Assert-Throws { Invoke-WrapperVerify } 'revision 40 refuses revision 39 payloads'
$candidate.payloads = @($candidate.payloads | Where-Object { $_.path -notin @($updated.comrades_revisions.'39'.PSObject.Properties.Name) })
$candidate.payloads += @($updated.comrades_revisions.'40'.PSObject.Properties | ForEach-Object {
    [pscustomobject]@{path=$_.Name; original_sha256=$_.Value.original_sha256; replacement_sha256=$_.Value.replacement_sha256; size=100; replacement_size=100}
})
Invoke-WrapperVerify
Write-Output 'PASS: revision 40 accepts isolated comrades component styles'
foreach ($pin in $updated.comrades_revisions.'40'.PSObject.Properties) {
    $payload = @($candidate.payloads | Where-Object path -CEQ $pin.Name)[0]
    $saved = $payload.replacement_sha256
    $payload.replacement_sha256 = 'wrong'
    Assert-Throws { Invoke-WrapperVerify } "revision 40 rejects altered asset $($pin.Name)"
    $payload.replacement_sha256 = $saved
    $payload.replacement_size++
    Assert-Throws { Invoke-WrapperVerify } "revision 40 rejects resized asset $($pin.Name)"
    $payload.replacement_size--
}
$candidate.experimental_comrades = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 40 requires comrades flag'
$candidate.experimental_comrades = $true
$candidate.shop_count_translation_reset = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 40 retains shop-count fix'
$candidate.shop_count_translation_reset = $true
$candidate.crafting_nested_layout = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 40 retains initial Crafting icons fix'
$candidate.crafting_nested_layout = $true
Invoke-WrapperVerify

# Revision 41 rejects the malformed revision 40 component even at equal length.
$candidate.revision = 41
Assert-Throws { Invoke-WrapperVerify } 'revision 41 rejects failed revision 40 binary'
$petPath = 'ui/bin__/pet_component_game.uibinary'
$petPayload = @($candidate.payloads | Where-Object path -CEQ $petPath)[0]
$petPayload.replacement_sha256 = $updated.comrades_revisions.'41'.$petPath.replacement_sha256
Invoke-WrapperVerify
Write-Output 'PASS: revision 41 accepts structurally validated management component'
$petPayload.original_sha256 = 'wrong'
Assert-Throws { Invoke-WrapperVerify } 'revision 41 rejects changed original component'
$petPayload.original_sha256 = $updated.comrades_revisions.'41'.$petPath.original_sha256
$petPayload.replacement_size++
Assert-Throws { Invoke-WrapperVerify } 'revision 41 requires exact component length'
$petPayload.replacement_size--
$candidate.comrades_rows = 4
Assert-Throws { Invoke-WrapperVerify } 'revision 41 requires compact grid dimensions'
$candidate.comrades_rows = 3
$candidate.shop_count_translation_reset = $false
Assert-Throws { Invoke-WrapperVerify } 'revision 41 retains the working shop reset'
$candidate.shop_count_translation_reset = $true
Invoke-WrapperVerify
