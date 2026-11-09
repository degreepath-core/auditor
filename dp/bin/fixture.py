"""Expand fixture students into standard student JSON.

    python3 -m dp.bin.fixture expand fixtures/students/t100-complete.yaml
    python3 -m dp.bin.fixture expand-all --out build/fixture-students
"""

import argparse
import json
import pathlib
import sys

from dp.fixtures.errors import FixtureError
from dp.fixtures.runner import FIXTURES_ROOT, discover_students, load_fixture


def main() -> int:
    parser = argparse.ArgumentParser(description='Expand fixture students into standard student JSON.')
    parser.add_argument('--root', default=str(FIXTURES_ROOT), help='the fixtures directory (default: %(default)s)')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    parser_expand = subparsers.add_parser('expand', help='print one fixture student as student JSON')
    parser_expand.add_argument('student', help='a fixture student .yaml file')

    parser_all = subparsers.add_parser('expand-all', help='write every fixture student as <id>.json')
    parser_all.add_argument('--out', required=True, help='the output directory')

    args = parser.parse_args()

    root = pathlib.Path(args.root)
    areas_root = root / 'areas'

    try:
        if args.command == 'expand':
            fixture = load_fixture(pathlib.Path(args.student), areas_root=areas_root)
            print(json.dumps(fixture.student, sort_keys=True, indent=2))
        else:
            out = pathlib.Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            for path in discover_students(root):
                fixture = load_fixture(path, areas_root=areas_root)
                target = out / f'{fixture.id}.json'
                target.write_text(json.dumps(fixture.student, sort_keys=True, indent=2) + '\n', encoding='utf-8')
                print(target, file=sys.stderr)
    except FixtureError as e:
        print(f'error: {e}', file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
