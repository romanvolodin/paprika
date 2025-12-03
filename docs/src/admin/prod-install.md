# Запуск Паприки

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
make prod ALLOWED_HOSTS=dev.paprika-app.ru ALLOWED_CORS=http://dev.paprika-app.ru
```

Эта команда сделает следующее:

- Создаст `.env`-файл из шаблона и заполнит его. Будут сгенерированы случайное имя пользователя и пароль для подключения к базе данных, случайный секретный ключ для Джанго, в разрешенные хосты будет записано значение `ALLOWED_HOSTS`. Вместо `your-domain.com` укажите свой домен или IP-адрес сервера. Домен в `ALLOWED_CORS` **обязательно** должен содержать `http://` или `https://`.
- Запустит Докер-контейнеры в фоновом режиме.
- Соберет статику.
- Выполнит миграции.
- Попросит ввести почту и пароль суперпользователя.

## Что дальше

- [Сохранение медиа-файлов на сетевой диск](./mount-nas.md)

- [Восстановление бэкапов](./restore-backup.md)

- **Настройка бэкапа** — полноценной статьи нет, есть старая статья: [Бэкап данных](../dev/backup.md). И там только про бэкап данных. Медиа-файлы просто скачиваю через `rsync` вручную с некоторой периодичность.
