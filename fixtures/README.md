# Fixture students and fixture areas

Synthetic students and synthetic areas of study for the auditor. They do three jobs:

1. **Regression tests.** `tests/test_fixtures.py` audits every fixture student against its fixture areas and checks the outcome each student declares, plus a full snapshot of the result.
2. **Examples.** Each fixture area demonstrates one feature of the area DSL; each fixture student shows that feature on a concrete transcript.
3. **Dev data.** Fixture students expand to the standard student JSON, and `fixtures/areas/` is laid out like `stolaf-areas`, so both feed straight into the existing tools.

Nothing here is real student data, and nothing here tests St. Olaf's real areas — the subject under test is the engine.

## Layout

```
fixtures/
  areas/<catalog-year>/<code>.yaml   # fixture areas, laid out like stolaf-areas
  students/<id>.yaml                 # fixture students (short form)
  snapshots/<id>.<code>.json         # full audit result for each student/area pair
```

- Codes `T100`–`T899` are **feature areas**, each isolating one engine feature. They use `type: concentration`, because the engine appends St. Olaf's built-in "Common Major Requirements" to every `type: major` area, which would muddy a single-feature fixture.
- Codes `T900`–`T999` are **composite areas**: realistic-looking majors, mainly for dev data. Being majors, they include the common requirements, so their students carry 21+ credits outside the major.
- Area names start with `Fixture:` and each file opens with a comment saying what it exercises.
- The earliest catalog folder is `2020-21`, so fixture students need `catalog: 2020` or later. `find_area` picks the newest folder at or before the student's catalog year.

## Writing a fixture student

```yaml
# Scenario: one sentence saying what this student demonstrates.
catalog: 2020                 # optional (default 2020)
current_term: '20203'         # optional; decides in-progress vs registered for IP courses
areas:
  - {code: T300, kind: concentration, degree: B.A.}
courses:
  - DEPT 101 2018-1 B
  - DEPT 201 2019-1 B transfer
  - DEPT 202 2019-3 B transfer inst=CARL
expect:
  T300:
    status: needs-more-items
    requirements: {Electives: needs-more-items}
```

Optional top-level keys: `stnum`, `catalog`, `curriculum`, `matriculation`, `current_term`, and — copied through verbatim in the auditor's own format — `exceptions`, `templates`, `performances`, `performance_attendances`, `proficiencies`, `mediums`. Each area needs `code`, `kind`, and `degree`; `status` defaults to `declared` and `name` to the area file's name.

### Course short form

```
SUBJ NUM[.SECTION] YEAR-TERM GRADE [flag ...]
```

- Terms: `1` fall, `2` interim, `3` spring, `4`/`5` summer. Spring 2020 (`2019-3`) is the COVID term.
- `GRADE` is any grade code. Letter grades are graded; `S`/`U` imply S/U; `P`/`N` imply P/N; `IP` means no grade yet. `F`, `N`, `U`, and withdrawals are dropped from the transcript by the loader, just as for real students.

| Flag | Meaning |
|---|---|
| `transfer` | transfer credit (`course_type: TR`, not St. Olaf; institution `XFER` unless `inst=`) |
| `ap` | AP credit (`course_type: AP`, not St. Olaf) |
| `su=C` | the letter grade behind an `S`/`U` |
| `incomplete` | `flag_incomplete` |
| `repeat` | `flag_repeat` |
| `repeated-later` | this attempt was repeated later (`transcript_code: R`); the loader drops it |
| `lab` | a lab section (`sub_type: lab`) |
| `credits=0.50` | credits (default `1.00`) |
| `gereqs=WRI,FYW` | gen-ed codes |
| `attrs=a,b` | course attributes |
| `inst=CARL` | institution |
| `"name=Some Title"` | course name (quote it if it has spaces) |
| `level=300` | level (default: the number's hundreds) |

Each course's `clbid` is `SUBJ NUM[.SECTION][.L] YEAR-TERM`, e.g. `DEPT 202 2019-3`. Exceptions refer to courses by that `clbid`. For anything the short form cannot say, use a mapping and override fields directly:

```yaml
courses:
  - {course: DEPT 390 2020-3 B, gereqs: [WRI], name: Capstone}
```

### Exceptions

Use the auditor's exception format, including `area_code`. Paths are the full result paths, including the `.count`/`[i]` segments a top-level `all:` introduces:

```yaml
exceptions:
  - {area_code: T400, type: insert, path: ['$', '.count', '[1]', '%Electives', '.query'], clbid: OTHR 250 2019-1}
```

To see the paths, expand the student and run `python3 -m dp --student <json> --area <yaml>`; every rule prints its path.

### Expectations

`expect` has one entry per declared area:

- `status` (required): the area's overall status — `done`, `needs-more-items`, `pending-current`, `pending-registered`, `waived`, `empty`, `pending-approval`, or `failed-invariant`.
- `requirements` (optional): requirement statuses by name; nested requirements join names with `/`, e.g. `Common Requirements/Credits at a C or higher`.
- `gpa` (optional): a quoted string, e.g. `'3.66'`.
- `known_issue` (optional): see below.

Only what you list is checked, so list what the fixture exists to show. The snapshot catches everything else. A rule with nothing matched reports `empty`, not `needs-more-items`, and an `override` exception reports `waived`.

Write the expectation from the area's rules **before** running the audit. If the audit disagrees, work out whether the fixture or the engine is wrong. Don't just copy the engine's answer.

### Known issues

When the engine gets a fixture wrong, keep the correct expectation and add `known_issue: "<what goes wrong>"`. The test becomes a strict xfail: it is reported as an expected failure today, and fails loudly once the engine is fixed, telling you to remove the marker. Known-issue pairs have no snapshot, so a bug is never recorded as correct output.

## Running

```shell script
pytest tests/test_fixtures.py                       # audit every fixture
pytest tests/test_fixtures.py -k t300               # just one family
pytest tests/test_fixtures.py --update-snapshots    # accept intended changes, prune stale snapshots
pytest tests/test_fixtures.py -rx                   # list the known issues
```

A snapshot diff in a pull request is a change in audit output; review it as such.

## Using fixtures as dev data

```shell script
# one student as standard student JSON
python3 -m dp.bin.fixture expand fixtures/students/composite-double-major.yaml > /tmp/student.json

# audit it
python3 -m dp --student /tmp/student.json --area fixtures/areas/2020-21/T901.yaml

# every student, as <id>.json
python3 -m dp.bin.fixture expand-all --out build/fixture-students
```

To run the whole corpus through `dp.bin.batch`, which reads `<stnum>.json` files and takes `stnum catalog code` lines on stdin, use `--by-stnum`:

```shell script
python3 -m dp.bin.fixture expand-all --by-stnum --out build/fixture-students \
    | python3 -m dp.bin.batch --dir build/fixture-students --areas-dir fixtures/areas
```

Anything else that takes an areas directory (such as the server's area root) can use `fixtures/areas`.

## Feature index

| Feature | Areas | Students |
|---|---|---|
| `course` rules | T100 | `t100-complete`, `t100-missing-course`, `t100-failed-course` |
| catalog-year resolution | T100 (2020-21, 2021-22) | `t100-catalog-2021` |
| `all` / `any` / `both` / `either` | T101 | `t101-complete`, `t101-half-of-both` |
| `count` / `of` | T110 | `t110-two-courses`, `t110-course-and-requirement`, `t110-only-one` |
| query aggregates (`count(courses)`, `sum(credits)`, `count(terms)`, `count(subjects)`, `average(grades)`, `count(distinct_courses)`) | T200 | `t200-complete`, `t200-low-grades`, `t200-one-term-one-subject` |
| query `limit` | T300 | `t300-one-transfer`, `t300-two-transfers` |
| claiming, `allow_claimed` | T310 | `t310-claimed-course`, `t310-separate-writing` (known issue) |
| `multicountable` | T311 | `t311-multicountable` (known issue) |
| exceptions: insert, override, block | T400 | `t400-no-exceptions`, `t400-insert`, `t400-block` |
| S/U during COVID (`$during_covid`) | T500 | `t500-su-during-covid`, `t500-su-outside-covid` |
| in-progress vs registered | T500 | `t500-in-progress`, `t500-registered` |
| repeated courses, GPA | T500 | `t500-repeated` |
| common major requirements | T900, T901 | `composite-imaginary-studies`, `composite-double-major` |
| double major | T900 + T901 | `composite-double-major` |
| music performances, recitals, proficiencies | — | — |
| templates | — | — |
| `count(areas)` | — | — |
| contracts | — | — |
| `department_audited` | — | — |
| area-level `audit` assertions | — | — |
| global `limit` | — | — |
| `in_gpa` | — | — |
| conditionals | — | — |
