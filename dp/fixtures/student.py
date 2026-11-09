"""Expand a fixture student (short form) into the auditor's student JSON."""

from typing import Any, Dict, List, Mapping, Optional
import pathlib
import zlib

import yaml

from ..data.area_enums import AreaStatus, AreaType
from ..run import find_area
from .course import expand_course
from .errors import FixtureError

STUDENT_KEYS = frozenset({
    'stnum', 'catalog', 'curriculum', 'matriculation', 'current_term', 'areas', 'courses', 'expect',
    'exceptions', 'templates', 'performances', 'performance_attendances', 'proficiencies', 'mediums',
})
PASSTHROUGH_KEYS = ('current_term', 'exceptions', 'templates', 'performances', 'performance_attendances', 'proficiencies', 'mediums')
AREA_KEYS = frozenset({'code', 'kind', 'status', 'degree', 'name', 'dept', 'gpa', 'terms_since_declaration'})

DEFAULT_CATALOG = 2020
MIN_CATALOG = 2020


def default_stnum(fixture_id: str) -> str:
    return '9' + str(zlib.crc32(fixture_id.encode('utf-8')) % 100_000).zfill(5)


def expand_student(data: Any, *, fixture_id: str, areas_root: Optional[pathlib.Path] = None) -> Dict[str, Any]:
    """Return standard student JSON (without the `expect` block)."""
    if not isinstance(data, Mapping):
        raise FixtureError(f"{fixture_id}: a fixture student must be a mapping")

    unknown = sorted(set(data) - STUDENT_KEYS)
    if unknown:
        raise FixtureError(f"{fixture_id}: unknown top-level key(s): {', '.join(unknown)}")

    catalog = data.get('catalog', DEFAULT_CATALOG)
    if not isinstance(catalog, int) or isinstance(catalog, bool) or catalog < MIN_CATALOG:
        raise FixtureError(f"{fixture_id}: catalog must be an integer year >= {MIN_CATALOG}; got {catalog!r}")

    areas_raw = data.get('areas')
    if not isinstance(areas_raw, list) or not areas_raw:
        raise FixtureError(f"{fixture_id}: 'areas' must be a non-empty list")
    areas = [_expand_area(a, fixture_id=fixture_id, catalog=catalog, areas_root=areas_root) for a in areas_raw]

    courses_raw = data.get('courses', [])
    if not isinstance(courses_raw, list):
        raise FixtureError(f"{fixture_id}: 'courses' must be a list")

    courses: List[Dict[str, Any]] = []
    seen_clbids: Dict[str, int] = {}
    for i, entry in enumerate(courses_raw):
        try:
            course = expand_course(entry)
        except FixtureError as e:
            raise FixtureError(f"{fixture_id}: courses[{i}]: {e}") from e

        if course['clbid'] in seen_clbids:
            raise FixtureError(
                f"{fixture_id}: courses[{i}] has the same clbid {course['clbid']!r} as courses[{seen_clbids[course['clbid']]}]"
            )
        seen_clbids[course['clbid']] = i
        courses.append(course)

    student: Dict[str, Any] = {
        'stnum': str(data.get('stnum', default_stnum(fixture_id))),
        'catalog': catalog,
        'curriculum': data.get('curriculum', catalog),
        'matriculation': data.get('matriculation', catalog - 2),
        'areas': areas,
        'courses': courses,
    }

    for key in PASSTHROUGH_KEYS:
        if key in data:
            student[key] = data[key]

    return student


def _expand_area(entry: Any, *, fixture_id: str, catalog: int, areas_root: Optional[pathlib.Path]) -> Dict[str, Any]:
    if not isinstance(entry, Mapping):
        raise FixtureError(f"{fixture_id}: each entry in 'areas' must be a mapping")

    unknown = sorted(set(entry) - AREA_KEYS)
    if unknown:
        raise FixtureError(f"{fixture_id}: area {entry.get('code')!r}: unknown key(s): {', '.join(unknown)}")

    for required in ('code', 'kind', 'degree'):
        if required not in entry:
            raise FixtureError(f"{fixture_id}: area {dict(entry)!r} is missing {required!r}")

    area = dict(entry)
    area['code'] = str(area['code'])
    area.setdefault('status', AreaStatus.Declared.value)

    try:
        AreaStatus(area['status'])
        AreaType(area['kind'])
    except ValueError as e:
        raise FixtureError(f"{fixture_id}: area {area['code']!r}: {e}") from e

    if 'name' not in area:
        area['name'] = _area_name(code=area['code'], catalog=catalog, areas_root=areas_root)

    return area


def _area_name(*, code: str, catalog: int, areas_root: Optional[pathlib.Path]) -> str:
    if areas_root is None:
        return code

    path = find_area(root=areas_root, area_catalog=catalog, area_code=code)
    if path is None:
        return code

    with open(path, 'r', encoding='utf-8') as infile:
        spec = yaml.load(stream=infile, Loader=yaml.SafeLoader)

    return str(spec.get('name', code))
