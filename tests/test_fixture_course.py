import pytest

from dp.data.course import load_course
from dp.fixtures.course import expand_course, parse_course
from dp.fixtures.errors import FixtureError


def test_defaults_for_a_plain_course():
    c = parse_course('CSCI 251 2019-1 B+')
    assert c['subject'] == 'CSCI'
    assert c['number'] == '251'
    assert c['section'] == ''
    assert c['year'] == 2019
    assert c['term'] == '1'
    assert c['grade_code'] == 'B+'
    assert c['grade_option'] == 'grade'
    assert c['grade_points'] == '3.30'
    assert c['flag_gpa'] is True
    assert c['flag_stolaf'] is True
    assert c['course_type'] == 'SE'
    assert c['institution_short'] == 'STOLAF'
    assert c['credits'] == '1.00'
    assert c['level'] == 200
    assert c['name'] == 'CSCI 251'
    assert c['crsid'] == 'CSCI 251'
    assert c['clbid'] == 'CSCI 251 2019-1'


def test_every_expanded_course_loads():
    for text in [
        'CSCI 251 2019-1 B+',
        'CSCI 251.A 2019-2 A',
        'CSCI 125 2019-3 S su=C',
        'CSCI 125 2019-4 P',
        'CSCI 399 2020-3 IP',
        'CHEM 121 2019-1 A lab credits=0.00',
        'CSCI 121 2017-3 A ap',
        'CSCI 241 2019-1 B transfer inst=CARL',
        'CSCI 241 2018-3 D repeated-later',
        'CSCI 241 2019-1 A repeat gereqs=WRI,FYW attrs=csci_elective "name=Hardware Design" level=300',
    ]:
        load_course(parse_course(text), overrides=[], credits_overrides={})


def test_section_and_term_types():
    assert parse_course('CSCI 251.A 2019-2 A')['section'] == 'A'
    assert parse_course('CSCI 251.A 2019-2 A')['clbid'] == 'CSCI 251.A 2019-2'
    assert parse_course('CSCI 251 2019-2 A')['course_type'] == 'IN'
    assert parse_course('CSCI 251 2019-4 A')['course_type'] == 'SM'


def test_grade_options_follow_the_grade():
    su = parse_course('CSCI 125 2019-3 S su=C')
    assert (su['grade_option'], su['su_grade_code'], su['flag_gpa']) == ('s/u', 'C', False)
    assert parse_course('CSCI 125 2019-3 N')['grade_option'] == 'p/n'
    ip = parse_course('CSCI 399 2020-3 IP')
    assert (ip['flag_in_progress'], ip['flag_gpa'], ip['grade_points']) == (True, False, '0.00')


def test_flags():
    t = parse_course('CSCI 241 2019-1 B transfer')
    assert (t['course_type'], t['flag_stolaf'], t['institution_short']) == ('TR', False, 'XFER')
    assert parse_course('CSCI 241 2019-1 B transfer inst=CARL')['institution_short'] == 'CARL'
    assert parse_course('CSCI 241 2019-1 B inst=CARL transfer')['institution_short'] == 'CARL'
    ap = parse_course('CSCI 121 2017-3 A ap')
    assert (ap['course_type'], ap['flag_stolaf'], ap['institution_short']) == ('AP', False, 'AP')
    assert parse_course('CSCI 241 2018-3 D repeated-later')['transcript_code'] == 'R'
    assert parse_course('CSCI 241 2019-1 A repeat')['flag_repeat'] is True
    assert parse_course('CSCI 241 2019-1 I incomplete')['flag_incomplete'] is True
    lab = parse_course('CHEM 121 2019-1 A lab credits=0.00')
    assert (lab['sub_type'], lab['credits'], lab['clbid']) == ('lab', '0.00', 'CHEM 121.L 2019-1')
    full = parse_course('CSCI 241 2019-1 A gereqs=WRI,FYW attrs=csci_elective "name=Hardware Design" level=300')
    assert full['gereqs'] == ['WRI', 'FYW']
    assert full['attributes'] == ['csci_elective']
    assert full['name'] == 'Hardware Design'
    assert full['level'] == 300


def test_clbid_is_stable_across_calls():
    assert parse_course('CSCI 251 2019-1 B')['clbid'] == parse_course('CSCI 251 2019-1 A')['clbid']


def test_mapping_overrides_fields():
    c = expand_course({'course': 'CSCI 390 2020-3 B', 'gereqs': ['WRI'], 'name': 'Capstone', 'credits': '0.50'})
    assert (c['gereqs'], c['name'], c['credits'], c['subject']) == (['WRI'], 'Capstone', '0.50', 'CSCI')


@pytest.mark.parametrize('entry,message', [
    ('CSCI 251 2019-1', "expected 'SUBJ NUM YEAR-TERM GRADE"),
    ('csci 251 2019-1 B', 'upper-case'),
    ('CSCI two 2019-1 B', 'must look like 251'),
    ('CSCI 251 2019-9 B', 'terms 1-5'),
    ('CSCI 251 2019-1 Q', "unknown grade 'Q'"),
    ('CSCI 251 2019-1 B shiny', "unknown flag 'shiny'"),
    ('CSCI 251 2019-1 B transfer=yes', 'does not take a value'),
    ('CSCI 251 2019-1 B credits=', 'needs a value'),
    ('CSCI 251 2019-1 B credits=lots', 'not a number'),
    ('CSCI 251 2019-1 B su=C', 'only applies to an S or U'),
    ('CSCI 251 2019-1 S su=S', 'must be a letter grade'),
    ('CSCI 251 2019-1 B level=high', 'must be an integer'),
    ('CSCI 251 2019-1 B "name=unclosed', 'No closing quotation'),
    ({'gereqs': ['WRI']}, "no 'course' key"),
    ({'course': 'CSCI 251 2019-1 B', 'colour': 'red'}, 'unknown field(s): colour'),
    (42, 'must be a string or a mapping'),
])
def test_errors_name_the_problem(entry, message):
    with pytest.raises(FixtureError, match=None) as info:
        expand_course(entry)
    assert message in str(info.value)
