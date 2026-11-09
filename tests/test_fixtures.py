"""Audit every fixture student against its fixture areas.

See fixtures/README.md. Refresh snapshots after an intended change with:

    pytest tests/test_fixtures.py --update-snapshots
"""

import difflib

import pytest
import yaml

from dp import AreaOfStudy, Constants
from dp.fixtures.errors import FixtureError
from dp.fixtures.runner import (
    FIXTURES_ROOT, ExpectationMismatch, discover_students, load_fixture, render_snapshot, snapshot_path, verify_fixture,
)

AREAS_ROOT = FIXTURES_ROOT / 'areas'
SNAPSHOTS_ROOT = FIXTURES_ROOT / 'snapshots'
UPDATE_HINT = 'run `pytest tests/test_fixtures.py --update-snapshots` if this change is intended'


def _collect():
    cases = []
    load_errors = []
    snapshot_names = set()

    for path in discover_students(FIXTURES_ROOT):
        try:
            fixture = load_fixture(path, areas_root=AREAS_ROOT)
        except FixtureError as e:
            load_errors.append(pytest.param(str(e), id=path.stem))
            continue

        for code, expectation in sorted(fixture.expectations.items()):
            marks = []
            if expectation.known_issue:
                marks.append(pytest.mark.xfail(reason=expectation.known_issue, strict=True, raises=ExpectationMismatch))
            else:
                snapshot_names.add(snapshot_path(FIXTURES_ROOT, fixture.id, code).name)
            cases.append(pytest.param(fixture, code, id=f'{fixture.id}[{code}]', marks=marks))

    return cases, load_errors, snapshot_names


CASES, LOAD_ERRORS, SNAPSHOT_NAMES = _collect()
AREA_FILES = sorted(AREAS_ROOT.glob('*/*.yaml'))


def test_fixture_corpus_exists():
    assert CASES, f'no fixture students found under {FIXTURES_ROOT / "students"}'
    assert AREA_FILES, f'no fixture areas found under {AREAS_ROOT}'


@pytest.mark.parametrize('error', LOAD_ERRORS)
def test_fixture_student_loads(error):
    pytest.fail(error)


@pytest.mark.parametrize('path', AREA_FILES, ids=lambda p: f'{p.parent.name}/{p.name}')
def test_fixture_area_is_valid(path):
    with open(path, 'r', encoding='utf-8') as infile:
        spec = yaml.load(stream=infile, Loader=yaml.SafeLoader)

    assert str(spec['code']) == path.stem, f'{path}: code {spec["code"]!r} does not match the filename'
    assert str(spec['code']).startswith('T'), f'{path}: fixture area codes must start with T'
    assert str(spec['name']).startswith('Fixture:'), f'{path}: fixture area names must start with "Fixture:"'

    AreaOfStudy.load(specification=spec, c=Constants(matriculation_year=200))


@pytest.mark.parametrize('fixture,code', CASES)
def test_fixture(fixture, code, request):
    expectation = fixture.expectations[code]
    result = verify_fixture(fixture, code, areas_root=AREAS_ROOT)

    if expectation.known_issue:
        return

    path = snapshot_path(FIXTURES_ROOT, fixture.id, code)
    rendered = render_snapshot(result)

    if request.config.getoption('--update-snapshots'):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding='utf-8')
        return

    if not path.exists():
        pytest.fail(f'no snapshot at {path}; {UPDATE_HINT}')

    stored = path.read_text(encoding='utf-8')
    if stored != rendered:
        diff = ''.join(difflib.unified_diff(
            stored.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=str(path),
            tofile='current audit',
        ))
        pytest.fail(f'snapshot mismatch for {fixture.id}[{code}]:\n{diff}\n{UPDATE_HINT}')


def test_no_orphaned_snapshots(request):
    if LOAD_ERRORS:
        pytest.skip('a fixture failed to load, so the expected snapshot set is incomplete')

    orphans = sorted(p for p in SNAPSHOTS_ROOT.glob('*.json') if p.name not in SNAPSHOT_NAMES)

    if request.config.getoption('--update-snapshots'):
        for orphan in orphans:
            orphan.unlink()
        return

    assert not orphans, f'snapshots with no matching fixture: {[p.name for p in orphans]}; {UPDATE_HINT}'


def test_known_issues_only_excuse_expectation_mismatches():
    xfails = [m for case in CASES for m in case.marks if m.name == 'xfail']
    assert xfails, 'expected at least one known_issue fixture'
    for mark in xfails:
        assert mark.kwargs.get('raises') is ExpectationMismatch
        assert mark.kwargs.get('strict') is True
