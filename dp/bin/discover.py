from typing import Iterator, Set, Any, List
from pathlib import Path
from collections import namedtuple
import argparse
import sys

import yaml

from dp.dotenv import load as load_dotenv

try:
    import psycopg2  # type: ignore
except ImportError:
    psycopg2 = None

from dp import AreaOfStudy, Constants
from dp.base import Rule
from dp.predicate_clause import PredicateCompoundAnd, PredicateCompoundOr, PredicateNot, Predicate, ConditionalPredicate, SomePredicate
from dp.assertion_clause import Assertion, ConditionalAssertion, AnyAssertion, DynamicConditionalAssertion
from dp.rule.course import CourseRule
from dp.rule.count import CountRule
from dp.rule.proficiency import ProficiencyRule
from dp.rule.query import QueryRule
from dp.rule.requirement import RequirementRule

load_dotenv()

CourseReference = namedtuple('CourseReference', ['code', 'course', 'crsid'])
BucketReference = namedtuple('BucketReference', ['code', 'catalog', 'bucket'])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+')
    parser.add_argument('--insert', default=False, action='store_true')
    args = parser.parse_args()

    files: List[str] = args.files
    courses: Set[CourseReference] = set()
    buckets: Set[BucketReference] = set()

    for filepath in files:
        if not filepath.endswith('.yaml'):
            continue

        file: Path = Path(filepath)

        code = file.stem
        catalog = file.parent.stem

        if '-' in code or '.' in code:
            continue

        with open(file, "r", encoding="utf-8") as infile:
            area_spec = yaml.load(stream=infile, Loader=yaml.SafeLoader)

        area = AreaOfStudy.load(specification=area_spec, c=Constants(), all_emphases=True)

        for course in find_courses_in_rule(area.result):
            if course.isdigit():
                # must be a crsid
                courses.add(CourseReference(code=code, course='', crsid=course))
            else:
                courses.add(CourseReference(code=code, course=course, crsid=None))

        for limit in area.limit.limits:
            for bucket in find_buckets_in_clause(limit.where):
                buckets.add(BucketReference(code=code, catalog=catalog, bucket=bucket))

        for bucket in find_buckets_in_rule(area.result):
            buckets.add(BucketReference(code=code, catalog=catalog, bucket=bucket))

    if args.insert:
        insert_to_db(courses=courses, buckets=buckets)
        print('inserted')
    else:
        for course_ref in sorted(courses):
            print(f"course: {course_ref.code}:{course_ref.course}")

        for bucket_ref in sorted(buckets):
            print(f"{bucket_ref.code}:{bucket_ref.catalog}:{bucket_ref.bucket}")


def find_courses_in_rule(rule: Rule) -> Iterator[str]:
    if isinstance(rule, CourseRule):
        if not rule.course and not rule.crsid:
            return

        if rule.institution or rule.clbid or rule.ap or rule.name:
            return

        if rule.hidden:
            return

        if rule.crsid:
            yield rule.crsid
            return

        if rule.course:
            yield rule.course
            return

        raise TypeError('never get here')

    elif isinstance(rule, ProficiencyRule):
        if not rule.course:
            return

        yield from find_courses_in_rule(rule.course)

    elif isinstance(rule, CountRule):
        for sub_rule in rule.items:
            yield from find_courses_in_rule(sub_rule)

    elif isinstance(rule, RequirementRule):
        if not rule.result:
            return

        yield from find_courses_in_rule(rule.result)


def insert_to_db(*, courses: Set[CourseReference], buckets: Set[BucketReference]) -> None:
    if not psycopg2:
        print('could not import module psycopg2', file=sys.stderr)
        sys.exit(1)

    # empty string means "use the environment variables"
    conn = psycopg2.connect('', application_name='degreepath-discovery')

    insert_course_refs(conn, courses)
    insert_bucket_refs(conn, buckets)


def insert_course_refs(conn: Any, courses: Set[CourseReference]) -> None:
    with conn.cursor() as curs:
        for course_ref in courses:
            curs.execute('''
                INSERT INTO map_constant_area(area_code, course, crsid)
                VALUES (%(code)s, %(course)s, %(crsid)s)
                ON CONFLICT DO NOTHING
            ''', {'code': course_ref.code, 'course': course_ref.course, 'crsid': course_ref.crsid})

        curs.execute('''
            SELECT area_code, course, crsid
            FROM map_constant_area
        ''')

        for code, course, crsid in curs.fetchall():
            ref = CourseReference(code=code, course=course, crsid=crsid)

            if ref not in courses:
                print('deleting', ref)
                if ref.course is not None:
                    curs.execute('''
                        DELETE FROM map_constant_area
                        WHERE area_code = %(code)s
                            AND course = %(course)s
                    ''', {'code': ref.code, 'course': ref.course})
                elif ref.crsid is not None:
                    curs.execute('''
                        DELETE FROM map_constant_area
                        WHERE area_code = %(code)s
                            AND crsid = %(crsid)s
                    ''', {'code': ref.code, 'crsid': ref.crsid})

        conn.commit()


def insert_bucket_refs(conn: Any, buckets: Set[BucketReference]) -> None:
    with conn.cursor() as curs:
        for bucket_ref in buckets:
            curs.execute('''
                INSERT INTO map_attribute_area(attr, area_code, catalog_year)
                VALUES (%(bucket)s, %(code)s, %(catalog)s)
                ON CONFLICT DO NOTHING
            ''', {'bucket': bucket_ref.bucket, 'code': bucket_ref.code, 'catalog': bucket_ref.catalog})

        curs.execute('''
            SELECT area_code, catalog_year, attr
            FROM map_attribute_area
        ''')

        for code, catalog, bucket in curs.fetchall():
            ref = BucketReference(code=code, catalog=catalog, bucket=bucket)
            if ref not in buckets:
                print('deleting', ref)
                curs.execute('''
                    DELETE FROM map_attribute_area
                    WHERE area_code = %(code)s
                        AND catalog_year = %(catalog)s
                        AND attr = %(bucket)s
                ''', {'bucket': ref.bucket, 'code': ref.code, 'catalog': ref.catalog})

        conn.commit()


def find_buckets_in_rule(rule: Rule) -> Iterator[str]:
    if isinstance(rule, QueryRule):
        for limit in rule.limit.limits:
            yield from find_buckets_in_clause(limit.where)

        if rule.where:
            yield from find_buckets_in_clause(rule.where)

        for assertion in rule.assertions:
            yield from find_buckets_in_assertion(assertion)

    elif isinstance(rule, CountRule):
        for sub_rule in rule.items:
            yield from find_buckets_in_rule(sub_rule)

    elif isinstance(rule, RequirementRule):
        if not rule.result:
            return

        yield from find_buckets_in_rule(rule.result)


def find_buckets_in_assertion(assertion: AnyAssertion) -> Iterator[str]:
    if isinstance(assertion, Assertion):
        if assertion.where:
            yield from find_buckets_in_clause(assertion.where)

    elif isinstance(assertion, ConditionalAssertion):
        yield from find_buckets_in_assertion(assertion.when_true)
        if assertion.when_false:
            yield from find_buckets_in_assertion(assertion.when_false)

    elif isinstance(assertion, DynamicConditionalAssertion):
        yield from find_buckets_in_assertion(assertion.when_true)


def find_buckets_in_clause(clause: SomePredicate) -> Iterator[str]:
    if isinstance(clause, (PredicateCompoundAnd, PredicateCompoundOr)):
        for pred in clause.predicates:
            yield from find_buckets_in_clause(pred)

    elif isinstance(clause, ConditionalPredicate):
        yield from find_buckets_in_clause(clause.when_true)
        if clause.when_false is not None:
            yield from find_buckets_in_clause(clause.when_false)

    elif isinstance(clause, PredicateNot):
        yield from find_buckets_in_clause(clause.predicate)

    elif isinstance(clause, Predicate):
        if clause.key == 'attributes':
            if type(clause.expected) is str:
                yield clause.expected
            elif type(clause.expected) is tuple:
                yield from clause.expected

    else:
        raise TypeError('unexpected predicate clause type')


if __name__ == '__main__':
    main()
