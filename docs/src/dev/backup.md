## Данные

Снять дамп на рабочей машине:

```bash
docker compose -f compose.dev.yaml exec -T pg sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl' > paprika.sql
```

Скопировать дамп на сервер:

```bash
rsync -avz paprika.sql user@server:~
```

Накатить дамп на сервере:

```bash
user@server:~/paprika_v2$ docker compose -f compose.prod.yaml exec -T pg sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < ../paprika.sql
```

## Медиа файлы

Копируем папку с файлами на сервер:

```bash
rsync -ahr --progress /NAS/tech/repos/paprika/backup_v2/paprika_media user@server:~
```

Перемещаем файлы в том:

```bash
user@server:~$ sudo mv paprika_media/* /var/lib/docker/volumes/paprika_v2_media_data/_data/
```
