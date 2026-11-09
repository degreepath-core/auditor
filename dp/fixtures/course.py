"""Expand the one-line course short form into the auditor's course JSON."""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping, Union
import re
import shlex

from ..data.course_enums import GradeCode
from ..lib import str_to_grade_points
from .errors import FixtureError

# Every key load_course() reads, plus the two it reads optionally.
COURSE_FIELDS = frozenset({
    'attributes', 'clbid', 'course_type', 'credits', 'crsid', 'flag_gpa',
    'flag_in_progress', 'flag_incomplete', 'flag_repeat', 'flag_stolaf',
    'gereqs', 'grade_code', 'grade_option', 'grade_points', 'institution_short',
    'level', 'name', 'number', 'schedid', 'section', 'su_grade_code', 'sub_type',
    'subject', 'term', 'transcript_code', 'year',
})

LETTER_GRADES = frozenset({'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F'})
VALID_GRADES = frozenset(g.value for g in GradeCode)

_SUBJECT_RE = re.compile(r'^[A-Z][A-Z/]*$')
_NUMBER_RE = re.compile(r'^(?P<number>\d+[A-Z]*)(?:\.(?P<section>[A-Z0-9]+))?$')
_YEARTERM_RE = re.compile(r'^(?P<year>\d{4})-(?P<term>[1-5])$')

_TERM_COURSE_TYPE = {'1': 'SE', '2': 'IN', '3': 'SE', '4': 'SM', '5': 'SM'}
_GRADE_OPTIONS = {'S': 's/u', 'U': 's/u', 'P': 'p/n', 'N': 'p/n'}

BOOLEAN_FLAGS = frozenset({'transfer', 'ap', 'incomplete', 'repeat', 'repeated-later', 'lab'})
VALUE_FLAGS = frozenset({'su', 'credits', 'gereqs', 'attrs', 'inst', 'name', 'level'})


def expand_course(entry: Union[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """Expand a short-form string, or a mapping of {course: <string>, **field overrides}."""
    if isinstance(entry, str):
        return parse_course(entry)

    if isinstance(entry, Mapping):
        if 'course' not in entry:
            raise FixtureError(f"course mapping {dict(entry)!r} has no 'course' key")

        course = parse_course(str(entry['course']))
        overrides = {k: v for k, v in entry.items() if k != 'course'}

        unknown = sorted(set(overrides) - COURSE_FIELDS)
        if unknown:
            raise FixtureError(f"course {entry['course']!r}: unknown field(s): {', '.join(unknown)}")

        course.update(overrides)
        return course

    raise FixtureError(f"a course must be a string or a mapping; got {type(entry).__name__}: {entry!r}")


def parse_course(text: str) -> Dict[str, Any]:
    """Parse 'SUBJ NUM[.SECTION] YEAR-TERM GRADE [flag ...]' into course JSON."""
    try:
        tokens = shlex.split(text)
    except ValueError as e:
        raise FixtureError(f"course {text!r}: {e}") from e

    if len(tokens) < 4:
        raise FixtureError(f"course {text!r}: expected 'SUBJ NUM YEAR-TERM GRADE [flag ...]'")

    subject, number_token, yearterm, grade = tokens[:4]

    if not _SUBJECT_RE.match(subject):
        raise FixtureError(f"course {text!r}: subject {subject!r} must be upper-case letters")

    number_match = _NUMBER_RE.match(number_token)
    if not number_match:
        raise FixtureError(f"course {text!r}: number {number_token!r} must look like 251 or 251.A")
    number = number_match.group('number')
    section = number_match.group('section') or ''

    yearterm_match = _YEARTERM_RE.match(yearterm)
    if not yearterm_match:
        raise FixtureError(f"course {text!r}: term {yearterm!r} must look like 2019-1 (terms 1-5)")
    year = int(yearterm_match.group('year'))
    term = yearterm_match.group('term')

    if grade not in VALID_GRADES:
        raise FixtureError(f"course {text!r}: unknown grade {grade!r}")

    course: Dict[str, Any] = {
        'attributes': [],
        'clbid': '',
        'course_type': _TERM_COURSE_TYPE[term],
        'credits': '1.00',
        'crsid': f'{subject} {number}',
        'flag_gpa': grade in LETTER_GRADES,
        'flag_in_progress': grade == 'IP',
        'flag_incomplete': False,
        'flag_repeat': False,
        'flag_stolaf': True,
        'gereqs': [],
        'grade_code': grade,
        'grade_option': _GRADE_OPTIONS.get(grade, 'grade'),
        'grade_points': str(str_to_grade_points(grade)),
        'institution_short': 'STOLAF',
        'level': int(re.sub(r'\D.*$', '', number)) // 100 * 100,
        'name': f'{subject} {number}',
        'number': number,
        'section': section,
        'sub_type': '',
        'subject': subject,
        'term': term,
        'transcript_code': '',
        'year': year,
    }

    for flag in tokens[4:]:
        _apply_flag(course, flag, text=text)

    suffix = (f'.{section}' if section else '') + ('.L' if course['sub_type'] == 'lab' else '')
    course['clbid'] = f'{subject} {number}{suffix} {year}-{term}'

    return course


def _apply_flag(course: Dict[str, Any], flag: str, *, text: str) -> None:  # noqa: C901
    key, has_value, value = flag.partition('=')

    if key in BOOLEAN_FLAGS:
        if has_value:
            raise FixtureError(f"course {text!r}: flag {key!r} does not take a value")
    elif key in VALUE_FLAGS:
        if not has_value or not value:
            raise FixtureError(f"course {text!r}: flag {key!r} needs a value, like {key}=...")
    else:
        raise FixtureError(f"course {text!r}: unknown flag {flag!r}")

    if key == 'transfer':
        course['course_type'] = 'TR'
        course['flag_stolaf'] = False
        if course['institution_short'] == 'STOLAF':
            course['institution_short'] = 'XFER'
    elif key == 'ap':
        course['course_type'] = 'AP'
        course['flag_stolaf'] = False
        if course['institution_short'] == 'STOLAF':
            course['institution_short'] = 'AP'
    elif key == 'incomplete':
        course['flag_incomplete'] = True
    elif key == 'repeat':
        course['flag_repeat'] = True
    elif key == 'repeated-later':
        course['transcript_code'] = 'R'
    elif key == 'lab':
        course['sub_type'] = 'lab'
    elif key == 'su':
        if course['grade_code'] not in ('S', 'U'):
            raise FixtureError(f"course {text!r}: su= only applies to an S or U grade")
        if value not in LETTER_GRADES:
            raise FixtureError(f"course {text!r}: su={value!r} must be a letter grade")
        course['su_grade_code'] = value
    elif key == 'credits':
        try:
            Decimal(value)
        except InvalidOperation:
            raise FixtureError(f"course {text!r}: credits={value!r} is not a number") from None
        course['credits'] = value
    elif key == 'gereqs':
        course['gereqs'] = value.split(',')
    elif key == 'attrs':
        course['attributes'] = value.split(',')
    elif key == 'inst':
        course['institution_short'] = value
    elif key == 'name':
        course['name'] = value
    elif key == 'level':
        if not value.isdigit():
            raise FixtureError(f"course {text!r}: level={value!r} must be an integer")
        course['level'] = int(value)
