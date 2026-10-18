# Настройка VPS

Эта инструкция про то, как подготовить чистый сервер к запуску Паприки: выбрать VPS, создать пользователя, закрыть лишнее, проверить DNS.

Сервер уже готов? Переходите к [установке Паприки](production-run.md).

## Какой сервер нужен

- **2 ГБ RAM.** Для самого приложения хватит и 512 МБ. Но образы собираются прямо на сервере, а для сборки памяти нужно больше.
- **1 vCPU.** Для команды из нескольких человек достаточно. Образы будут собираться чуть дольше, и только.
- **20 ГБ диска.** Сами образы маленькие. Но база данных и загруженные файлы со временем разрастутся, поэтому берите с запасом. (TODO: нужна инструкция для подключения отдельного диска для загруженных файлов.)
- **Публичный IPv4-адрес** и возможность открыть порты **80** и **443**.

## Операционная система

Всё приложение работает в Docker. Подойдёт любая операционная система, где Docker запускается.

Сам я разрабатываю Паприку в основном на Ubuntu, поэтому все команды ниже — для неё.

## Создание пользователя

Большинство VPS выдают доступ пользователю `root` по паролю. Это стоит поменять сразу при первом подключении. Создадим обычного пользователя и настроим вход по SSH.

Имя может быть любым. Я назову его `rika` (потому что pap**rika**).

Подключитесь к серверу как `root` и выполните:

```bash
adduser rika
usermod -aG sudo rika
```

Скопируйте свой SSH-ключ на сервер. (TODO: нужна инструкция по созданию ключа.)

На локальной машине выполните:

```bash
ssh-copy-id rika@ваш-сервер
```

!!! warning "Важно"

    Сначала убедитесь, что новый пользователь работает: заходит на сервер и получает root через `sudo`. И только потом отключайте пароль и вход под root.

    Не закрывая текущее соединение с сервером, откройте **новый терминал** на локальной машине и выполните `ssh rika@ваш-сервер`. Затем запустите команду, которой нужен `sudo`, например `sudo apt update`.

    Так, если что-то пойдёт не так, у вас останется рабочее соединение, чтобы всё исправить.

Теперь закроем опасные способы входа по SSH.

Откройте файл дополнительных настроек. На сервере выполните:

```bash
nano /etc/ssh/sshd_config.d/hardening.conf
```

Добавьте в него строки:

```bash
PasswordAuthentication no
PermitRootLogin no
MaxAuthTries 3
AllowUsers rika
```

`AllowUsers` — явный список пользователей, которым вообще можно заходить по SSH. Пригодится, если на сервере вдруг появится ещё один системный аккаунт с доступом.

Перезапустите SSH:

```bash
sudo systemctl restart ssh
```

Дальше все команды выполняются от пользователя `rika`, с `sudo` там, где он нужен.

## Автоматические обновления безопасности

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

Патчи безопасности ОС будут ставиться сами. Запускать `apt upgrade` руками не придётся.

Docker-контейнеры это не затрагивает: обновляются только пакеты самой ОС.

## Файрвол

```bash
sudo apt update && sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Больше ничего открывать не нужно. Ни Postgres, ни бэкенд не публикуют порты на хост. Наружу смотрит только Caddy.

## Docker

Ставим официальным способом. Пакеты из репозиториев Ubuntu и Debian часто устаревшие.

```bash
# удалить возможные старые версии
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Проверьте, что стоит именно плагин Compose. Его команда — `docker compose`, без дефиса. Так же её называет `justfile`:

```bash
docker compose version
```

Чтобы не писать `sudo` перед каждой командой:

```bash
sudo usermod -aG docker rika
```

Потом нужно перелогиниться.

Учтите: членство в группе `docker` фактически равно root-доступу на хосте. Это стандартный компромисс ради удобства.

Наши образы собраны на базовых образах `postgres:18-alpine` и `caddy:2-alpine`. Изредка стоит подтягивать в них патчи безопасности. `just run` и `just update` этого сами не делают, если слой лежит в кэше:

```bash
docker compose -f compose.prod.yaml build --pull
```

Размер логов контейнеров уже ограничен: в `compose.prod.yaml`, в секции `logging:`, стоит 10 МБ × 3 файла на сервис. Без этого драйвер `json-file` в Docker ничего не ограничивает, и со временем логи могут забить диск.

## `just`

```bash
sudo apt install -y just
```

В репозитории вашего дистрибутива версия слишком старая или `just` нет совсем? Смотрите [официальные способы установки](https://github.com/casey/just#installation).

## DNS

Заведите A-запись домена на IP этого сервера до первого запуска.

Caddy получает сертификат от Let's Encrypt сам, при первом обращении. Но для этого домен уже должен указывать на сервер.

Проверить:

```bash
dig +short ваш-домен.example.com
```

Команда должна вернуть тот же IP, что у сервера.

## Дополнительные проверки (необязательно)

```bash
sudo apt install -y lynis
sudo lynis audit system
```

`lynis` читает конфигурацию сервера и показывает список типовых рекомендаций по безопасности. Достаточно прогнать его один раз после настройки. Держать постоянно запущенным сервисом не нужно.

## Дальше

Сервер готов. Переходите к [продакшн-запуску](production-run.md): клонирование репозитория, `just init prod <домен>`, `just run`, `just superuser`.
