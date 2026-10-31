"""Audit the exact tracked and staged publication allowlist without printing file contents."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT = ['git', '-c', 'safe.directory=' + ROOT.as_posix()]
SECRET = re.compile(rb'(?i)(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
FORBIDDEN = {'.exe','.dll','.asi','.paz','.pamt','.papgt','.uibinary','.thtml','.png','.jpg','.jpeg','.webp','.zip','.7z','.log','.pyc'}
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp'}


def audit_file(name, data):
    """Check a staged file; documentation images retain the exact-path allowlist."""
    path = Path(name)
    if path.parts[:2] == ('docs', 'images') and path.suffix.lower() in IMAGE_SUFFIXES:
        if not 0 < len(data) <= 8 * 1024 * 1024:
            raise SystemExit('Documentation image exceeds 8 MiB or is empty: ' + name)
        suffix = path.suffix.lower()
        signatures = {
            '.png': data.startswith(b'\x89PNG\r\n\x1a\n') and data.endswith(b'\x00\x00\x00\x00IEND\xaeB`\x82'),
            '.jpg': data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9'),
            '.jpeg': data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9'),
            '.webp': data.startswith(b'RIFF') and data[8:12] == b'WEBP' and int.from_bytes(data[4:8], 'little') + 8 == len(data),
        }
        if not signatures[suffix]:
            raise SystemExit('Documentation image has an unexpected file signature: ' + name)
        return 'image'
    if path.suffix.lower() in FORBIDDEN or name.split('/')[0] in ('build','research','tools','.deps','.venv'):
        raise SystemExit('Forbidden tracked file: ' + name)
    if len(data) > 262144 or b'\0' in data:
        raise SystemExit('Large or binary staged file: ' + name)
    data.decode('utf-8')
    if SECRET.search(data):
        raise SystemExit('Possible credential in staged file: ' + name)
    if re.search(rb'(?i)https?://[^\s/]+:[^\s/@]+@', data):
        raise SystemExit('Credential-bearing URL in staged file: ' + name)
    return 'text'


def main():
    allowed = {line.strip() for line in (ROOT / 'tracked-files.txt').read_text().splitlines() if line.strip()}
    tracked = set(subprocess.check_output(GIT + ['ls-files','-z'], cwd=ROOT).decode().strip('\0').split('\0')) - {''}
    if tracked != allowed:
        raise SystemExit(f'Allowlist mismatch: unexpected={sorted(tracked-allowed)} missing={sorted(allowed-tracked)}')
    total = 0
    images = 0
    for name in sorted(tracked):
        data = subprocess.check_output(GIT + ['show',':'+name], cwd=ROOT)
        images += audit_file(name, data) == 'image'
        total += len(data)
    print(f'PASS: {len(tracked)-images} text files, {images} documentation images, {total} bytes; exact allowlist, size, image signature, binary, path, and text credential checks.')


if __name__ == '__main__':
    main()
