import attr
from typing import Optional, List, TYPE_CHECKING
import logging

from ..base import Base, Result, BaseRequirementRule, RuleState

if TYPE_CHECKING:
    from ..claim import ClaimAttempt  # noqa: F401

logger = logging.getLogger(__name__)


@attr.s(cache_hash=True, slots=True, kw_only=True, frozen=True, auto_attribs=True)
class RequirementResult(Result, BaseRequirementRule):
    overridden: bool

    @staticmethod
    def from_solution(
        *,
        solution: BaseRequirementRule,
        result: Optional[Base],
        overridden: bool = False,
    ) -> 'RequirementResult':
        return RequirementResult(
            name=solution.name,
            message=solution.message,
            audited_by=solution.audited_by,
            is_contract=solution.is_contract,
            path=solution.path,
            result=result,
            overridden=overridden,
        )

    def state(self) -> RuleState:
        if self.result is None:
            return RuleState.Result

        return self.result.state()

    def claims(self) -> List['ClaimAttempt']:
        if self.result is None:
            return []

        return self.result.claims()

    def was_overridden(self) -> bool:
        return self.overridden

    def ok(self) -> bool:
        if self.was_overridden():
            return self.overridden

        if self.result is None:
            return False

        return self.result.ok()
