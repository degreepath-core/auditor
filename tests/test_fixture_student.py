import pathlib

import pytest

from dp.data.student import Student
from dp.fixtures.errors import FixtureError
from dp.fixtures.student import default_stnum, expand_student

MINIMAL = {'areas': [{'code': 'T100', 'kind': 'concentration', 'degree': 'B.A.'}]}


def test_minimal_student_gets_defaults():
    s = expand_student(MINIMAL, fixture_id='t100-example')
    assert s['stnum'] == default_stnum('t100-example')
    assert len(s['stnum']) == 6 and s['stnum'].startswith('9')
    assert (s['catalog'], s['curriculum'], s['matriculation']) == (2020, 2020, 2018)
    assert s['areas'] == [{'code': 'T100', 'kind': 'concentration', 'degree': 'B.A.', 'status': 'declared', 'name': 'T100'}]
    assert s['courses'] == []
    assert 'expect' not in s


def test_expanded_student_loads():
    data = dict(MINIMAL, current_term='20201', courses=['DEPT 101 2018-1 A', 'DEPT 399 2020-3 IP'])
    s = expand_student(data, fixture_id='t100-example')
    loaded = Student.load(s, code='T100')
    assert [c.course() for c in loaded.courses] == ['DEPT 101', 'DEPT 399']
    assert loaded.courses[1].is_in_progress_in_future is True


def test_area_name_comes_from_the_area_file(tmp_path: pathlib.Path):
    (tmp_path / '2020-21').mkdir()
    (tmp_path / '2020-21' / 'T100.yaml').write_text('name: "Fixture: course rules"\ncode: T100\n')
    s = expand_student(MINIMAL, fixture_id='x', areas_root=tmp_path)
    assert s['areas'][0]['name'] == 'Fixture: course rules'


def test_passthrough_keys_are_copied():
    exceptions = [{'area_code': 'T100', 'type': 'override', 'path': ['$']}]
    s = expand_student(dict(MINIMAL, exceptions=exceptions, current_term='20193'), fixture_id='x')
    assert s['exceptions'] == exceptions
    assert s['current_term'] == '20193'


@pytest.mark.parametrize('data,message', [
    ([], 'must be a mapping'),
    (dict(MINIMAL, favourite_colour='red'), 'unknown top-level key(s): favourite_colour'),
    (dict(MINIMAL, catalog=2019), 'catalog must be an integer year >= 2020'),
    (dict(MINIMAL, catalog='2020'), 'catalog must be an integer year'),
    ({}, "'areas' must be a non-empty list"),
    ({'areas': [{'code': 'T100', 'kind': 'concentration'}]}, "missing 'degree'"),
    ({'areas': [{'code': 'T100', 'kind': 'hobby', 'degree': 'B.A.'}]}, "'hobby' is not a valid AreaType"),
    ({'areas': [{'code': 'T100', 'kind': 'major', 'degree': 'B.A.', 'colour': 'red'}]}, 'unknown key(s): colour'),
    (dict(MINIMAL, courses='DEPT 101 2018-1 A'), "'courses' must be a list"),
    (dict(MINIMAL, courses=['DEPT 101 2018-1 A', 'DEPT 101 2018-1 Q']), 'courses[1]'),
    (dict(MINIMAL, courses=['DEPT 101 2018-1 A', 'DEPT 101 2018-1 B']), 'same clbid'),
])
def test_errors_name_the_problem(data, message):
    with pytest.raises(FixtureError) as info:
        expand_student(data, fixture_id='t100-example')
    assert message in str(info.value)
    assert 't100-example' in str(info.value)
