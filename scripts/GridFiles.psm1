Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-GridHash([string]$Path) {
    (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-GridPackage([string]$Package, $Manifest) {
    $names = @('NativeGrid.asi', 'winmm.dll', 'winmm.ini')
    if (@($Manifest.files).Count -ne 3 -or @($Manifest.files.name | Select-Object -Unique).Count -ne 3) { throw 'Package must contain three unique owned files.' }
    foreach ($file in $Manifest.files) {
        if ($file.name -cnotin $names -or $file.sha256 -cnotmatch '^[a-f0-9]{64}$') { throw 'Invalid owned file record.' }
        if ((Get-GridHash (Join-Path $Package $file.name)) -ne $file.sha256) { throw "Package file changed: $($file.name)" }
    }
}

function Copy-GridNew([string]$Source, [string]$Target) {
    $data = [IO.File]::ReadAllBytes($Source)
    $stream = [IO.File]::Open($Target, 'CreateNew', 'Write', 'None')
    try { $stream.Write($data, 0, $data.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}

function Invoke-GridChange {
    param(
        [ValidateSet('Verify','Install','Uninstall')][string]$Action,
        [string]$Game, [string]$Package, $Manifest,
        [string]$PreviousPackage, $PreviousManifest,
        [string]$BackupRoot,
        [scriptblock]$Running = { [bool](Get-Process -Name CrimsonDesert -ErrorAction SilentlyContinue) }
    )
    Assert-GridPackage $Package $Manifest
    if ($PreviousManifest) { Assert-GridPackage $PreviousPackage $PreviousManifest }
    if ($Action -ne 'Verify' -and (& $Running)) { throw 'Game is running; no changes made.' }
    if ($Action -ne 'Uninstall') { foreach ($check in @(
        @{path='bin64\CrimsonDesert.exe'; hash=$Manifest.exe_sha256},
        @{path='meta\0.papgt'; hash=$Manifest.master_sha256},
        @{path='0012\0.pamt'; hash=$Manifest.pamt_sha256}
    )) {
        if ((Get-GridHash (Join-Path $Game $check.path)) -ne $check.hash) { throw "Game changed: $($check.path)" }
    } }
    $bin = Join-Path $Game 'bin64'
    $other = @(Get-ChildItem -LiteralPath $bin -File -Filter '*.asi' | Where-Object Name -ne 'NativeGrid.asi')
    if ($other.Count) { throw 'Another ASI is installed. Resolve the shared loader before changing this package.' }
    $operations = @()
    foreach ($file in $Manifest.files) {
        $target = Join-Path $bin $file.name
        $before = $null
        if (Test-Path -LiteralPath $target) {
            $before = Get-GridHash $target
            if ($before -ne $file.sha256) {
                if ($Action -eq 'Uninstall' -or -not $PreviousManifest) { throw "Conflicting installed file: $($file.name)" }
                $prior = @($PreviousManifest.files | Where-Object name -eq $file.name)
                if ($prior.Count -ne 1 -or $prior[0].sha256 -ne $before) { throw "Existing file is not the verified previous package: $($file.name)" }
            }
        }
        $after = if ($Action -eq 'Uninstall') { $null } else { $file.sha256 }
        if ($before -ne $after) { $operations += [pscustomobject]@{name=$file.name; before=$before; after=$after} }
    }
    if ($Action -eq 'Verify') { Write-Output 'Verified package, game fingerprints, and existing files.'; return }
    if (-not $operations.Count) { Write-Output 'Owned files already match the requested state.'; return }
    $gameFull = [IO.Path]::GetFullPath($Game).TrimEnd('\')
    $backupFull = [IO.Path]::GetFullPath($BackupRoot).TrimEnd('\')
    if ($backupFull -eq $gameFull -or $backupFull.StartsWith($gameFull + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Rollback directory must be outside the game installation.' }
    $backup = Join-Path $backupFull ('rollback-' + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($backup) | Out-Null
    foreach ($operation in $operations) {
        if ($operation.before) {
            Copy-GridNew (Join-Path $bin $operation.name) (Join-Path $backup $operation.name)
            if ((Get-GridHash (Join-Path $backup $operation.name)) -ne $operation.before) { throw 'Rollback copy verification failed.' }
        }
    }
    if ($Action -eq 'Install') {
        $incoming = Join-Path $backup 'incoming'
        [IO.Directory]::CreateDirectory($incoming) | Out-Null
        foreach ($file in $Manifest.files) {
            Copy-GridNew (Join-Path $Package $file.name) (Join-Path $incoming $file.name)
            if ((Get-GridHash (Join-Path $incoming $file.name)) -ne $file.sha256) { throw 'Package changed during staging.' }
        }
    }
    $journal = [pscustomobject]@{schema=1; action=$Action; status='prepared'; game=$gameFull; package=$Package; operations=$operations}
    $journalPath = Join-Path $backup 'transaction.json'
    $journal | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $journalPath -Encoding UTF8
    # Validate the entire destination again before the first mutation.
    if (& $Running) { throw 'Game started during validation; no installed files changed.' }
    foreach ($operation in $operations) {
        $target = Join-Path $bin $operation.name
        $current = if (Test-Path -LiteralPath $target) { Get-GridHash $target } else { $null }
        if ($current -ne $operation.before) { throw 'Installed files changed during validation.' }
    }
    $changed = @()
    try {
        foreach ($operation in $operations) {
            if (& $Running) { throw 'Game started during transaction. Retain the rollback journal.' }
            $target = Join-Path $bin $operation.name
            $changed += $operation
            if ($operation.before) { Remove-Item -LiteralPath $target }
            if ($operation.after) {
                Copy-GridNew (Join-Path $incoming $operation.name) $target
                if ((Get-GridHash $target) -ne $operation.after) { throw 'Installed file hash mismatch.' }
            }
        }
        $journal.status = 'complete'
    } catch {
        $failure = $_
        $journal.status = 'needs_recovery'
        if (-not (& $Running)) {
            foreach ($operation in $changed) {
                $target = Join-Path $bin $operation.name
                if (Test-Path -LiteralPath $target) {
                    if ((Get-GridHash $target) -ne $operation.after) { continue }
                    Remove-Item -LiteralPath $target
                }
                if ($operation.before) { Copy-GridNew (Join-Path $backup $operation.name) $target }
            }
        }
        $journal | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $journalPath -Encoding UTF8
        throw $failure
    }
    $journal | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $journalPath -Encoding UTF8
    Write-Output "$Action complete. Preserved rollback files and journal: $backup"
}

Export-ModuleMember -Function Get-GridHash, Assert-GridPackage, Invoke-GridChange
