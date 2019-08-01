from dataclasses import dataclass
from collections.abc import Mapping, Iterable
from typing import Union, List, Tuple, Dict, Any, Callable, Optional, Sequence, Iterator
import logging
import decimal
from .constants import Constants
from .lib import str_to_grade_points
from .operator import Operator, apply_operator, str_operator
from .rule.course import CourseRule
from .data.course_enums import GradeType

logger = logging.getLogger(__name__)


def load_clause(data: Dict, c: Constants):
    if not isinstance(data, Mapping):
        raise Exception(f'expected {data} to be a dictionary')

    if "$and" in data:
        assert len(data.keys()) == 1
        return AndClause.load(data["$and"], c)
    elif "$or" in data:
        assert len(data.keys()) == 1
        return OrClause.load(data["$or"], c)

    clauses = [SingleClause.load(key, value, c) for key, value in data.items()]

    if len(clauses) == 1:
        return clauses[0]

    return AndClause(children=tuple(clauses))


@dataclass(frozen=True)
class ResolvedBaseClause:
    resolved_with: Optional[Any] = None
    resolved_items: Sequence[Any] = tuple()
    result: bool = False

    def to_dict(self):
        return {
            "resolved_with": str(self.resolved_with) if isinstance(self.resolved_with, decimal.Decimal) else self.resolved_with,
            "resolved_items": [str(x) if isinstance(x, decimal.Decimal) else x for x in self.resolved_items],
            "result": self.result,
        }


@dataclass(frozen=True)
class AndClause:
    children: Tuple = tuple()

    def to_dict(self):
        return {
            "type": "and-clause",
            "children": [c.to_dict() for c in self.children],
        }

    @staticmethod
    def load(data: List[Dict], c: Constants):
        clauses = [load_clause(clause, c) for clause in data]
        return AndClause(children=tuple(clauses))

    def validate(self, *, ctx):
        for c in self.children:
            c.validate(ctx=ctx)

    def is_subset(self, other_clause) -> bool:
        return any(c.is_subset(other_clause) for c in self.children)

    def compare_and_resolve_with(self, *, value: Any, map_func: Callable) -> ResolvedBaseClause:
        children = tuple(c.compare_and_resolve_with(value=value, map_func=map_func) for c in self.children)
        result = all(c.result for c in children)

        return ResolvedAndClause(children=children, resolved_with=None, resolved_items=[], result=result)


@dataclass(frozen=True)
class ResolvedAndClause(AndClause, ResolvedBaseClause):
    def to_dict(self):
        return {
            **AndClause.to_dict(self),
            **ResolvedBaseClause.to_dict(self),
        }


@dataclass(frozen=True)
class OrClause:
    children: Tuple = tuple()

    def to_dict(self):
        return {
            "type": "or-clause",
            "children": [c.to_dict() for c in self.children],
        }

    @staticmethod
    def load(data: Dict, c: Constants):
        clauses = [load_clause(clause, c) for clause in data]
        return OrClause(children=tuple(clauses))

    def validate(self, *, ctx):
        for c in self.children:
            c.validate(ctx=ctx)

    def is_subset(self, other_clause) -> bool:
        return any(c.is_subset(other_clause) for c in self.children)

    def compare_and_resolve_with(self, *, value: Any, map_func: Callable) -> ResolvedBaseClause:
        children = tuple(c.compare_and_resolve_with(value=value, map_func=map_func) for c in self.children)
        result = any(c.result for c in children)

        return ResolvedOrClause(children=children, resolved_with=None, resolved_items=[], result=result)


@dataclass(frozen=True)
class ResolvedOrClause(OrClause, ResolvedBaseClause):
    def to_dict(self):
        return {
            **OrClause.to_dict(self),
            **ResolvedBaseClause.to_dict(self),
        }


@dataclass(frozen=True)
class SingleClause:
    key: str
    expected: Any
    expected_verbatim: Any
    operator: Operator
    at_most: bool = False

    def to_dict(self):
        expected = self.expected
        if isinstance(self.expected, GradeType):
            expected = self.expected.value
        if isinstance(self.expected, decimal.Decimal):
            expected = str(self.expected)

        return {
            "type": "single-clause",
            "key": self.key,
            "expected": expected,
            "expected_verbatim": self.expected_verbatim,
            "operator": self.operator.name,
        }

    @staticmethod
    def from_course_rule(rule: CourseRule):
        return SingleClause(key='course', expected=rule.course, expected_verbatim=rule.course, operator=Operator.EqualTo)

    @staticmethod  # noqa: C901
    def load(key: str, value: Any, c: Constants):
        if not isinstance(value, Dict):
            raise Exception(f'expected {value} to be a dictionary')

        operators = [k for k in value.keys() if k.startswith('$')]

        assert len(operators) == 1, f"{value}"
        op = list(operators)[0]

        at_most = value.get('at_most', False)
        assert type(at_most) is bool

        operator = Operator(op)
        expected_value = value[op]

        if isinstance(expected_value, list):
            expected_value = tuple(expected_value)

        expected_verbatim = expected_value

        if key == "subjects":
            key = "subject"
        if key == "attribute":
            key = "attributes"
        if key == "gereq":
            key = "gereqs"

        if type(expected_value) == str:
            expected_value = c.get_by_name(expected_value)
        elif isinstance(expected_value, Iterable):
            expected_value = tuple(c.get_by_name(v) for v in expected_value)

        if key == 'grade':
            expected_value = str_to_grade_points(expected_value) if type(expected_value) is str else decimal.Decimal(expected_value)
        elif key == 'grade_type':
            expected_value = GradeType(expected_value)
        elif key == 'credits':
            expected_value = decimal.Decimal(expected_value)

        return SingleClause(
            key=key,
            expected=expected_value,
            operator=operator,
            expected_verbatim=expected_verbatim,
            at_most=at_most,
        )

    def validate(self, *, ctx):
        pass

    def compare(self, to_value: Any) -> bool:
        return apply_operator(lhs=to_value, op=self.operator, rhs=self.expected)

    def is_subset(self, other_clause) -> bool:
        """
        answers the question, "am I a subset of $other"
        """

        if isinstance(other_clause, AndClause):
            return any(self.is_subset(c) for c in other_clause.children)

        elif isinstance(other_clause, OrClause):
            return any(self.is_subset(c) for c in other_clause.children)

        elif isinstance(other_clause, CourseRule):
            return other_clause.is_equivalent_to_clause(self)

        elif not isinstance(other_clause, type(self)):
            raise TypeError(f'unsupported value {type(other_clause)}')

        if self.key != other_clause.key:
            return False

        if self.operator == Operator.EqualTo and other_clause.operator == Operator.In:
            return any(v == self.expected for v in other_clause.expected)

        return self.expected == other_clause.expected

    def compare_and_resolve_with(self, *, value: Any, map_func: Callable) -> ResolvedBaseClause:
        reduced_value, value_items = map_func(clause=self, value=value)
        result = apply_operator(lhs=reduced_value, op=self.operator, rhs=self.expected)

        return ResolvedSingleClause(
            key=self.key,
            expected=self.expected,
            expected_verbatim=self.expected_verbatim,
            operator=self.operator,
            at_most=self.at_most,
            resolved_with=reduced_value,
            resolved_items=value_items,
            result=result,
        )

    def input_size_range(self, *, maximum) -> Iterator[int]:
        if type(self.expected) is not int:
            raise TypeError('cannot find a range of values for a non-integer clause: %s', type(self.expected))

        if self.operator == Operator.EqualTo or (self.operator == Operator.GreaterThanOrEqualTo and self.at_most is True):
            yield from range(self.expected, self.expected + 1)

        elif self.operator == Operator.NotEqualTo:
            # from 0-maximum, skipping "expected"
            yield from range(0, self.expected)
            yield from range(self.expected + 1, max(self.expected + 1, maximum + 1))

        elif self.operator == Operator.GreaterThanOrEqualTo:
            yield from range(self.expected, max(self.expected + 1, maximum + 1))

        elif self.operator == Operator.GreaterThan:
            yield from range(self.expected + 1, max(self.expected + 2, maximum + 1))

        elif self.operator == Operator.LessThan:
            yield from range(0, self.expected)

        elif self.operator == Operator.LessThanOrEqualTo:
            yield from range(0, self.expected + 1)

        else:
            raise TypeError('unsupported operator for ranges %s', self.operator)


@dataclass(frozen=True)
class ResolvedSingleClause(ResolvedBaseClause, SingleClause):
    def to_dict(self):
        return {
            **SingleClause.to_dict(self),
            **ResolvedBaseClause.to_dict(self),
        }


def str_clause(clause) -> str:
    if not isinstance(clause, dict):
        return str_clause(clause.to_dict())

    if clause["type"] == "single-clause":
        if clause.get('resolved_with', None) is not None:
            resolved = f" ({clause.get('resolved_with', None)})"
            postpostscript = f" (resolved items: {sorted(clause.get('resolved_items', []))})"
        else:
            resolved = ""
            postpostscript = ""

        if clause['expected'] != clause['expected_verbatim']:
            postscript = f" (via \"{clause['expected_verbatim']}\")"
        else:
            postscript = ""

        op = str_operator(clause['operator'])

        return f"\"{clause['key']}\"{resolved} {op} \"{clause['expected']}\"{postscript}{postpostscript}"
    elif clause["type"] == "or-clause":
        return f'({" or ".join(str_clause(c) for c in clause["children"])})'
    elif clause["type"] == "and-clause":
        return f'({" and ".join(str_clause(c) for c in clause["children"])})'

    raise Exception('not a clause')


Clause = Union[AndClause, OrClause, SingleClause]
ResolvedClause = Union[ResolvedAndClause, ResolvedOrClause, ResolvedSingleClause, ResolvedBaseClause]
