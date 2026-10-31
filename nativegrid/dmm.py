"""Export a verified local revision 41 package for DMM's ASI Mods library."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NOTICES = ('MinHook.txt', 'CDUMM.txt')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def export_package(package, output):
    """Package bytes after the CLI has run the existing compatibility verifier.

    This function checks export integrity, not game compatibility. The public CLI
    always invokes NativeGrid.ps1 -Action Verify first.
    """
    package = Path(package).resolve(strict=True)
    output = Path(output).resolve()
    manifest_bytes = (package / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get('schema') != 1 or manifest.get('revision') != 41:
        raise ValueError('DMM export currently supports revision 41 only.')
    if manifest.get('fixture_tests_passed', 0) < 10:
        raise ValueError('Revision 41 requires ten passing native suites.')
    records = manifest.get('files', [])
    if len(records) != 3 or {f['name'] for f in records} != {
        'NativeGrid.asi', 'winmm.dll', 'winmm.ini'
    }:
        raise ValueError('Expected exactly the three standalone owned files.')
    data = {}
    for record in records:
        content = (package / record['name']).read_bytes()
        if digest(content) != record['sha256']:
            raise ValueError('Package hash mismatch: ' + record['name'])
        data[record['name']] = content
    log = package / 'runtime.log'
    entries = {'NativeGrid/NativeGrid.asi': data['NativeGrid.asi']}
    for name in NOTICES:
        entries['NativeGrid/NativeGrid-license-' + name] = (package / 'licenses' / name).read_bytes()
    entries['NativeGrid/NativeGrid-README.txt'] = (
        'NativeGrid revision 41 - local DMM ASI package\n\n'
        f"Supported Steam build: {manifest['game_build']}\n"
        f"Required EXE SHA-256: {manifest['exe_sha256']}\n"
        f"Plugin SHA-256: {digest(data['NativeGrid.asi'])}\n\n"
        'Import this ZIP through DMM, or extract it and import the NativeGrid\n'
        'folder as an ASI mod. Enable one NativeGrid entry in ASI Mods.\n'
        'Close the game before importing, enabling, disabling, or updating.\n'
        'Keep the existing single ASI loader. No loader is bundled here.\n'
        'Do not mount archive mods for the first migration check.\n'
        'DmmRuntime.asi coexistence has not been tested.\n\n'
        'This is the unchanged revision 41 binary, including its UI payloads\n'
        'and native fixes. Keep the original build directory in place.\n'
        f'Runtime log: {log}\n\n'
        'Keep this generated package local; it embeds game-derived resources.\n'
        'See docs/dmm.md in the source repository for migration and rollback.\n'
        'https://github.com/diegoag64/crimson-desert-mods\n'
    ).encode('utf-8')
    # Never overwrite earlier exports or write into the preserved build package.
    if output == package or output.is_relative_to(package):
        raise ValueError('Export must be outside the source package.')
    output.mkdir(parents=True, exist_ok=False)
    archive = output / 'NativeGrid-r41-DMM.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, content)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None or set(z.namelist()) != set(entries):
            raise ValueError('Archive verification failed.')
        for name, content in entries.items():
            if z.read(name) != content:
                raise ValueError('Export changed bytes: ' + name)
    receipt = {
        'schema': 1, 'format': 'dmm-asi-folder', 'dmm_version_reviewed': '4.6.0',
        'revision': 41, 'game_build': manifest['game_build'],
        'source_package': str(package), 'runtime_log': str(log),
        'source_manifest_sha256': digest(manifest_bytes),
        'archive_sha256': digest(archive.read_bytes()),
        'entries': {name: digest(content) for name, content in sorted(entries.items())},
        'dmm_import_tested': False, 'dmm_runtime_coexistence_tested': False,
    }
    (output / 'export-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    # Reuse the full revision, asset, native method, game, and ownership checks.
    # Verify is read-only and is permitted while the game is running.
    subprocess.run([
        'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        str(ROOT / 'scripts' / 'NativeGrid.ps1'), '-Action', 'Verify',
        '-Game', str(args.game.resolve()), '-Package', str(args.package.resolve()),
    ], check=True)
    print(export_package(args.package, args.out))


if __name__ == '__main__':
    main()
