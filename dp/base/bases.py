import abc
from typing import Iterator, Dict, Set, Any, List, Tuple, Collection, Optional, TYPE_CHECKING
from decimal import Decimal
import enum
import attr
from functools import cmp_to_key, lru_cache
from ..status import ResultStatus, PassingStatuses
from ..claim import Claim
from ..exception import BlockException

if TYPE_CHECKING:  # pragma: no cover
    from ..context import RequirementContext
    from ..data.course import CourseInstance  # noqa: F401
    from ..data.clausable import Clausable  # noqa: F401

# TODO: rename matched() to collect_matches()


@enum.unique
class RuleState(enum.Enum):
    Rule = "rule"
    Solution = "solution"
    Result = "result"


@attr.s(cache_hash=True, slots=True, kw_only=True, frozen=True, auto_attribs=True)
class Base(abc.ABC):
    path: Tuple[str, ...]
    overridden: bool

    def to_dict(self) -> Dict[str, Any]:
        status = self.status()
        rank, max_rank = self.rank()

        return {
            "path": list(self.path),
            "state": self.state().value,
            "type": self.type(),
            "status": status.value,
            "rank": str(rank),
            "max_rank": str(max_rank),
            "overridden": self.overridden,
        }

    @abc.abstractmethod
    def type(self) -> str:
        raise NotImplementedError('must define a type() method')

    def state(self) -> RuleState:
        return RuleState.Rule

    def status(self) -> ResultStatus:
        if self.is_waived():
            return ResultStatus.Waived

        matched = self.matched()
        has_ip_courses = any(c.is_in_progress for c in matched)
        has_enrolled_courses = any(c.is_in_progress_this_term for c in matched)
        has_registered_courses = any(c.is_in_progress_in_future for c in matched)

        if has_ip_courses and has_enrolled_courses and (not has_registered_courses):
            return ResultStatus.PendingCurrent
        elif has_ip_courses and has_registered_courses:
            return ResultStatus.PendingRegistered

        rank, _max_rank = self.rank()

        if rank < 1:
            return ResultStatus.NeedsMoreItems

        return ResultStatus.Empty

    def rank(self) -> Tuple[Decimal, Decimal]:
        if self.is_waived():
            return Decimal(1), Decimal(1)

        return Decimal(0), Decimal(1)

    def claims(self) -> List[Claim]:
        return []

    def claims_for_gpa(self) -> List[Claim]:
        return self.claims()

    def matched(self) -> Set['CourseInstance']:
        return set(claim.get_course() for claim in self.claims() if claim.failed is False)

    def matched_for_gpa(self) -> Set['CourseInstance']:
        return set(claim.get_course() for claim in self.claims_for_gpa() if claim.failed is False)

    def is_in_gpa(self) -> bool:
        return True

    def is_waived(self) -> bool:
        return self.overridden

    def is_always_disjoint(self) -> bool:
        return False

    def is_never_disjoint(self) -> bool:
        return False

    def is_ok(self) -> bool:
        return self.status() in PassingStatuses

    def all_courses(self, ctx: 'RequirementContext') -> List['CourseInstance']:
        return []


class Result(Base, abc.ABC):
    __slots__ = ()

    def state(self) -> RuleState:
        return RuleState.Result


class Solution(Base):
    __slots__ = ()

    def state(self) -> RuleState:
        return RuleState.Solution

    @abc.abstractmethod
    def audit(self, *, ctx: 'RequirementContext') -> Result:
        raise NotImplementedError('must define an audit() method')


class Rule(Base):
    __slots__ = ()

    def state(self) -> RuleState:
        return RuleState.Rule

    @abc.abstractmethod
    def get_requirement_names(self) -> List[str]:
        raise NotImplementedError('must define a get_requirement_names() method')

    @abc.abstractmethod
    def get_required_courses(self, *, ctx: 'RequirementContext') -> Collection['CourseInstance']:
        raise NotImplementedError('must define a get_required_courses() method')

    def exclude_required_courses(self, to_exclude: Collection['CourseInstance']) -> 'Rule':
        return self

    def apply_block_exception(self, to_block: BlockException) -> 'Rule':
        return self

    @abc.abstractmethod
    def solutions(self, *, ctx: 'RequirementContext', depth: Optional[int] = None) -> Iterator[Solution]:
        raise NotImplementedError('must define a solutions() method')

    @abc.abstractmethod
    def estimate(self, *, ctx: 'RequirementContext', depth: Optional[int] = None) -> int:
        raise NotImplementedError('must define an estimate() method')

    @abc.abstractmethod
    def has_potential(self, *, ctx: 'RequirementContext') -> bool:
        raise NotImplementedError('must define a has_potential() method')

    @abc.abstractmethod
    def all_matches(self, *, ctx: 'RequirementContext') -> Collection['Clausable']:
        raise NotImplementedError('must define an all_matches() method')


def compare_path_tuples(a: Base, b: Base) -> int:
    if a.path == b.path:
        # a equals b
        return 0
    elif compare_path_tuples__lt(a.path, b.path):
        # a is less-than b
        return -1
    else:
        # a is greater than b
        return 1


sort_by_path = cmp_to_key(compare_path_tuples)


@lru_cache(2048)
def compare_path_tuples__lt(path_a: Tuple[str, ...], path_b: Tuple[str, ...]) -> bool:
    """
    >>> compare_path_tuples__lt(('$', '.count', '[2]'), ('$', '.count', '[10]'))
    True
    >>> compare_path_tuples__lt(('$', '.count'), ('$', '[10]'))
    False
    >>> compare_path_tuples__lt(('$', '[10]'), ('$', '.count'))
    True
    >>> compare_path_tuples__lt(('$', '.count', '[2]'), ('$', '.count'))
    False
    >>> compare_path_tuples__lt(('$', '.count', '[2]'), ('$', '.count', '[3]', '.count', '[1]'))
    True
    >>> compare_path_tuples__lt(('$', '.count', '[2]'), ('$', '.count', '%Emphasis: Public Policy'))
    True
    >>> compare_path_tuples__lt(('$', '.count', '.emphasis', '%Emphasis: Public Policy'), ('$', '.count', '[2]', '.stuff'))
    False
    """
    a_len = len(path_a)
    b_len = len(path_b)

    if a_len < b_len:
        return True

    if b_len < a_len:
        return False

    a: Any
    b: Any

    for a, b in zip(path_a, path_b):
        # convert indices to integers
        if a and a[0] == '[':
            a = int(a[1:-1])

        if b and b[0] == '[':
            b = int(b[1:-1])

        if type(a) == type(b):
            if a == b:
                continue

            if a < b:
                return True
            else:
                return False

        elif type(a) == int:
            return True

        else:
            return False

    return True
