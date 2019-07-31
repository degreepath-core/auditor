import argparse
import json
import logging
import os
import runpy

import dotenv
import psycopg2
import sentry_sdk

from degreepath import pretty_ms
from degreepath.audit import NoStudentsMsg, ResultMsg, AuditStartMsg, ExceptionMsg, NoAuditsCompletedMsg, ProgressMsg, Arguments

dp = runpy.run_path('./dp-common.py')


logger = logging.getLogger(__name__)

dotenv.load_dotenv(verbose=True)
if os.environ.get('SENTRY_DSN', None):
    sentry_sdk.init(dsn=os.environ.get('SENTRY_DSN'))
else:
    logger.warn('SENTRY_DSN not set; skipping')


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--area", dest="area_file", required=True)
    parser.add_argument("--student", dest="student_file", required=True)
    parser.add_argument("--run", dest="run", type=int, required=True)
    parser.add_argument("--loglevel", dest="loglevel", choices=("warn", "debug", "info", "critical"), default="warn")
    args = parser.parse_args()

    loglevel = getattr(logging, args.loglevel.upper())
    logging.basicConfig(level=loglevel)

    main(student_file=args.student_file, area_file=args.area_file, run_id=args.run)


def main(area_file, student_file, run_id=None):
    conn = psycopg2.connect(
        host=os.environ.get("PG_HOST"),
        database=os.environ.get("PG_DATABASE"),
        user=os.environ.get("PG_USER"),
        password=os.environ.get("PG_PASSWORD"),
    )

    try:
        result_id = None

        args = Arguments(area_files=[area_file], student_files=[student_file])

        for msg in dp['run'](args):
            if isinstance(msg, NoStudentsMsg):
                logger.critical('no student files provided')

            elif isinstance(msg, NoAuditsCompletedMsg):
                logger.critical('no audits completed')

            elif isinstance(msg, AuditStartMsg):
                logger.info("auditing #%s against %s %s", msg.stnum, msg.area_catalog, msg.area_code)
                with sentry_sdk.configure_scope() as scope:
                    scope.user = {"id": msg.stnum}

                result_id = make_result_id(conn=conn, stnum=msg.stnum, area_code=msg.area_code, catalog=msg.area_catalog)
                logger.info("result id = %s", result_id)

                with sentry_sdk.configure_scope() as scope:
                    scope.user = {"id": msg.stnum}
                    scope.set_tag('area_code', msg.area_code)
                    scope.set_tag('catalog', msg.area_catalog)
                    scope.set_extra('result_id', result_id)

            elif isinstance(msg, ExceptionMsg):
                logger.critical("%s %s %s", msg.msg, msg.ex, msg.tb)
                sentry_sdk.capture_exception(msg.ex)

                if result_id:
                    with conn.cursor() as curs:
                        curs.execute("UPDATE result SET in_progress = false WHERE id = %(result_id)s", {"result_id": result_id})
                        conn.commit()

            elif isinstance(msg, ProgressMsg):
                avg_iter_s = sum(msg.recent_iters) / max(len(msg.recent_iters), 1)
                avg_iter_time = pretty_ms(avg_iter_s * 1_000, format_sub_ms=True, unit_count=1)
                update_progress(conn=conn, start_time=msg.start_time, count=msg.count, result_id=result_id)
                logger.info(f"{msg.count:,} at {avg_iter_time} per audit")

            elif isinstance(msg, ResultMsg):
                record(conn=conn, result_id=result_id, message=msg)

            else:
                logger.critical('unknown message %s', msg)

    finally:
        conn.close()


def record(*, message, conn, result_id):
    result = message.result.to_dict() if message.result is not None else None

    avg_iter_s = sum(message.iterations) / max(len(message.iterations), 1)
    avg_iter_time = pretty_ms(avg_iter_s * 1_000, format_sub_ms=True, unit_count=1)

    claims = result["claims"]

    rank = result["rank"]
    ok = result["ok"]

    claims = []

    with conn.cursor() as curs:
        curs.execute("""
            UPDATE result
            SET iterations = %(total_count)s
              , duration = interval %(elapsed)s
              , per_iteration = interval %(avg_iter_time)s
              , rank = %(rank)s
              , max_rank = %(max_rank)s
              , result = %(result)s::jsonb
              , claimed_courses = %(claims)s::jsonb
              , ok = %(ok)s
              , ts = now()
              , gpa = %(gpa)s
              , in_progress = false
            WHERE id = %(result_id)s
        """, {
            "result_id": result_id,
            "total_count": message.count,
            "elapsed": message.elapsed,
            "avg_iter_time": avg_iter_time.strip("~"),
            "result": json.dumps(result),
            "rank": rank,
            "max_rank": 30,
            "claims": json.dumps(claims),
            "gpa": "0.00",
            "ok": False if ok is None else ok,
        })

        conn.commit()


def update_progress(*, conn, start_time, count, result_id):
    with conn.cursor() as curs:
        curs.execute("""
            UPDATE result
            SET iterations = %(count)s, duration = cast(now() - %(start_time)s as interval)
            WHERE id = %(result_id)s
        """, {"result_id": result_id, "count": count, "start_time": start_time})

        conn.commit()


def make_result_id(*, stnum, conn, area_code, catalog):
    with conn.cursor() as curs:
        curs.execute("""
            INSERT INTO result (student_id, area_code, catalog, in_progress)
            VALUES (%(student_id)s, %(area_code)s, %(catalog)s, true)
            RETURNING id
        """, {"student_id": stnum, "area_code": area_code, "catalog": catalog})

        conn.commit()

        for record in curs:
            return record[0]


if __name__ == "__main__":
    cli()
