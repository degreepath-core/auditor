"""Parse a fixture's `expect:` block and check it against an audit result."""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Optional, Sequence

import attr

from ..status import ResultStatus
from .errors import FixtureError

STATUS_VALUES = frozenset(s.value for s in ResultStatus)
EXPECTATION_KEYS = frozenset({'status', 'gpa', 'requirements', 'known_issue'})


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class AreaExpectation:
    status: str
    gpa: Optional[str] = None
    requirements: Dict[str, str] = attr.Factory(dict)
    known_issue: Optional[str] = None


def parse_expectations(raw: Any, *, area_codes: Sequence[str], fixture_id: str) -> Dict[str, AreaExpectation]:
    if not isinstance(raw, Mapping):
        raise FixtureError(f"{fixture_id}: 'expect' must be a mapping of area code to expectation")

    expected_codes = {str(k) for k in raw}
    declared_codes = set(area_codes)
    if expected_codes != declared_codes:
        raise FixtureError(
            f"{fixture_id}: 'expect' covers {sorted(expected_codes)} but 'areas' declares {sorted(declared_codes)}; they must match"
        )

    return {str(code): _parse_one(entry, code=str(code), fixture_id=fixture_id) for code, entry in raw.items()}


def _parse_one(entry: Any, *, code: str, fixture_id: str) -> AreaExpectation:
    where = f"{fixture_id}: expect.{code}"

    if not isinstance(entry, Mapping):
        raise FixtureError(f"{where} must be a mapping")

    unknown = sorted(set(entry) - EXPECTATION_KEYS)
    if unknown:
        raise FixtureError(f"{where}: unknown key(s): {', '.join(unknown)}")

    status = entry.get('status')
    if status not in STATUS_VALUES:
        raise FixtureError(f"{where}.status must be one of {sorted(STATUS_VALUES)}; got {status!r}")

    gpa = entry.get('gpa')
    if gpa is not None:
        if not isinstance(gpa, str):
            raise FixtureError(f"{where}.gpa must be a quoted string like '3.25'; got {gpa!r}")
        try:
            Decimal(gpa)
        except InvalidOperation:
            raise FixtureError(f"{where}.gpa {gpa!r} is not a number") from None

    requirements = entry.get('requirements', {})
    if not isinstance(requirements, Mapping):
        raise FixtureError(f"{where}.requirements must be a mapping of requirement path to status")
    for name, req_status in requirements.items():
        if req_status not in STATUS_VALUES:
            raise FixtureError(f"{where}.requirements[{name!r}] must be one of {sorted(STATUS_VALUES)}; got {req_status!r}")

    known_issue = entry.get('known_issue')
    if known_issue is not None and (not isinstance(known_issue, str) or not known_issue.strip()):
        raise FixtureError(f"{where}.known_issue must be a non-empty description")

    return AreaExpectation(
        status=status,
        gpa=gpa,
        requirements={str(k): str(v) for k, v in requirements.items()},
        known_issue=known_issue,
    )


def requirement_statuses(result: Mapping[str, Any]) -> Dict[str, str]:
    """Map every requirement in an area result's to_dict() to its status.

    Keys are requirement names from the top down, joined with '/', taken from
    the '%Name' segments of each requirement's path.
    """
    found: Dict[str, str] = {}
    _walk(result, found)
    return found


def _walk(node: Any, found: Dict[str, str]) -> None:
    if isinstance(node, Mapping):
        if node.get('type') == 'requirement' and 'path' in node:
            key = '/'.join(segment[1:] for segment in node['path'] if segment.startswith('%'))
            found[key] = node['status']
        for value in node.values():
            _walk(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk(item, found)


def check_expectation(expectation: AreaExpectation, result: Mapping[str, Any]) -> List[str]:
    """Return a list of human-readable mismatches; empty means the expectation holds."""
    problems: List[str] = []

    if result['status'] != expectation.status:
        problems.append(f"status: expected {expectation.status!r}, got {result['status']!r}")

    if expectation.gpa is not None and Decimal(result['gpa']) != Decimal(expectation.gpa):
        problems.append(f"gpa: expected {expectation.gpa}, got {result['gpa']}")

    actual = requirement_statuses(result)
    for name, expected_status in sorted(expectation.requirements.items()):
        if name not in actual:
            problems.append(f"requirement {name!r} not found; available: {sorted(actual)}")
        elif actual[name] != expected_status:
            problems.append(f"requirement {name!r}: expected {expected_status!r}, got {actual[name]!r}")

    return problems
