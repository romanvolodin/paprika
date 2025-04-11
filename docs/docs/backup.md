# Бэкап данных

Ниже даны команды для использования во время разработки.

Для боевого сервера нужно убрать аргумент `--file docker-compose-dev.yml`.

```sh
docker compose --file docker-compose-dev.yml exec paprika-app ./manage.py dumpdata \
 --format=json \
 --indent=2 \
 --natural-primary \
 --natural-foreign \
 --exclude sessions.session \
 --exclude auth.permission \
 --exclude admin.logentry \
 --exclude contenttypes \
 --output dump.json
```

Не сохраняются `auth.permissions` и `contenttypes`, чтобы избежать ошибки `IntegrityError` при дальнейшей загрузке данных. Происходит она потому, что Джанго заново генерит id записей. Эту ошибку должны исправить ключи `--natural-primary` и `--natural-foreign`, но указанные таблицы пока всё равно не сохраняются. Считай это данью традиции.

Таблицы `sessions.session` и `admin.logentry` игнорируются, ибо не содержат важных данных (это сессии и лог действий в админке).

## Бэкап медиа

Установка Я.Диска

echo "deb http://repo.yandex.ru/yandex-disk/deb/ stable main" | sudo tee -a /etc/apt/sources.list.d/yandex-disk.list > /dev/null && wget http://repo.yandex.ru/yandex-disk/YANDEX-DISK-KEY.GPG -O- | sudo apt-key add - && sudo apt-get update && sudo apt-get install -y yandex-disk

yandex-disk token -- Важно! выберите правильный аккаунт в браузере

Если ошиблись -- удалите .config/yandex-disk/passwd и попробуйте заново

Указываем папку
nano .config/yandex-disk/config.cfg
dir=/root/paprika/backend/media_backup

## Заполняем базу данными

```sh
cp dump.json /var/lib/docker/volumes/paprika_media_volume/_data
docker compose --file docker-compose-dev.yml exec paprika-app ./manage.py loaddata media/dump.json
```
