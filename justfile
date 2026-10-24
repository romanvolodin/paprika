RED := `printf '\033[31m'`
PURPLE := `printf '\033[35m'`
RESET-COLOR := `printf '\033[0m'`

MODE := `cat .paprika-mode 2>/dev/null || true`
COMPOSE-FILE := if MODE == "prod" { "compose.prod.yaml" } else { "compose.dev.yaml" }
MANAGE := if MODE == "prod" { "python manage.py" } else { "uv run manage.py" }

default:
  @just --list

_require-mode:
  @if [ "{{MODE}}" != "dev" ] && [ "{{MODE}}" != "prod" ]; then \
    echo "{{RED}}Not initialized yet. Run 'just init dev' or 'just init prod <domain>' first.{{RESET-COLOR}}"; \
    exit 1; \
  fi

init mode domain='':
  @if [ -f .paprika-mode ]; then \
    echo "{{RED}}Already initialized as '$(cat .paprika-mode)' (see .paprika-mode). Remove that file to reinit.{{RESET-COLOR}}"; \
    exit 1; \
  fi
  @if [ "{{mode}}" = "dev" ]; then \
    just _init-dev; \
  elif [ "{{mode}}" = "prod" ] && [ -n "{{domain}}" ]; then \
    just _init-prod {{domain}}; \
  else \
    echo "{{RED}}Usage: just init dev  |  just init prod <domain>{{RESET-COLOR}}"; \
    exit 1; \
  fi

_init-dev:
  @echo "{{PURPLE}}Setting up dev environment...{{RESET-COLOR}}"
  cd backend/ && uv run pre-commit install && cd ..
  @if [ ! -f backend/.env ]; then \
    echo "{{PURPLE}}Creating backend/.env from template...{{RESET-COLOR}}"; \
    cp backend/.env.template backend/.env; \
  else \
    echo "{{RED}}backend/.env already exists, leaving it as-is.{{RESET-COLOR}}"; \
  fi
  echo dev > .paprika-mode
  docker compose -f compose.dev.yaml up --build --detach
  docker compose -f compose.dev.yaml exec backend uv run manage.py migrate
  docker compose -f compose.dev.yaml down
  @echo "{{PURPLE}}Done - run 'just dev' to start working.{{RESET-COLOR}}"

_init-prod domain:
  @case "{{domain}}" in \
    */*|http*) echo "{{RED}}Give a bare domain, e.g. paprika.example.com (no scheme, no path).{{RESET-COLOR}}"; exit 1 ;; \
  esac
  @echo "{{PURPLE}}Setting up production for {{domain}}...{{RESET-COLOR}}"
  @read -p "Email for Let's Encrypt renewal notices: " caddy_email; \
  secret_key=$(openssl rand -base64 48); \
  db_password=$(openssl rand -base64 32); \
  cp backend/.env.template backend/.env; \
  sed -i "s|^PAPRIKA_SECRET_KEY=.*|PAPRIKA_SECRET_KEY=$secret_key|" backend/.env; \
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$db_password|" backend/.env; \
  sed -i "s|^PAPRIKA_ALLOWED_HOSTS=.*|PAPRIKA_ALLOWED_HOSTS={{domain}}|" backend/.env; \
  { echo ""; echo "PAPRIKA_DOMAIN={{domain}}"; echo "CADDY_EMAIL=$caddy_email"; } >> backend/.env
  echo prod > .paprika-mode
  @echo "{{PURPLE}}Written backend/.env - review it, then:{{RESET-COLOR}}"
  @echo "{{PURPLE}}  1) make sure {{domain}} already points at this server (DNS){{RESET-COLOR}}"
  @echo "{{PURPLE}}  2) run 'just run', then 'just superuser'{{RESET-COLOR}}"

dev: _require-mode
  @if [ "{{MODE}}" != "dev" ]; then echo "{{RED}}This machine is set up for '{{MODE}}', not dev.{{RESET-COLOR}}"; exit 1; fi
  @echo "{{PURPLE}}Running dev environment... Ctrl+C to stop.{{RESET-COLOR}}"
  docker compose -f compose.dev.yaml up --build

run: _require-mode
  @if [ "{{MODE}}" != "prod" ]; then echo "{{RED}}This machine is set up for '{{MODE}}', not prod.{{RESET-COLOR}}"; exit 1; fi
  @echo "{{PURPLE}}Building and starting production stack...{{RESET-COLOR}}"
  docker compose -f compose.prod.yaml up --build --detach

update: _require-mode
  @if [ "{{MODE}}" != "prod" ]; then echo "{{RED}}'update' is for prod - use 'just dev' locally.{{RESET-COLOR}}"; exit 1; fi
  @echo "{{PURPLE}}Checking for local changes...{{RESET-COLOR}}"
  @if [ -n "$(git status --porcelain --untracked-files=no)" ]; then \
    echo "{{RED}}Tracked files have uncommitted changes - resolve that first, aborting.{{RESET-COLOR}}"; \
    exit 1; \
  fi
  @echo "{{PURPLE}}Pulling latest changes...{{RESET-COLOR}}"
  git pull --ff-only
  just run

down: _require-mode
  docker compose -f {{COMPOSE-FILE}} down

logs *ARGS: _require-mode
  docker compose -f {{COMPOSE-FILE}} logs -f {{ARGS}}

status:
  @if [ "{{MODE}}" = "" ]; then echo "Mode: not initialized"; else echo "{{PURPLE}}Mode: {{MODE}}{{RESET-COLOR}}"; fi
  @if [ "{{MODE}}" != "" ]; then docker compose -f {{COMPOSE-FILE}} ps; fi

migrations *ARGS: _require-mode
  docker compose -f {{COMPOSE-FILE}} exec backend {{MANAGE}} makemigrations {{ARGS}}

migrate: _require-mode
  docker compose -f {{COMPOSE-FILE}} exec backend {{MANAGE}} migrate

superuser: _require-mode
  docker compose -f {{COMPOSE-FILE}} exec backend {{MANAGE}} createsuperuser

backup: _require-mode
  @if [ "{{MODE}}" = "dev" ]; then \
    docker compose -f compose.dev.yaml exec -T pg sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl' > "paprika-dev-backup-$(date +%Y%m%d-%H%M%S).sql"; \
  elif [ "{{MODE}}" = "prod" ]; then \
    docker compose -f compose.prod.yaml exec -T pg sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl' > paprika.sql; \
  fi

test *ARGS:
  docker compose -f compose.dev.yaml exec backend uv run pytest {{ARGS}}

# Regenerate frontend/src/api/schema.ts from the running backend's OpenAPI schema.
generate-api-types:
  docker compose -f compose.dev.yaml exec frontend npm run generate-api-types -- http://backend:8000/api/v1/docs/openapi.json

frontend-test *ARGS:
  docker compose -f compose.dev.yaml exec frontend npm run test {{ARGS}}

frontend-lint:
  docker compose -f compose.dev.yaml exec frontend npm run lint

