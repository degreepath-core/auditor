from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Union, Any, List, Optional, TYPE_CHECKING
import re
import itertools
import logging

from ...clause import Operator

if TYPE_CHECKING:
    from ...requirement import RequirementContext


@dataclass(frozen=True)
class Assertion:
    command: str
    source: str
    operator: Operator
    compare_to: Union[str, int, float]

    def to_dict(self):
        return {
            "type": "from-assertion",
            "command": self.command,
            "source": self.source,
            "operator": self.operator.name,
            "compare_to": self.compare_to,
        }

    @staticmethod
    def load(data: Dict) -> Assertion:
        keys = list(data.keys())

        assert (len(keys)) == 1

        rex = re.compile(r"(count|sum|minimum|maximum|stored)\((.*)\)")

        k = keys[0]

        m = rex.match(k)
        if not m:
            raise KeyError(f'expected "{k}" to match {rex}')

        val = data[k]

        assert len(val.keys()) == 1

        op = list(val.keys())[0]

        groups = m.groups()

        command = groups[0]
        source = groups[1]
        operator = Operator(op)
        compare_to = val[op]

        return Assertion(
            command=command, source=source, operator=operator, compare_to=compare_to
        )

    def validate(self, *, ctx: RequirementContext):
        assert self.command in [
            "count",
            "sum",
            "minimum",
            "maximum",
            "stored",
        ], f"{self.command}"

        if self.command == "count":
            assert self.source in [
                "courses",
                "areas",
                "performances",
                "terms",
                "semesters",
            ]
        elif self.command == "sum":
            assert self.source in ["grades", "credits"]
        elif self.command == "minimum" or self.command == "maximum":
            assert self.source in ["terms", "semesters", "grades", "credits"]
        elif self.command == "stored":
            # TODO: assert that the stored lookup exists
            pass

    def range(self, *, items: List):
        compare_to: Any = self.compare_to

        if type(compare_to) not in [int, float]:
            raise TypeError(
                f"compare_to must be numeric to be used in range(); was {repr(compare_to)} ({type(compare_to)}"
            )

        if self.operator == Operator.LessThanOrEqualTo:
            hi = compare_to
            lo = len(items)

        elif self.operator == Operator.LessThan:
            hi = compare_to - 1
            lo = len(items)

        elif self.operator == Operator.GreaterThan:
            hi = len(items)
            lo = compare_to + 1

        elif self.operator == Operator.GreaterThanOrEqualTo:
            hi = len(items)
            lo = compare_to

        elif self.operator == Operator.EqualTo:
            hi = compare_to + 1
            lo = compare_to

        if hi <= lo:
            logging.info(f"expected hi={hi} > lo={lo}")

        return range(lo, hi)