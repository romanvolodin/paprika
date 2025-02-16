RANDOM_DB_USER=$$(tr -dc 'A-Za-z' </dev/urandom | head -c 6; echo)
RANDOM_DB_PASSWORD=$$(tr -dc 'A-Za-z0-9~_-' </dev/urandom | head -c 10; echo)
RANDOM_SECRET_KEY=$$(tr -dc 'A-Za-z0-9~_-' </dev/urandom | head -c 64; echo)
ALLOWED_HOSTS?=localhost,127.0.0.1
ALLOWED_CORS?=http://localhost:5173,http://localhost

env:
	cp -n .env.template .env
	sed -i "s/db_user/$(RANDOM_DB_USER)/" .env
	sed -i "s/db_password/$(RANDOM_DB_PASSWORD)/" .env
	sed -i "s/secret_key/$(RANDOM_SECRET_KEY)/" .env
	sed -i "s/allowed_hosts/$(ALLOWED_HOSTS)/" .env
	sed -i "s~allowed_cors~$(ALLOWED_CORS)~" .env
	sed -i '/DJANGO_SUPERUSER_EMAIL/d' .env
	sed -i '/DJANGO_SUPERUSER_PASSWORD/d' .env

run:
	docker compose up --detach --build

collectstatic:
	docker compose exec paprika-app ./manage.py collectstatic --no-input

migrate:
	docker compose exec paprika-app ./manage.py migrate

createsuperuser:
	docker compose exec paprika-app ./manage.py createsuperuser

prod:	env run collectstatic migrate createsuperuser

init.dev:
	cp -n .env.template .env.dev
	sed -i "s/PAPRIKA_DEBUG=false/PAPRIKA_DEBUG=true/" .env.dev
	sed -i "s/allowed_hosts/$(ALLOWED_HOSTS)/" .env.dev
	sed -i "s~allowed_cors~$(ALLOWED_CORS)~" .env.dev
	docker compose --file docker-compose-dev.yml up --build --detach
	docker compose --file docker-compose-dev.yml exec paprika-app ./manage.py collectstatic --no-input
	docker compose --file docker-compose-dev.yml exec paprika-app ./manage.py migrate
	docker compose --file docker-compose-dev.yml exec paprika-app ./manage.py createsuperuser --no-input
	docker compose --file docker-compose-dev.yml down

dev:
	docker compose --file docker-compose-dev.yml up --build

stop.dev:
	docker compose --file docker-compose-dev.yml down

env.dev:
	cp -n .env.template .env.dev
	sed -i "s/PAPRIKA_DEBUG=false/PAPRIKA_DEBUG=true/" .env.dev

collectstatic.dev:
	docker compose exec --file docker-compose-dev.yml paprika-app ./manage.py collectstatic --no-input

migrate.dev:
	docker compose --file docker-compose-dev.yml exec paprika-app ./manage.py migrate
