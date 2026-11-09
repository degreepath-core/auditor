import json
import pathlib

import pytest

from dp.fixtures.errors import FixtureError
from dp.fixtures.runner import (
    ExpectationMismatch, audit_fixture, discover_students, load_fixture, render_snapshot, snapshot_path, verify_fixture,
)

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


def test_verify_reports_a_wrong_outcome_as_a_mismatch(root: pathlib.Path):
    (root / 'students' / 't100-tiny.yaml').write_text(STUDENT.replace('{status: done}', '{status: empty}'))
    fixture = load_fixture(root / 'students' / 't100-tiny.yaml', areas_root=root / 'areas')
    with pytest.raises(ExpectationMismatch, match="status: expected 'empty', got 'done'"):
        verify_fixture(fixture, 'T100', areas_root=root / 'areas')


def test_verify_reports_a_broken_fixture_as_a_fixture_error_not_a_mismatch(root: pathlib.Path):
    # A typo'd requirement name must not look like the known engine bug a
    # strict xfail is waiting for; it has to fail the test outright.
    typo = STUDENT.replace('{status: done}', "{status: empty, requirements: {Capstnoe: done}, known_issue: 'x'}")
    (root / 'students' / 't100-tiny.yaml').write_text(typo)
    fixture = load_fixture(root / 'students' / 't100-tiny.yaml', areas_root=root / 'areas')
    with pytest.raises(FixtureError, match="requirement\\(s\\) \\['Capstnoe'\\] not found") as info:
        verify_fixture(fixture, 'T100', areas_root=root / 'areas')
    assert not isinstance(info.value, ExpectationMismatch)


def test_expand_all_by_stnum_pipes_into_batch(root: pathlib.Path, tmp_path: pathlib.Path):
    import subprocess
    import sys

    out = tmp_path / 'out'
    expanded = subprocess.run(
        [sys.executable, '-m', 'dp.bin.fixture', '--root', str(root), 'expand-all', '--by-stnum', '--out', str(out)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True,
    )
    fixture = load_fixture(root / 'students' / 't100-tiny.yaml', areas_root=root / 'areas')
    stnum = fixture.student['stnum']
    assert expanded.stdout == f'{stnum} 2020 T100\n'
    assert (out / f'{stnum}.json').exists()

    batch = subprocess.run(
        [sys.executable, '-m', 'dp.bin.batch', '--dir', str(out), '--areas-dir', str(root / 'areas')],
        input=expanded.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )
    assert batch.returncode == 0, batch.stderr
    assert "'Fixture: tiny' audit status: done" in batch.stdout
