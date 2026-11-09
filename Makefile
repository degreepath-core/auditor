all: lint

lint: flake mypy test
check: lint

flake:
	uv run flake8 --show-source --statistics dp/

mypy:
	uv run mypy --pretty --show-error-codes dp/

test:
	uv run pytest tests/ dp/

watch:
	uv run --with pytest-watch ptw

push: lint
	git push

validate:
	uv run python -m dp.bin.validate ../degreepath-areas/*/**.yaml --break

profile:
	echo 'use pyinstrument'
	echo 'or use py-spy'

nuitka:
	uv run --with nuitka python -m nuitka --standalone --follow-imports --plugin-enable=pylint-warnings --python-flag=no_site --warn-unusual-code --warn-implicit-exceptions dp/__main__.py

sync:
	uv sync --all-groups

lock:
	uv lock

upgrade:
	uv lock --upgrade

.PHONY: sync lock upgrade nuitka profile validate push watch test mypy lint flake check all

###

report-%.html:
	cargo run --release --bin dp-major-report -- ./testbed_db.db "$(*F)" --as-html > "${@}"

summary-%.html:
	cargo run --release --bin dp-major-summary -- ./testbed_db.db "$(*F)" --as-html > "${@}"

upload-reports:
	scp summary-*.html report-*.html "ola:/home/www/sis/dp-report/"
