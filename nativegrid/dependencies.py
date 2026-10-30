"""Fetch hash-pinned upstream artifacts into an ignored local cache."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import urllib.request
import zipfile

SOURCE = Path(__file__).resolve().parent
CACHE = SOURCE.parent / '.deps'
LOCK = json.loads((SOURCE / 'dependencies.lock.json').read_text())
MINHOOK = CACHE / 'minhook'
LOADER_HASH = '57ec56390c92a18b82f58855e63c93985e254d1e29d5f75cbc28dc08f96c8a12'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def artifact(name, offline=True):
    record = LOCK[name]
    path = CACHE / 'downloads' / name
    if not path.exists():
        if offline:
            raise RuntimeError('Missing dependency. Run python -m nativegrid.dependencies first: ' + name)
        data = urllib.request.urlopen(record['url'], timeout=60).read()
        if sha256(data) != record['sha256']:
            raise ValueError('Downloaded dependency checksum mismatch: ' + name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if sha256(path.read_bytes()) != record['sha256']:
        raise ValueError('Cached dependency checksum mismatch: ' + name)
    return path


def prepare(offline=True):
    """Verify all cached inputs, then extract only owned dependency paths."""
    artifacts = {name: artifact(name, offline) for name in LOCK}
    with zipfile.ZipFile(artifacts['minhook.zip']) as archive:
        for entry in archive.infolist():
            parts = PurePosixPath(entry.filename).parts
            if entry.is_dir() or len(parts) < 2:
                continue
            relative = PurePosixPath(*parts[1:])
            if '..' in relative.parts or relative.is_absolute():
                raise ValueError('Unsafe dependency archive path')
            if relative.parts[0] not in ('include', 'src') and str(relative) != 'LICENSE.txt':
                continue
            target = MINHOOK.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(entry))
    package = CACHE / 'python' / 'cdumm' / 'archive'
    package.mkdir(parents=True, exist_ok=True)
    for folder in (package, package.parent):
        (folder / '__init__.py').write_text('')
    for name in ('hashlittle.py', 'paz_crypto.py'):
        shutil.copyfile(artifacts[name], package / name)
    shutil.copyfile(artifacts['CDUMM-LICENSE'], package.parent / 'LICENSE')
    loader = CACHE / 'loader'
    loader.mkdir(exist_ok=True)
    with zipfile.ZipFile(artifacts['ual.zip']) as archive:
        data = archive.read('dinput8.dll')
    if sha256(data) != LOADER_HASH:
        raise ValueError('Official loader binary checksum mismatch')
    (loader / 'winmm.dll').write_bytes(data)
    shutil.copyfile(artifacts['UAL-LICENSE'], loader / 'LICENSE')
    return MINHOOK, loader / 'winmm.dll'


def load_archive_helpers():
    package = CACHE / 'python' / 'cdumm' / 'archive'
    for name in ('hashlittle.py', 'paz_crypto.py'):
        if not (package / name).exists() or sha256((package / name).read_bytes()) != LOCK[name]['sha256']:
            raise RuntimeError('Archive helper missing or changed. Run python -m nativegrid.dependencies.')
    sys.path.insert(0, str(CACHE / 'python'))
    hashlittle = importlib.import_module('cdumm.archive.hashlittle').hashlittle
    decrypt = importlib.import_module('cdumm.archive.paz_crypto').decrypt
    return hashlittle, decrypt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true', help='Require verified artifacts already in .deps/downloads')
    args = parser.parse_args()
    prepare(args.offline)
    print('Verified pinned MinHook, CDUMM helpers, and Ultimate ASI Loader in .deps.')


if __name__ == '__main__':
    main()
