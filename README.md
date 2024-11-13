# paprika

## Деплой

Устанавливаем гит (если его нет), клонируем репозиторий и переключаемся в ветку с Докером:

```bash
apt install git
git clone git@github.com:romanvolodin/paprika.git
# если не проброшен ssh ключ, то
# git clone https://github.com/romanvolodin/paprika.git

cd paprika
git checkout docker
```

### Docker

Добавляем ключ и репозиторий Докера (команды взяты из [документации](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)):

```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get -y install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```

Устанавливаем Докер и плагины:

```bash
sudo apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Если вы работаете под `root`-пользователем, то можно переходить к следующему разделу. Иначе нужно разрешить запуск Докера вашему пользователю:

```bash
sudo groupadd docker
sudo usermod -aG docker $USER
```

Чтобы изменения вступили в силу нужно разлогиниться и заново войти в систему (иногда нужно перезагрузить машину):

```bash
logout
# или
# reboot
```

```bash
nano .env

POSTGRES_DB=db_name
POSTGRES_USER=db_user
POSTGRES_PASSWORD=db_passwd

PAPRIKA_SECRET_KEY=dev
PAPRIKA_DEBUG=true
PAPRIKA_ALLOWED_HOSTS=123.45.67.8

POSTGRES_HOST=db
POSTGRES_PORT=5432

DATABASE_URL=postgres://db_user:db_passwd@db:5432/db_name
```

Запускаем Паприку, создаем таблицы в БД, создаем суперпользователя, собираем статические файлы (JS, CSS, картинки и прочее):

```bash
docker compose up --build --detach
docker compose exec app ./manage.py collectstatic --no-input
docker compose exec app ./manage.py migrate
docker compose exec app ./manage.py createsuperuser
```

Обновление:

```bash
# cd paprika/
# git pull
/root/paprika/venv/bin/python backend/manage.py collectstatic --noinput
# sudo systemctl restart paprika.service
```

## Бэкап данных

Не сохраняются `auth.permissions` и `contenttypes`, чтобы избежать ошибки `IntegrityError` при дальнейшей загрузке данных. Происходит она потому, что Джанго заново генерит id записей. Эту ошибку должны исправить ключи `--natural-primary` и `--natural-foreign`, но указанные таблицы пока всё равно не сохраняются. Считай это данью традиции.

Таблицы `sessions.session` и `admin.logentry` игнорируются, ибо не содержат важных данных (это сессии и лог действий в админке).

```bash
cd paprika_ZS_backup/

# /root/paprika/venv/bin/python /root/paprika/backend/manage.py dumpdata --format=json --indent=2 \
#   --natural-primary \
#   --natural-foreign \
#   --exclude sessions.session \
#   --exclude auth.permission \
#   --exclude admin.logentry \
#   --exclude contenttypes \
#   --output /root/paprika_ZS_backup/dump/ZS_dump.json

# git add .
# git commit -m "backup"
# git push
```

Чтобы залить бэкап:

```bash
cp -r /root/paprika_ZS_backup/media/* /var/lib/docker/volumes/paprika_media_volume/_data
cp /root/paprika_ZS_backup/dump/ZS_dump.json /var/lib/docker/volumes/paprika_media_volume/_data
docker compose exec app ./manage.py loaddata media/ZS_dump.json

```

## (Возможно устарело) Заметки по запуску Паприки через докер

Устанавливаем Докер:

<https://docs.docker.com/engine/install/ubuntu/>

Я ставил из Докеровского апт репозитория

Настраиваем разрешение запускать Докер не от рутового пользователя:

<https://docs.docker.com/engine/install/linux-postinstall/>

Важно выйти и войти в систему (или перезагрузить комп), чтобы подхватились настройки

## Запуск Паприки

### Предварительные требования

- Создать `.env` с настройками БД в корне проекта

Пример:

```bash
POSTGRES_DB=db_name
POSTGRES_USER=db_user
POSTGRES_PASSWORD=db_passwd

DATABASE_URL=postgres://db_user:db_passwd@db:5432/db_name
```

- Создать `.env` с настройками Паприки в папке `backend/`.

Пример:

```bash
PAPRIKA_SECRET_KEY=lb0rb08^80*62%5+cz0ba^-yta5_ef53dwp^^jlb0bu
PAPRIKA_DEBUG=false
PAPRIKA_ALLOWED_HOSTS=127.0.0.1,localhost
```

### Запускаем

Запустите базу данных и сайт:

```bash
docker compose up
```

Версия для разработки:

```bash
docker compose -f docker-compose-dev.yml up
```

В новом терминале не выключая сайт запустите команды для настройки базы данных:

```bash
docker compose exec app ./manage.py migrate
docker compose exec app ./manage.py createsuperuser
```

Для разработки:

```bash
docker compose -f docker-compose-dev.yml exec app ./manage.py migrate
docker compose -f docker-compose-dev.yml exec app ./manage.py createsuperuser
```
