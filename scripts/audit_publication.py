"""Audit the exact tracked and staged publication allowlist without printing file contents."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT = ['git', '-c', 'safe.directory=' + ROOT.as_posix()]
SECRET = re.compile(rb'(?i)(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
FORBIDDEN = {'.exe','.dll','.asi','.paz','.pamt','.papgt','.uibinary','.thtml','.png','.jpg','.zip','.7z','.log','.pyc'}


def main():
    allowed = {line.strip() for line in (ROOT / 'tracked-files.txt').read_text().splitlines() if line.strip()}
    tracked = set(subprocess.check_output(GIT + ['ls-files','-z'], cwd=ROOT).decode().strip('\0').split('\0')) - {''}
    if tracked != allowed:
        raise SystemExit(f'Allowlist mismatch: unexpected={sorted(tracked-allowed)} missing={sorted(allowed-tracked)}')
    total = 0
    for name in sorted(tracked):
        path = ROOT / name
        if path.suffix.lower() in FORBIDDEN or name.split('/')[0] in ('build','research','tools','.deps','.venv'):
            raise SystemExit('Forbidden tracked file: ' + name)
        data = subprocess.check_output(GIT + ['show',':'+name], cwd=ROOT)
        if len(data) > 262144 or b'\0' in data:
            raise SystemExit('Large or binary staged file: ' + name)
        data.decode('utf-8')
        if SECRET.search(data):
            raise SystemExit('Possible credential in staged file: ' + name)
        if re.search(rb'(?i)https?://[^\s/]+:[^\s/@]+@', data):
            raise SystemExit('Credential-bearing URL in staged file: ' + name)
        total += len(data)
    print(f'PASS: {len(tracked)} tracked text files, {total} bytes; exact allowlist, size, binary, path, and credential checks.')


if __name__ == '__main__':
    main()
