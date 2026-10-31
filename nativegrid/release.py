"""Export the portable patch-based candidate; never install or publish it."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0-rc1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def expected_payloads(support):
    from .requirements import PATH
    pins = dict(support['shop_assets'])
    for group in (support['sell_assets'], support['refinement_revisions']['30'],
                  support['crafting_revisions']['31'], support['extraction_revisions']['34'],
                  support['buy_label_revisions']['33'], support['shop_count_assets_revisions']['38'],
                  support['comrades_revisions']['41']):
        pins.update(group)
    pins[PATH] = support['shop_requirements']['asset']
    return pins


def check_privacy(data):
    # Check both ordinary and UTF-16 strings. Do not print matched contents.
    for decoded in (data.decode('latin1'), data.decode('utf-16-le', errors='ignore'),
                    data[1:].decode('utf-16-le', errors='ignore')):
        if re.search(r'(?i)[a-z]:[\\/]users[\\/]|[\\/]\.t3[\\/]|[\\/]scratch[\\/]', decoded):
            raise ValueError('Personal build path found in release file')


def validation_for(plugin_sha256):
    record = json.loads((ROOT/'nativegrid/release_validation.json').read_text())
    if record['version'] == VERSION and record['revision'] == 42 and record['game_build'] == '26345091' and record['plugin_sha256'] == plugin_sha256:
        return record
    return None


def export_package(package, output):
    package, output = Path(package).resolve(strict=True), Path(output).resolve()
    if output == package or output.is_relative_to(package) or package.is_relative_to(output):
        raise ValueError('Export must be separate from the preserved build directory')
    manifest = json.loads((package/'manifest.json').read_text())
    if manifest.get('revision') != 42 or manifest.get('release_patches') is not True:
        raise ValueError('Only the portable revision 42 patch candidate can be exported')
    support = json.loads((ROOT/'nativegrid/builds/26345091.json').read_text())
    for key in ('game_build', 'exe_sha256', 'master_sha256', 'pamt_sha256'):
        if manifest.get(key) != support[key]:
            raise ValueError('Candidate compatibility mismatch: ' + key)
    expected = expected_payloads(support)
    records = manifest['payloads']
    if len(records) != len(expected) or {r['path'] for r in records} != set(expected):
        raise ValueError('Candidate resource set differs from revision 41')
    patches = json.loads((package/'patch-report.json').read_text())
    if len(patches) != len(records) or {r['path'] for r in patches} != set(expected):
        raise ValueError('Incomplete patch report')
    for record in records + patches:
        for key in ('original_sha256', 'replacement_sha256'):
            if record[key] != expected[record['path']][key]:
                raise ValueError('Resource hash mismatch: ' + record['path'])
    suites = []
    for name, count in [('fixture-results.json', 10), ('release-fixture-results.json', 12)]:
        results = json.loads((package/name).read_text())
        if len(results) != count or any(r.get('passed') is not True for r in results):
            raise ValueError('Missing or failed native fixtures: ' + name)
        suites.extend(r['case'] for r in results)
    patch_test = json.loads((package/'patch-fixture-results.json').read_text())
    if patch_test.get('passed') is not True or '330 native patch checks across 30 resources' not in patch_test.get('output', ''):
        raise ValueError('Actual-resource native patch checks did not pass')
    binary = (package/'NativeGrid.asi').read_bytes()
    matches = [r for r in manifest['files'] if r['name'] == 'NativeGrid.asi']
    if len(matches) != 1 or digest(binary) != matches[0]['sha256'] or not binary.startswith(b'MZ'):
        raise ValueError('Candidate ASI integrity mismatch')
    check_privacy(binary)
    validation = validation_for(digest(binary))
    public = dict(version=VERSION, revision=42, status='candidate_user_confirmed' if validation else 'candidate_not_live_validated',
                  game_build=support['game_build'], executable_version=support['executable_version'],
                  exe_sha256=support['exe_sha256'], plugin_sha256=digest(binary),
                  resource_delivery='original-dependent copy/XOR patches with input/output SHA-256 checks',
                  runtime_log='NativeGrid.log beside the loaded ASI; optional',
                  native_suites=len(suites), actual_resource_patch_checks=330,
                  dmm_import_tested=bool(validation), live_tested=bool(validation), dmm_runtime_coexistence_tested=False,
                  live_validation=validation,
                  payloads=records)
    entries = {'NativeGrid/NativeGrid.asi': binary,
               'NativeGrid/NativeGrid-LICENSE.txt': (ROOT/'LICENSE').read_bytes(),
               'NativeGrid/NativeGrid-release.json': (json.dumps(public, indent=2)+'\n').encode()}
    for name in ('MinHook', 'CDUMM'):
        entries[f'NativeGrid/NativeGrid-license-{name}.txt'] = (ROOT/f'nativegrid/licenses/{name}.txt').read_bytes()
    entries['NativeGrid/NativeGrid-README.txt'] = (
        'NativeGrid 0.1.0-rc1 (revision 42) - experimental candidate\n\n'
        'Windows x64, Steam build 26345091, EXE 1.0.0.3460 only.\n'
        + ('This exact plugin passed a user-reported basic game check on Steam 26345091.\n'
           'Matching DMM/deployed hashes and active hooks verified; exhaustive coverage\n'
           'and DMM disable/re-enable remain unverified for this candidate.\n' if validation else
           'This candidate has passed offline fixtures, not its own live game test.\n') +
        'Revision 41 layouts are preserved; resource delivery and logging changed.\n\n'
        'Close the game. In DMM 4.6.0 use Mods > Import for this ZIP, then enable\n'
        'one NativeGrid entry in ASI Mods. Keep one ASI loader. None is bundled.\n'
        'NativeGrid itself needs no archive mount. Initially leave archive mods\n'
        'unmounted; coexistence with DmmRuntime.asi is unverified.\n'
        'Manual alternative: with one ASI loader installed, copy this folder\n'
        "contents into the game's bin64. Do not combine manual and DMM copies.\n\n"
        'Log: NativeGrid.log beside the loaded ASI, normally bin64. Logging is\n'
        'optional; failure to write it does not disable the mod.\n'
        'Other UI mods and English requirement-table mods may conflict.\n'
        'Unknown executable hashes stay inactive. No game archive or save writes.\n\n'
        'Uninstall: close the game and disable NativeGrid in DMM, or remove only\n'
        'NativeGrid.asi and its NativeGrid-prefixed companion files for manual\n'
        'installs. Keep shared loaders. Restore a preserved package to roll back.\n\n'
        'Original code and mod changes: MIT, copyright 2026 diegoag64.\n'
        'Keep the copyright and license notice with reuse. Third-party notices\n'
        'remain separate. The MIT grant does not cover Pearl Abyss game content.\n'
        'Credits: MinHook/HDE (runtime hooks), CDUMM helpers (local builder).\n'
        'DMM and Ultimate ASI Loader are separate tools, not bundled.\n\n'
        'Source and documentation: https://github.com/diegoag64/crimson-desert-mods\n'
        'DMM: https://www.nexusmods.com/crimsondesert/mods/633\n'
    ).encode()
    for content in entries.values():
        check_privacy(content)
    output.mkdir(parents=True, exist_ok=False)
    archive = output/f'NativeGrid-{VERSION}-DMM.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, content)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() or z.namelist() != sorted(entries) or any(z.read(n) != d for n, d in entries.items()):
            raise ValueError('ZIP round-trip verification failed')
    source_files = [p for p in (ROOT/'tracked-files.txt').read_text().splitlines()
                    if p.startswith('nativegrid/') or p in ('LICENSE', 'requirements.txt')]
    receipt = dict(version=VERSION, archive_sha256=digest(archive.read_bytes()),
                   entries={n:digest(d) for n,d in entries.items()},
                   source_files_sha256={p:digest((ROOT/p).read_bytes()) for p in source_files},
                   fixture_suites=suites, patch_checks=patch_test,
                   full_resource_copies_excluded=True, personal_paths_excluded=True,
                   live_tested=bool(validation), live_validation=validation, publication_ready=False)
    (output/'release-audit.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(export_package(args.package, args.out))


if __name__ == '__main__':
    main()
