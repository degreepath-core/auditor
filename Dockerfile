FROM rust:1.50-buster AS builder

WORKDIR /usr/src/reports

COPY ./Cargo.toml ./
COPY ./Cargo.lock ./
COPY ./reports ./reports
COPY ./src ./src
COPY ./formatter ./formatter

RUN cargo build --release --bin dp-report

FROM python:3.15-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

WORKDIR /usr/src/app

# Use the image's Python rather than downloading one, and keep the venv
# self-contained (no hardlinks into a cache that isn't in the image).
ENV UV_PYTHON_DOWNLOADS=never \
	UV_LINK_MODE=copy \
	UV_NO_CACHE=1

ENV PGPASSFILE /opt/.pgpass

RUN mkdir /opt/areas
ENV AREA_ROOT /opt/areas

RUN touch .env

COPY pyproject.toml uv.lock .python-version ./

RUN uv sync --locked --no-default-groups --group server

COPY dp ./dp

COPY docker-install-packages.sh ./docker-install-packages.sh
RUN bash ./docker-install-packages.sh

COPY docker-healthcheck.sh ./docker-healthcheck.sh

ENV DP_REPORT_BIN /opt/dp-report
COPY --from=builder /usr/src/reports/target/release/dp-report /opt/dp-report

HEALTHCHECK --start-period=5s \
	CMD bash ./docker-healthcheck.sh

CMD ["uv", "run", "--no-sync", "python", "-m", "dp.server"]
