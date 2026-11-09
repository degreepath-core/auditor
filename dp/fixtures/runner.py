"""Load fixture files, audit them, and render snapshots."""

from typing import Any, Dict, List
import json
import pathlib

import attr
import yaml

from ..audit import Arguments, NoAuditsCompletedMsg, ResultMsg
from ..run import find_area, load_area, run
from .errors import FixtureError
from .expect import AreaExpectation, parse_expectations
from .student import expand_student

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES_ROOT = REPO_ROOT / 'fixtures'


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class Fixture:
    id: str
    path: pathlib.Path
    student: Dict[str, Any]
    expectations: Dict[str, AreaExpectation]


def discover_students(root: pathlib.Path) -> List[pathlib.Path]:
    return sorted((root / 'students').glob('*.yaml'))


def load_fixture(path: pathlib.Path, *, areas_root: pathlib.Path) -> Fixture:
    fixture_id = path.stem

    try:
        with open(path, 'r', encoding='utf-8') as infile:
            raw = yaml.load(stream=infile, Loader=yaml.SafeLoader)
    except OSError as e:
        raise FixtureError(f"{fixture_id}: cannot read {path}: {e.strerror}") from e
    except yaml.YAMLError as e:
        raise FixtureError(f"{fixture_id}: invalid YAML: {e}") from e

    student = expand_student(raw, fixture_id=fixture_id, areas_root=areas_root)
    codes = [area['code'] for area in student['areas']]
    expectations = parse_expectations(raw.get('expect'), area_codes=codes, fixture_id=fixture_id)

    return Fixture(id=fixture_id, path=path, student=student, expectations=expectations)


def resolve_area(*, areas_root: pathlib.Path, catalog: int, code: str) -> pathlib.Path:
    path = find_area(root=areas_root, area_catalog=catalog, area_code=code)
    if path is None:
        raise FixtureError(f"no fixture area {code!r} exists under {areas_root} for catalog {catalog}")
    return path


def audit_fixture(fixture: Fixture, code: str, *, areas_root: pathlib.Path) -> Dict[str, Any]:
    """Audit one declared area of a fixture student; return the area result's to_dict()."""
    area_path = resolve_area(areas_root=areas_root, catalog=fixture.student['catalog'], code=code)
    area_spec = load_area(area_path)

    final = None
    for msg in run(Arguments(), student=fixture.student, area_spec=area_spec):
        if isinstance(msg, NoAuditsCompletedMsg):
            raise FixtureError(f"{fixture.id}[{code}]: the audit completed no solutions")
        if isinstance(msg, ResultMsg):
            final = msg

    if final is None:
        raise FixtureError(f"{fixture.id}[{code}]: the audit produced no result")

    return final.result.to_dict()


def snapshot_path(root: pathlib.Path, fixture_id: str, code: str) -> pathlib.Path:
    return root / 'snapshots' / f'{fixture_id}.{code}.json'


def render_snapshot(result: Dict[str, Any]) -> str:
    return json.dumps(result, sort_keys=True, indent=2) + '\n'
