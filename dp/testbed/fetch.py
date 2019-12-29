from typing import Any
import argparse
import os

import tqdm  # type: ignore

from .sqlite import sqlite_connect, sqlite_cursor
from dp.ms import pretty_ms


def fetch(args: argparse.Namespace) -> None:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore

    pg_conn = psycopg2.connect(
        host=os.environ.get("PGHOST"),
        database=os.environ.get("PGDATABASE"),
        user=os.environ.get("PGUSER"),
        cursor_factory=psycopg2.extras.DictCursor,
    )
    pg_conn.set_session(readonly=True)

    selected_run = fetch__select_run(args, pg_conn)

    with pg_conn.cursor() as curs:
        # language=PostgreSQL
        curs.execute('''
            SELECT count(*) total_count
            FROM result
            WHERE run = %s
        ''', [selected_run])

        total_items = curs.fetchone()['total_count']

    print(f"Fetching run #{selected_run} with {total_items:,} audits into '{args.db}'")

    if args.clear:
        with sqlite_connect(args.db) as conn:
            print('clearing cached data... ', end='', flush=True)
            # noinspection SqlWithoutWhere
            conn.execute('DELETE FROM server_data')
            conn.commit()
            print('cleared')

    # named cursors only allow one execute() call, so this must be its own block
    with pg_conn.cursor(name="degreepath_testbed") as curs:
        curs.itersize = 50

        # language=PostgreSQL
        curs.execute('''
            SELECT student_id AS stnum
                 , catalog
                 , area_code AS code
                 , iterations
                 , extract(EPOCH FROM duration) AS duration
                 , gpa
                 , ok
                 , rank
                 , max_rank
                 , result::text as result
                 , input_data::text as input_data
                 , run
            FROM result
            WHERE result IS NOT NULL AND run = %s
        ''', [selected_run])

        with sqlite_connect(args.db) as conn:
            for row in tqdm.tqdm(curs, total=total_items, unit_scale=True):
                try:
                    conn.execute('''
                        INSERT INTO server_data
                                (run,  stnum,  catalog,  code,  iterations,  duration,  ok,  gpa,  rank,  max_rank,       result,        input_data)
                        VALUES (:run, :stnum, :catalog, :code, :iterations, :duration, :ok, :gpa, :rank, :max_rank, json(:result), json(:input_data))
                    ''', dict(row))
                except Exception as e:
                    print(dict(row))
                    raise e

            conn.commit()


def fetch__select_run(args: argparse.Namespace, conn: Any) -> int:
    with conn.cursor() as curs:
        if args.latest:
            # language=PostgreSQL
            curs.execute('SELECT max(run) as max FROM result')
            to_fetch = curs.fetchone()['max']

        elif args.run:
            to_fetch = args.run

        else:
            # language=PostgreSQL
            curs.execute("""
                SELECT run
                     , min(ts AT TIME ZONE 'America/Chicago') AS first
                     , max(ts AT TIME ZONE 'America/Chicago') AS last
                     , extract(epoch from max(ts AT TIME ZONE 'America/Chicago') - min(ts AT TIME ZONE 'America/Chicago')) AS duration
                     , count(*) AS total
                     , sum(ok::integer) AS ok
                     , sum((NOT ok)::integer) AS "not-ok"
                FROM result
                WHERE run > 0
                  AND ts > now() - INTERVAL '1 week'
                GROUP BY run
                ORDER BY run DESC
            """)

            # 219: 2019-12-06 23:07 / 2019-12-07 04:40 [5h 32m 58.7s]; 6,997 total, 201 ok, 6,796 not-ok
            date_fmt = "%Y-%m-%d %H:%M"
            for row in curs.fetchall():
                first = row['first'].strftime(date_fmt)
                last = row['last'].strftime(date_fmt)
                duration = pretty_ms(row['duration'] * 1000, unit_count=2)
                print(f"{row['run']}: {first} / {last} [{duration}]; {row['total']:,} total, {row['ok']:,} ok, {row['not-ok']:,} not-ok")

            print('Download which run?')
            to_fetch = int(input('>>> '))

        return int(to_fetch)


def fetch_if_needed(args: argparse.Namespace) -> None:
    with sqlite_connect(args.db) as conn:
        with sqlite_cursor(conn) as curs:
            curs.execute('SELECT count(*) FROM server_data')

            if curs.fetchone()[0]:
                return
            else:
                raise Exception('run the fetch subcommand')