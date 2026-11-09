import json
import pathlib

import pytest

from dp.fixtures.errors import FixtureError
from dp.fixtures.runner import audit_fixture, discover_students, load_fixture, render_snapshot, snapshot_path

AREA = '''
name: "Fixture: tiny"
type: concentration
code: T100
degree: B.A.
result:
  all:
    - course: DEPT 101
'''

STUDENT = '''
areas: [{code: T100, kind: concentration, degree: B.A.}]
courses: [DEPT 101 2020-1 A]
expect:
  T100: {status: done}
'''


@pytest.fixture
def root(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / 'areas' / '2020-21').mkdir(parents=True)
    (tmp_path / 'areas' / '2020-21' / 'T100.yaml').write_text(AREA)
    (tmp_path / 'students').mkdir()
    (tmp_path / 'students' / 't100-tiny.yaml').write_text(STUDENT)
    return tmp_path


def test_load_and_audit(root: pathlib.Path):
    [path] = discover_students(root)
    fixture = load_fixture(path, areas_root=root / 'areas')
    assert fixture.id == 't100-tiny'
    assert fixture.student['areas'][0]['name'] == 'Fixture: tiny'
    assert fixture.expectations['T100'].status == 'done'

    result = audit_fixture(fixture, 'T100', areas_root=root / 'areas')
    assert result['status'] == 'done'
    rendered = render_snapshot(result)
    assert rendered.endswith('}\n')
    assert render_snapshot(json.loads(rendered)) == rendered


def test_missing_area_is_an_error_not_a_placeholder(root: pathlib.Path):
    (root / 'areas' / '2020-21' / 'T100.yaml').unlink()
    fixture = load_fixture(root / 'students' / 't100-tiny.yaml', areas_root=root / 'areas')
    with pytest.raises(FixtureError, match="no fixture area 'T100'"):
        audit_fixture(fixture, 'T100', areas_root=root / 'areas')


def test_unreadable_and_invalid_files(root: pathlib.Path):
    with pytest.raises(FixtureError, match='cannot read'):
        load_fixture(root / 'students' / 'missing.yaml', areas_root=root / 'areas')

    (root / 'students' / 'broken.yaml').write_text('areas: [unclosed\n')
    with pytest.raises(FixtureError, match='invalid YAML'):
        load_fixture(root / 'students' / 'broken.yaml', areas_root=root / 'areas')


def test_snapshot_path(root: pathlib.Path):
    assert snapshot_path(root, 't100-tiny', 'T100') == root / 'snapshots' / 't100-tiny.T100.json'
