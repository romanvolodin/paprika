RANDOM_DB_USER=$$(tr -dc 'A-Za-z' </dev/urandom | head -c 6; echo)
RANDOM_DB_PASSWORD=$$(tr -dc 'A-Za-z0-9~_-' </dev/urandom | head -c 10; echo)
RANDOM_SECRET_KEY=$$(tr -dc 'A-Za-z0-9~_-' </dev/urandom | head -c 64; echo)
ALLOWED_HOSTS?=localhost,127.0.0.1

env:
	cp -n .env.template .env
	sed -i "s/db_user/$(RANDOM_DB_USER)/" .env
	sed -i "s/db_password/$(RANDOM_DB_PASSWORD)/" .env
	sed -i "s/secret_key/$(RANDOM_SECRET_KEY)/" .env
	sed -i "s/allowed_hosts/$(ALLOWED_HOSTS)/" .env
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
