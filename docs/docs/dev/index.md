# Для разработчика

`paprika-prod` — это ssh алиас для рабочего сервера.

## Скачать дамп с рабочего сервера

```bash
ssh paprika-prod "cd paprika/ && docker compose exec paprika-app python manage.py dumpdata --exclude=contenttypes --exclude=auth.permission > datadump.json"
scp paprika-prod:paprika/datadump.json ./datadump.json
ssh paprika-prod "rm paprika/datadump.json"
```

## Скачать медиа с рабочего сервера

Скачать всю папку целиком:

```bash
rsync -avz --progress --log-file=rsync.log paprika-prod:/mnt/NAS/media .
```

Скачать только `*.jpg` с сохранением структуры директорий:

```bash
rsync -avz --progress --log-file=rsync.log --include='*/' --include='*.jpg' --exclude='*' paprika-prod:/mnt/NAS/media .
```

Важно:

- Порядок include/exclude важен. Сначала разрешаем вход в директории (\*/) и включаем нужные файлы, потом всё остальное исключаем.
- Убедитесь, что на стороне источника есть доступ к файлам (права чтения).
