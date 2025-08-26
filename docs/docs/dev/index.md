# Настройка dev-окружения

Для запуска Паприки для разработки нужны следующие пакеты:

- `git`
- `make`
- `docker`
- `nodejs`

Скачайте исходный код и перейдите в папку репозитория:

```bash
git clone https://github.com/romanvolodin/paprika.git
cd paprika/
```

Для настройки dev-окружения выполните команду:

```bash
make dev.init
```

Эта команда создаст необходимые контейнеры и `.env` файл в корне проекта.

## ВАЖНО: На данный момент также необходимо сделать следующее

- Создать отдельный `.env` в корне фронтенда с адресом и портом, на котором запускается dev-контейнер бэкенда:

  ```bash
  echo "VITE_API_URL=http://localhost:8000/" > frontend/.env
  ```

- Установить зависимости фронтенда

```bash
npm install --prefix frontend/
```

чтобы создать папку `node_modules`. Это необходимо для запуска контейнера со фронтендом.

## Запуск dev-версии

```bash
make dev
```

## Наполняем сайт данными

Предполагается, что у вас есть дамп данных и медиа-файлы. TODO: нужен небольшой демо-проект.

Ниже есть инструкция как скачать данные с рабочего сервера.

### Заполняем базу данных

Копируем дамп данных в докер и запускаем команду `loaddata`:

```bash
sudo cp /path/to/dump.json /var/lib/docker/volumes/paprika_media_volume/_data
docker compose --file docker-compose-dev.yml exec paprika-app ./manage.py loaddata media/dump.json
```

### Копируем медиа-файлы

Предположим, что медиа-файлы скачаны в папку `paprika_media`. Копируем содержимое этой папки в докер:

```bash
sudo rsync -ahr --progress /path/to/paprika_media/* /var/lib/docker/volumes/paprika_media_volume/_data
```

Проверяем:

```bash
sudo ls /var/lib/docker/volumes/paprika_media_volume/_data
```

Должно вывести что-то вроде этого — папка с аватарками пользователей и папки с файлами проектов:

```bash
avatars  PRJ1  PRJ2  ...
```

После этого все картинки и видео должны корректно отображаться на сайте.

## Скачать дамп с рабочего сервера

Здесь и далее `paprika-prod` — это [ssh алиас](../admin/ssh-alias.md) для рабочего сервера.

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
