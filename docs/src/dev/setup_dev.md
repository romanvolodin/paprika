just init dev

just dev

В отдельном терминале, в корне репозитория:

```bash
docker compose -f compose.dev.yaml exec -T pg sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < /path/to/paprika.sql
```

!!! info "Полезно"

    Иногда нужно удалить все данные перед наполнением базы данных

    ```bash
    docker compose -f compose.dev.yaml exec -T pg sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'
    ```

sudo rsync -ah --info=progress2 /NAS/tech/repos/paprika/backup/paprika_media/media/ backend/media/
