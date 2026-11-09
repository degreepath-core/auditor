# Degreepath, the automated degree auditor

> Gobbldygook lives!

Degreepath is a tool to perform automated, comprehensive, and fast degree audits.

**Automated**: (eventually) A web interface, for reviewing the status of a cohort of students and for running reports

**Comprehensive**: Just checking degree audits? Nah. How about running graduation, general education, major, and concentration/minor audits, all at once?

**Fast**: (eventually) And of course, this only makes sense to run if it's faster than doing the checks by hand. Luckily, computers are fast, and they can do lots of things at once!

---

Requires Python 3.15+ and [uv](https://docs.astral.sh/uv/). uv will download Python 3.15 for you if it isn't installed.

```shell script
$ uv sync                    # creates .venv with runtime + dev/test dependencies
$ uv sync --all-groups       # ...plus the optional excel dependencies
$ uv run python -m dp --help
```

To run tests:

```shell script
$ uv run pytest  # or, with coverage, uv run pytest --cov=dp
```

Other commands:

## CLI

```shell script
$ uv run python -m dp --help
```

The main CLI entry point; see `--help`.

Basic usage is as follows:

```shell script
# somehow get a student JSON file; documentation coming at some point
# area.yaml can be any .yaml file in the stolaf-areas repository
$ uv run python -m dp --student <student.json> --area <area.yaml>
```

## Batch Job Server

The `dp.server` module handles sorting through the queued jobs, both batched and one-off what-ifs.

Basic usage is as follows:

```shell script
# start listening for events from postgres
$ uv run python -m dp.server &
# fetch the next batch of students to audit from SIS and queues them in postgres
$ uv run python -m dp.server.batch
# or, run a one-off what-if audit
$ uv run python -m dp.server.whatif --student <file> --code <code> --catalog <catalog>
```

The `dp.server.audit` module encapsulates driving the auditor and storing the final result into postgres.

## Misc. Scripts

- You can pair up `uv run python -m dp.bin.index <QUERY> | uv run python -m dp.bin.batch` to run batches of audits quickly on a folder of student files.
- `uv run python -m dp.bin.discover <area-file>` will give you a list of the bucket references and static course references contained within.
- `uv run python -m dp.bin.expand <student-file>` will print (student_file, area_file) pairs to stdout, one for each area in the student.
- `uv run python -m dp.bin.print <student-file> <output-json>` will print the same output that `-m dp` generates.
- `uv run python -m dp.bin.validate <area-file>` will validate that an area specification is syntactically valid.

## Fancier CLI

```shell script
$ uv run python -m dp.testbed --help
```

Allows eas[ier] benchmarking of changes against the stable branch.

Usage:

```shell script
$ uv run python -m dp.testbed fetch
$ uv run python -m dp.testbed baseline
$ uv run python -m dp.testbed branch <name>
$ uv run python -m dp.testbed compare <name>
```

---

Dependencies are declared in `pyproject.toml` and locked in `uv.lock`. Use `uv add` / `uv remove` to change them (with `--group <name>` for the groups below), and `uv lock --upgrade` to bump everything.

| dependency group | why                                                    | installed by default |
| ---------------- | ------------------------------------------------------ | -------------------- |
| _(main)_         | Common runtime dependencies                            | yes                  |
| `dev`            | Linting and type checking - flake8, mypy               | yes                  |
| `test`           | pytest and plugins                                     | yes                  |
| `server`         | Database and HTTP dependencies for `dp.server`         | via `dev`             |
| `excel`          | `openpyxl`, for `dp.bin.excelify`                      | no (`--group excel`)  |
