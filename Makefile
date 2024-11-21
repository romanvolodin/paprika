run:
	docker compose up --detach --build

collectstatic:
	docker compose exec paprika-app ./manage.py collectstatic --no-input

migrate:
	docker compose exec paprika-app ./manage.py migrate

createsuperuser:
	docker compose exec paprika-app ./manage.py createsuperuser

prod:	run collectstatic migrate createsuperuser
