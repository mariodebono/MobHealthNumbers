"""Test and package the standalone addon without touching any game installation."""
from pathlib import Path
import argparse
import hashlib
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ADDON = 'MobHealthNumbers'
FILES = (
    'MobHealthNumbers.toc', 'HealthLearner.lua', 'MobHealthNumbers.lua',
    'Options.lua', 'README.md', 'CREDITS.md', 'LICENSE.txt', 'FEATURES.md',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--github-output', type=Path, help='Write release metadata to a GitHub Actions output file.')
    args = parser.parse_args()
    toc = (ROOT / 'MobHealthNumbers.toc').read_text(encoding='utf-8')
    match = re.search(r'^## Version:\s*([0-9A-Za-z][0-9A-Za-z.+-]*)\s*$', toc, re.MULTILINE)
    if not match:
        raise ValueError('The TOC must contain a version suitable for a ZIP filename.')
    version = match.group(1)
    for line in toc.splitlines():
        if line.endswith('.lua') and line not in FILES:
            raise ValueError(f'TOC entry is missing from the package allowlist: {line}')

    subprocess.run(
        [sys.executable, '-B', str(ROOT / 'tests/test_mob_health.py')],
        cwd=ROOT, check=True,
    )
    entries = {f'{ADDON}/{name}': (ROOT / name).read_bytes() for name in FILES}
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / f'{ADDON}-{version}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as release:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            release.writestr(info, data)
    with zipfile.ZipFile(archive) as release:
        if release.testzip() is not None or set(release.namelist()) != set(entries):
            raise RuntimeError('ZIP integrity or package allowlist verification failed.')
        for name, expected in entries.items():
            if release.read(name) != expected:
                raise RuntimeError(f'Packaged content differs from source: {name}')
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = output / f'{archive.name}.sha256'
    checksum.write_text(
        f'{digest}  {archive.name}\n', encoding='utf-8',
    )
    if args.github_output:
        with args.github_output.open('a', encoding='utf-8') as handle:
            handle.write(f'version={version}\ntag=v{version}\n')
            handle.write(f'archive={archive.relative_to(ROOT).as_posix()}\n')
            handle.write(f'checksum={checksum.relative_to(ROOT).as_posix()}\n')
    print(f'Built {archive}')
    print(f'SHA256: {digest}')


if __name__ == '__main__':
    main()
