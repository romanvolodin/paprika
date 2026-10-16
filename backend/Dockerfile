# syntax = docker/dockerfile:1

FROM python:3.14-slim AS base

# Needed for fixing permissions of files created by Docker:
ARG UID=1000 \
  GID=1000

ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONHASHSEED=random \
  PYTHONDONTWRITEBYTECODE=1 \
  # pip:
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_DEFAULT_TIMEOUT=100 \
  PIP_ROOT_USER_ACTION=ignore \
  # uv:
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy \
  UV_PROJECT_ENVIRONMENT=/usr/local \
  UV_CACHE_DIR='/var/cache/uv'

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

RUN apt-get update && apt-get upgrade -y \
  && apt-get install --no-install-recommends -y \
    bash \
    brotli \
    curl \
    ffmpeg \
    gettext \
    git \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && apt-get clean -y && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.22 /uv /usr/local/bin/uv

WORKDIR /app

RUN groupadd -g "${GID}" -r paprika \
  && useradd -d '/app' -g paprika -l -r -u "${UID}" paprika \
  && chown paprika:paprika -R '/app' \
  # Static and media files:
  && mkdir -p '/var/lib/paprika/static' '/var/lib/paprika/media' \
  && chown paprika:paprika '/var/lib/paprika/static' '/var/lib/paprika/media'

COPY --chown=paprika:paprika ./uv.lock ./pyproject.toml /app/

RUN --mount=type=cache,target="$UV_CACHE_DIR" \
  uv sync --no-dev

FROM base AS dev
RUN --mount=type=cache,target="$UV_CACHE_DIR" \
  uv sync --dev
COPY . .
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS prod
COPY --chown=paprika:paprika . .
USER paprika
EXPOSE 8000
CMD ["gunicorn", "paprika.wsgi:application", "--bind", "0.0.0.0:8000", "--worker-class", "gthread", "--workers", "3", "--threads", "4", "--timeout", "120"]
