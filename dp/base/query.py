import attr
from typing import Optional, Tuple, Dict, Any, Sequence, Union, cast
import enum
from fractions import Fraction

from .bases import Base
from ..status import ResultStatus
from ..limit import LimitSet
from ..clause import Clause
from ..claim import ClaimAttempt
from ..rule.assertion import AssertionRule, ConditionalAssertionRule
from ..result.assertion import AssertionResult


@enum.unique
class QuerySource(enum.Enum):
    Courses = "courses"
    Claimed = "claimed"
    Areas = "areas"
    MusicPerformances = "music performances"
    MusicAttendances = "music recitals"


@attr.s(cache_hash=True, slots=True, kw_only=True, frozen=True, auto_attribs=True)
class BaseQueryRule(Base):
    source: QuerySource
    assertions: Tuple[Union[AssertionRule, ConditionalAssertionRule], ...]
    limit: LimitSet
    where: Optional[Clause]
    allow_claimed: bool
    attempt_claims: bool
    record_claims: bool
    path: Tuple[str, ...]
    inserted: Tuple[str, ...]
    force_inserted: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "source": self.source.value,
            "limit": self.limit.to_dict(),
            "assertions": [a.to_dict() for a in self.all_assertions()],
            "where": self.where.to_dict() if self.where else None,
            "claims": [c.to_dict() for c in self.claims()],
            "failures": [c.to_dict() for c in self.only_failed_claims()],
            "inserted": list(self.inserted),
        }

    def only_failed_claims(self) -> Sequence[ClaimAttempt]:
        return []

    def all_assertions(self) -> Sequence[Union[AssertionRule, ConditionalAssertionRule, AssertionResult]]:
        return self.assertions

    def type(self) -> str:
        return "query"

    def rank(self) -> Fraction:
        if self.waived():
            return Fraction(1, 1)

        return cast(Fraction, sum(a.rank() for a in self.all_assertions()))

    def status(self) -> ResultStatus:
        if self.waived():
            return ResultStatus.Waived

        allowed_statuses = {ResultStatus.Done, ResultStatus.Waived}
        statuses = set(a.status() for a in self.all_assertions())

        if allowed_statuses.issuperset(statuses):
            return ResultStatus.Done

        allowed_statuses.add(ResultStatus.PendingCurrent)
        if allowed_statuses.issuperset(statuses):
            return ResultStatus.PendingCurrent

        allowed_statuses.add(ResultStatus.PendingRegistered)
        if allowed_statuses.issuperset(statuses):
            return ResultStatus.PendingRegistered

        allowed_statuses.add(ResultStatus.NeedsMoreItems)
        if allowed_statuses.issuperset(statuses):
            return ResultStatus.NeedsMoreItems

        return ResultStatus.Empty
