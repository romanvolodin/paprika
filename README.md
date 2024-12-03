# paprika

## Подготовка

Для запуска Паприки нужны следующие пакеты:

- `git`
- `make`
- `docker`

Паприка разрабатывается в Ubuntu, команды будут соответствующие.

### Устанавливаем Git

```bash
sudo apt install -y git
```

### Устанавливаем Make

```bash
sudo apt install -y make
```

### Устанавливаем Docker

Добавляем ключ и репозиторий Docker, затем устанавливаем сам Docker и плагины (команды взяты из [документации](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository)):

```bash
sudo apt update
sudo apt -y install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update

sudo apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Если вы работаете под `root`-пользователем, то можно переходить к следующему разделу. Иначе нужно разрешить запуск Докера вашему пользователю.

Чтобы изменения вступили в силу нужно разлогиниться и заново войти в систему. Иногда нужно перезагрузить машину — для этого выполните `reboot` вместо `logout`:

```bash
sudo groupadd docker
sudo usermod -aG docker $USER
logout
```
### Клонируем репозиторий

Клонируем репозиторий и переходим в папку проекта:

```bash
git clone https://github.com/romanvolodin/paprika.git
cd paprika
```

## Запуск

Для запуска выполните в корне проекта команду:

```bash
make prod ALLOWED_HOSTS=your-domain.com
```

Эта команда сделает следующее:
- Создаст `.env`-файл из шаблона и заполнит его. Будут сгенерированы случайное имя пользователя и пароль для подключения к базе данных, случайный секретный ключ для Джанго, в разрешенные хосты будет записано значение `ALLOWED_HOSTS`. Вместо `your-domain.com` укажите свой домен или IP-адрес сервера.
- Запустит Докер-контейнеры в фоновом режиме.
- Соберет статику.
- Выполнит миграции.
- Попросит ввести почту и пароль суперпользователя.

## Обновление

Чтобы обновить Паприку выполните в корне проекта:

```bash
docker compose down
git pull
make run collectstatic migrate
```

## Запуск для разработки

При первом запуске выполните команду:

```bash
make init.dev
```

Эта команда сделает следующее:
- Создаст `.env.dev`-файл из шаблона. Переменная  `PAPRIKA_DEBUG` будет установлена в `true`.
- Запустит Докер-контейнеры.
- Соберет статику.
- Выполнит миграции.
- Создаст суперпользователя из `.env.dev` (по умолчанию — `admin@admin.com` с паролем `admin`).
- Остановит контейнеры.

Для запуска сервера для разработки (сейчас и в дальнейшем) используйте команду:

```bash
make dev
```

Для остановки сервера нажмите `Ctrl+C`. 

## Бэкап данных

Не сохраняются `auth.permissions` и `contenttypes`, чтобы избежать ошибки `IntegrityError` при дальнейшей загрузке данных. Происходит она потому, что Джанго заново генерит id записей. Эту ошибку должны исправить ключи `--natural-primary` и `--natural-foreign`, но указанные таблицы пока всё равно не сохраняются. Считай это данью традиции.

Таблицы `sessions.session` и `admin.logentry` игнорируются, ибо не содержат важных данных (это сессии и лог действий в админке).

```bash
cd paprika_ZS_backup/

/root/paprika/venv/bin/python /root/paprika/backend/manage.py dumpdata --format=json --indent=2 \
  --natural-primary \
  --natural-foreign \
  --exclude sessions.session \
  --exclude auth.permission \
  --exclude admin.logentry \
  --exclude contenttypes \
  --output /root/paprika_ZS_backup/dump/ZS_dump.json

git add .
git commit -m "backup"
git push
```

Чтобы залить бэкап:

```bash
cp -r /backup/media/* /var/lib/docker/volumes/paprika_media_volume/_data
cp /backup/dump/ZS_dump.json /var/lib/docker/volumes/paprika_media_volume/_data

docker compose exec paprika-app ./manage.py loaddata media/ZS_dump.json
```
