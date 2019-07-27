from dataclasses import dataclass
from collections.abc import Mapping, Iterable
from typing import Union, List, Tuple, Dict, Any, Callable, Optional, Sequence, Iterator
import logging
import decimal
from .constants import Constants
from .lib import grade_from_str
from .operator import Operator, apply_operator, str_operator

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
    resolved_with: Optional[Any]
    resolved_items: Sequence[Any]
    result: bool

    def to_dict(self):
        return {
            "resolved_with": self.resolved_with,
            "resolved_items": [x for x in self.resolved_items],
            "result": self.result,
        }


@dataclass(frozen=True)
class AndClause:
    children: Tuple

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
    children: Tuple

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

    def to_dict(self):
        return {
            "type": "single-clause",
            "key": self.key,
            "expected": self.expected,
            "expected_verbatim": self.expected_verbatim,
            "operator": self.operator.name,
        }

    @staticmethod
    def load(key: str, value: Any, c: Constants):
        if not isinstance(value, Dict):
            raise Exception(f'expected {value} to be a dictionary')

        assert len(value.keys()) == 1, f"{value}"
        op = list(value.keys())[0]

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
            expected_value = grade_from_str(expected_value) if type(expected_value) is str else decimal.Decimal(expected_value)
        elif key == 'credits':
            expected_value = decimal.Decimal(expected_value)

        return SingleClause(
            key=key,
            expected=expected_value,
            operator=operator,
            expected_verbatim=expected_verbatim,
        )

    def validate(self, *, ctx):
        pass

    def compare(self, to_value: Any) -> bool:
        return apply_operator(lhs=to_value, op=self.operator, rhs=self.expected)

    # def mc_applies_same(self, other) -> bool:
    #     """Checks if this clause applies to the same items as the other clause,
    #     when used as part of a multicountable ruleset."""
    #
    #     if isinstance(other, AndClause):
    #         return other.mc_applies_same(self)
    #
    #     if isinstance(other, OrClause):
    #         return other.mc_applies_same(self)
    #
    #     logger.debug('mc_applies_same: %s, %s', self, other)
    #
    #     if not isinstance(other, SingleClause):
    #         return False
    #
    #     return (
    #         self.key == other.key
    #         and self.expected == other.expected
    #         and self.operator == other.operator
    #     )

    def is_subset(self, other_clause) -> bool:
        """
        answers the question, "am I a subset of $other"
        """

        if isinstance(other_clause, AndClause):
            return any(self.is_subset(c) for c in other_clause.children)

        elif isinstance(other_clause, OrClause):
            return any(self.is_subset(c) for c in other_clause.children)

        if self.key != other_clause.key:
            return False

        if self.operator == Operator.EqualTo and other_clause.operator == Operator.In:
            return any(v == self.expected for v in other_clause.expected)

        return self.expected == other_clause.expected

    def applies_to(self, other) -> bool:
        logger.debug('applies_to: %s, %s', self, other)
        return apply_operator(lhs=other, op=self.operator, rhs=self.expected)

    def compare_and_resolve_with(self, *, value: Any, map_func: Callable) -> ResolvedBaseClause:
        reduced_value, value_items = map_func(clause=self, value=value)
        result = apply_operator(lhs=reduced_value, op=self.operator, rhs=self.expected)

        return ResolvedSingleClause(
            key=self.key,
            expected=self.expected,
            expected_verbatim=self.expected_verbatim,
            operator=self.operator,
            resolved_with=reduced_value,
            resolved_items=value_items,
            result=result,
        )

    def input_size_range(self, *, maximum) -> Iterator[int]:
        if type(self.expected) is not int:
            raise TypeError('cannot find a range of values for a non-integer clause: %s', type(self.expected))

        if self.operator == Operator.EqualTo:
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
            resolved = f" ({clause.get('resolved_with', None)}; {sorted(clause.get('resolved_items', []))})"
        else:
            resolved = ""

        if clause['expected'] != clause['expected_verbatim']:
            postscript = f" (via \"{clause['expected_verbatim']}\")"
        else:
            postscript = ""

        op = str_operator(clause['operator'])

        return f"\"{clause['key']}\"{resolved} {op} \"{clause['expected']}\"{postscript}"
    elif clause["type"] == "or-clause":
        return f'({" or ".join(str_clause(c) for c in clause["children"])})'
    elif clause["type"] == "and-clause":
        return f'({" and ".join(str_clause(c) for c in clause["children"])})'

    raise Exception('not a clause')


Clause = Union[AndClause, OrClause, SingleClause]
ResolvedClause = Union[ResolvedAndClause, ResolvedOrClause, ResolvedSingleClause, ResolvedBaseClause]
