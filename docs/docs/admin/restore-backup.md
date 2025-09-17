# Восстановление бэкапов

Восстанавливаем бэкап на рабочем сервере. Предполагается, создан [ssh алиас](ssh-alias.md) для рабочего сервера — `paprika-prod`.

## Заполняем базу данных

Копируем дамп данных на сервер:

```bash
rsync -avz dump.json paprika-prod:/var/lib/docker/volumes/paprika_media_volume/_data/
```

Заполняем базу данных из дампа:

```bash
ssh paprika-prod "cd paprika/ && docker compose exec paprika-app python manage.py loaddata media/dump.json"
```

## Копируем медиа-файлы

Перейдите в папку с файлами и выполните команду:

```bash
rsync -ahr --progress ./* paprika-prod:/var/lib/docker/volumes/paprika_media_volume/_data
```
