# mypy: warn_unreachable = False

from typing import Dict, cast
import json
import logging

import psycopg2.extensions  # type: ignore
import sentry_sdk

from dp.run import run
from dp.ms import pretty_ms
from dp.audit import ResultMsg, NoAuditsCompletedMsg, ProgressMsg, Arguments, EstimateMsg

logger = logging.getLogger(__name__)


def audit(*, area_spec: Dict, area_code: str, area_catalog: str, student: Dict, run_id: int, curs: psycopg2.extensions.cursor) -> None:
    args = Arguments()

    stnum = student['stnum']

    logger.info("auditing #%s against %s %s", stnum, area_catalog, area_code)
    with sentry_sdk.configure_scope() as scope:
        scope.user = {"id": stnum}

    curs.execute("""
        INSERT INTO result (  student_id,     area_code,     catalog,     run,     input_data)
        VALUES             (%(student_id)s, %(area_code)s, %(catalog)s, %(run)s, %(student)s )
        RETURNING id
    """, {"student_id": stnum, "area_code": area_code, "catalog": area_catalog, "run": run_id, "student": json.dumps(student)})

    row = curs.fetchone()
    result_id: int = cast(int, row[0])

    logger.info(f"result id = {result_id}")

    with sentry_sdk.configure_scope() as scope:
        scope.user = dict(id=stnum)
        scope.set_tag("area_code", area_code)
        scope.set_tag("catalog", area_catalog)
        scope.set_extra("result_id", result_id)

    try:
        for msg in run(args, area_spec=area_spec, student=student):
            if isinstance(msg, NoAuditsCompletedMsg):
                logger.critical('no audits completed')

            elif isinstance(msg, EstimateMsg):
                pass

            elif isinstance(msg, ProgressMsg):
                avg_iter_time = pretty_ms(msg.avg_iter_ms, format_sub_ms=True)

                curs.execute("""
                    UPDATE result
                    SET iterations = %(count)s, duration = interval %(elapsed)s
                    WHERE id = %(result_id)s
                """, {"result_id": result_id, "count": msg.iters, "elapsed": f"{msg.elapsed_ms}ms"})

                logger.info(f"{msg.iters:,} at {avg_iter_time} per audit")

            elif isinstance(msg, ResultMsg):
                result = msg.result.to_dict()
                result_str = json.dumps(result)

                # we use clock_timestamp() instead of now() here, because
                # now() is the start time of the transaction, and we instead
                # want the time when the computation was finished.
                # see https://stackoverflow.com/a/24169018
                curs.execute("""
                    UPDATE result
                    SET iterations = %(total_count)s
                      , duration = interval %(elapsed)s
                      , per_iteration = interval %(avg_iter_time)s
                      , rank = %(rank)s
                      , max_rank = %(max_rank)s
                      , result = %(result)s::jsonb
                      , ok = %(ok)s
                      , ts = clock_timestamp()
                      , gpa = %(gpa)s
                      , claimed_courses = %(claimed_courses)s::jsonb
                      , status = %(status)s
                    WHERE id = %(result_id)s
                """, {
                    "result_id": result_id,
                    "total_count": msg.iters,
                    "elapsed": f"{msg.elapsed_ms}ms",
                    "avg_iter_time": f"{msg.avg_iter_ms}ms",
                    "result": result_str,
                    "claimed_courses": json.dumps(msg.result.keyed_claims()),
                    "rank": result["rank"],
                    "max_rank": result["max_rank"],
                    "gpa": result["gpa"],
                    "ok": result["ok"],
                    "status": result["status"],
                })

            else:
                logger.critical('unknown message %s', msg)

    except Exception as ex:
        sentry_sdk.capture_exception(ex)

        curs.execute("""
            UPDATE result
            SET error = %(error)s
            WHERE id = %(result_id)s
        """, {"result_id": result_id, "error": json.dumps({"error": str(ex)})})
