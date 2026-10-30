"""Build and fixture-test the inventory mod using read-only game inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct

from .dependencies import MINHOOK, prepare
from .compiler import compile_flexible
from .inventory import INVENTORY_PATHS, SELL_PATHS, transform, transform_sell
from .pe import PE, package_methods
from .tests import test

SOURCE = Path(__file__).resolve().parent
SUPPORT = json.loads((SOURCE / 'supported_build.json').read_text())
SUPPORTED_BUILDS = [SUPPORT] + [json.loads(path.read_text()) for path in sorted((SOURCE / 'builds').glob('*.json'))]


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def output_directory(path, game=None):
    output = Path(path).resolve()
    if game:
        game = Path(game).resolve()
        require(output != game and game not in output.parents and output not in game.parents,
                'Output and game installation must be separate directories')
    require(not output.exists() or not any(output.iterdir()), 'Output directory must be new or empty')
    output.mkdir(parents=True, exist_ok=True)
    return output


def build(game, output, gcc, experimental_shop=False):
    from .archive import Pamt, decrypt
    import lz4.block

    exe_hash = digest(game / 'bin64/CrimsonDesert.exe')
    matches = [record for record in SUPPORTED_BUILDS if record['exe_sha256'] == exe_hash]
    require(len(matches) == 1, 'Unsupported or ambiguous executable fingerprint')
    support = matches[0]
    fingerprints = {
        'bin64/CrimsonDesert.exe': support['exe_sha256'],
        'meta/0.papgt': support['master_sha256'],
        '0012/0.pamt': support['pamt_sha256'],
    }
    requirement_support = support.get('shop_requirements') if experimental_shop else None
    if requirement_support:
        from .requirements import INDEX, PATH as REQUIREMENT_PATH, transform as requirement_transform
        require(requirement_support['index_path'] == INDEX, 'Unexpected localization index')
        fingerprints[INDEX] = requirement_support['index_sha256']
    for path, expected in fingerprints.items():
        require(digest(game / path) == expected, 'Unsupported or changed game file: ' + path)
    exe = (game / 'bin64/CrimsonDesert.exe').read_bytes()
    methods = package_methods(exe) + [support['method_rvas'][2]]
    require(methods == support['method_rvas'], 'Derived package-worker methods differ from supported build')
    if 'resize_call_offset' in support:
        call = methods[1] + support['resize_call_offset']
        raw = PE(exe).raw(call)
        require(exe[raw] == 0xe8 and call + 5 + struct.unpack_from('<i', exe, raw+1)[0] == methods[2],
                'Full-read direct resize call differs from audited allocator')
    entries = {entry.path: entry for entry in Pamt.parse((game / '0012/0.pamt').read_bytes()).entries()}
    groups = {path: '0012' for path in entries}
    if requirement_support:
        localized = {entry.path: entry for entry in Pamt.parse((game / INDEX).read_bytes()).entries()}
        require(REQUIREMENT_PATH not in entries, 'Ambiguous localization asset')
        entries[REQUIREMENT_PATH] = localized[REQUIREMENT_PATH]
        groups[REQUIREMENT_PATH] = INDEX.split('/')[0]
    paths = list(INVENTORY_PATHS)
    sell_pins = support.get('sell_assets', {})
    require(not sell_pins or set(sell_pins) == set(SELL_PATHS), 'Incomplete sell layout support')
    paths += list(sell_pins)
    if experimental_shop:
        from .shop import SHOP_PATHS, transform as shop_transform
        paths += list(SHOP_PATHS)
    pins = dict(support['shop_assets'] if experimental_shop else support['assets'])
    pins.update(sell_pins)
    if requirement_support:
        paths.append(REQUIREMENT_PATH)
        pins[REQUIREMENT_PATH] = requirement_support['asset']
    payloads, records = [], []
    for path in paths:
        entry = entries[path]
        is_requirement = bool(requirement_support and path == REQUIREMENT_PATH)
        require(entry.flags == (0x30 if is_requirement else 0x32), 'Unexpected asset encoding: ' + path)
        with (game / f'{groups[path]}/{entry.chunk}.paz').open('rb') as stream:
            stream.seek(entry.offset)
            packed = stream.read(entry.stored)
        require(len(packed) == entry.stored, 'Incomplete archive read: ' + path)
        decoded = decrypt(packed, path.rsplit('/', 1)[1])
        before = decoded if is_requirement else lz4.block.decompress(decoded, uncompressed_size=entry.original)
        require(len(before) == entry.original, 'Decoded length mismatch: ' + path)
        require(hashlib.sha256(before).hexdigest() == pins[path]['original_sha256'], 'Original asset changed: ' + path)
        after = transform(path, before) if path in INVENTORY_PATHS else before
        if path in sell_pins:
            after = transform_sell(path, before)
        if experimental_shop and (path in SHOP_PATHS or path.endswith('/itemicon.css')):
            after = shop_transform(path, after)
            require(len(after) == len(before), 'Shop asset must support fixed-buffer reads: ' + path)
        if is_requirement:
            after = requirement_transform(before)
        require(hashlib.sha256(after).hexdigest() == pins[path]['replacement_sha256'], 'Transform differs from pinned replacement: ' + path)
        payloads.append((path, before, after))
        records.append(dict(path=path, size=len(before), replacement_size=len(after),
                            original_sha256=hashlib.sha256(before).hexdigest(), replacement_sha256=hashlib.sha256(after).hexdigest()))
    results = test(output, gcc, MINHOOK)
    compile_flexible(output, exe, payloads, methods, gcc, MINHOOK)
    shutil.copyfile(SOURCE.parent / '.deps/loader/winmm.dll', output / 'winmm.dll')
    # Match the tested loader configuration, including Windows line endings.
    (output / 'winmm.ini').write_bytes(b'[GlobalSets]\r\nDebugLog=1\r\nLoadExtraPlugins=\r\n[FileLoader]\r\nOverloadFromFolder=\r\n')
    shutil.copytree(SOURCE / 'licenses', output / 'licenses')
    revision = 20 if requirement_support else (14 if sell_pins or experimental_shop else (7 if support['game_build'] == '26329202' else 5))
    manifest = dict(schema=1, revision=revision, experimental_shop=experimental_shop,
                    status='built_not_installed', game_build=support['game_build'],
                    exe_sha256=support['exe_sha256'], master_sha256=support['master_sha256'], pamt_sha256=support['pamt_sha256'],
                    grid_columns=8, grid_rows=11, storage_grid_columns=8, storage_grid_rows=11,
                    tile_width=64, tile_height=62.5, list_toggle=False, resource_replacement=True,
                    variable_length_resources=True, fixture_tests_passed=len(results), payloads=records,
                    live_validation='Revision 5 inventory and Private Storage user-verified on build 26317560. This rebuilt binary and experimental shop have no live validation.',
                    files=[dict(name=name, sha256=digest(output / name)) for name in ('NativeGrid.asi', 'winmm.dll', 'winmm.ini')])
    if requirement_support:
        manifest.update(extra_indexes={INDEX: fingerprints[INDEX]}, requirement_labels_language='eng',
                        requirement_labels_status='icons_only_awaiting_live_validation')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    if sell_pins:
        manifest.update(sell_grid_columns=8, sell_grid_rows=11, sell_status='awaiting_live_validation')
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for path, expected in fingerprints.items():
        require(digest(game / path) == expected, 'Game input changed during build: ' + path)
    if experimental_shop:
        manifest.update(shop_columns=6, shop_rows=3, shop_tile_width=124, shop_tile_height=112,
                        shop_status='experimental_no_live_validation', shop_purchase_behavior='original native handlers and quantity selection')
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Built revision {manifest["revision"]}: {len(payloads)} exact-validated payloads; {len(results)} fixture suites passed. {output}')
    return manifest


def main():
    if not __debug__:
        raise RuntimeError('Do not use python -O: transform assertions are required.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, help='Supported Crimson Desert installation, read only')
    parser.add_argument('--out', type=Path, required=True, help='New or empty ignored output directory')
    parser.add_argument('--gcc', default='gcc', help='Path to MinGW-w64 x64 GCC')
    parser.add_argument('--test-only', action='store_true', help='Run native fixture suites without game files')
    parser.add_argument('--experimental-shop', action='store_true', help='Include experimental 6 by 3 NPC buy-store cards')
    args = parser.parse_args()
    require(args.test_only or args.game is not None, '--game is required unless --test-only is used')
    gcc = shutil.which(args.gcc)
    require(gcc is not None, 'MinGW-w64 x64 GCC not found: ' + args.gcc)
    prepare(offline=True)
    output = output_directory(args.out, args.game)
    if args.test_only:
        test(output, gcc, MINHOOK)
    else:
        build(args.game.resolve(), output, gcc, args.experimental_shop)


if __name__ == '__main__':
    main()
