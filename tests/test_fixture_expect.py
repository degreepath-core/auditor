import pytest

from dp.fixtures.errors import FixtureError
from dp.fixtures.expect import AreaExpectation, check_expectation, parse_expectations, requirement_statuses

RESULT = {
    'type': 'area', 'status': 'needs-more-items', 'gpa': '3.25', 'path': ['$'],
    'result': {
        'type': 'count', 'path': ['$', '.count'],
        'items': [
            {'type': 'requirement', 'path': ['$', '.count', '[0]', '%Core'], 'status': 'done',
             'result': {'type': 'requirement', 'path': ['$', '.count', '[0]', '%Core', '%Lab'], 'status': 'empty', 'result': None}},
            {'type': 'requirement', 'path': ['$', '.count', '[1]', '%Electives'], 'status': 'needs-more-items', 'result': None},
        ],
    },
}


def test_requirement_statuses_walks_nested_requirements():
    assert requirement_statuses(RESULT) == {'Core': 'done', 'Core/Lab': 'empty', 'Electives': 'needs-more-items'}


def test_parse_minimal_and_full():
    parsed = parse_expectations(
        {'T100': {'status': 'done'}, 'T200': {'status': 'empty', 'gpa': '3.00', 'requirements': {'A': 'done'}, 'known_issue': 'bug'}},
        area_codes=['T100', 'T200'], fixture_id='x',
    )
    assert parsed['T100'] == AreaExpectation(status='done')
    assert parsed['T200'] == AreaExpectation(status='empty', gpa='3.00', requirements={'A': 'done'}, known_issue='bug')


@pytest.mark.parametrize('raw,message', [
    (None, "'expect' must be a mapping"),
    ({'T999': {'status': 'done'}}, "'areas' declares ['T100']"),
    ({'T100': 'done'}, 'expect.T100 must be a mapping'),
    ({'T100': {'status': 'finished'}}, "expect.T100.status must be one of"),
    ({'T100': {'status': 'done', 'gpa': 3.25}}, 'must be a quoted string'),
    ({'T100': {'status': 'done', 'gpa': 'high'}}, 'is not a number'),
    ({'T100': {'status': 'done', 'requirements': ['Core']}}, 'requirements must be a mapping'),
    ({'T100': {'status': 'done', 'requirements': {'Core': 'ok'}}}, "requirements['Core'] must be one of"),
    ({'T100': {'status': 'done', 'known_issue': ''}}, 'known_issue must be a non-empty description'),
    ({'T100': {'status': 'done', 'note': 'hi'}}, 'unknown key(s): note'),
])
def test_parse_errors(raw, message):
    with pytest.raises(FixtureError) as info:
        parse_expectations(raw, area_codes=['T100'], fixture_id='x')
    assert message in str(info.value)


def test_check_passes_when_everything_listed_matches():
    exp = AreaExpectation(status='needs-more-items', gpa='3.250', requirements={'Core/Lab': 'empty'})
    assert check_expectation(exp, RESULT) == []


def test_check_reports_each_mismatch():
    exp = AreaExpectation(status='done', gpa='4.00', requirements={'Core': 'empty', 'Capstone': 'done'})
    problems = check_expectation(exp, RESULT)
    assert problems == [
        "status: expected 'done', got 'needs-more-items'",
        'gpa: expected 4.00, got 3.25',
        "requirement 'Capstone' not found; available: ['Core', 'Core/Lab', 'Electives']",
        "requirement 'Core': expected 'empty', got 'done'",
    ]
