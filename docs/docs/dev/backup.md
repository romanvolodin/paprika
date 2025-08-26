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

### Бэкап данных в Git

Сгенерируйте ssh-ключ на сервере:

```bash
ssh-keygen
```

Теперь надо добавить ключ в аккаунт на сайте вашего гит-хостинга, чтобы сервер мог заливать данные в репозиторий.

Для этого выводим в терминале публичную часть ключа:

```bash
cat .ssh/id_rsa.pub
```

Публичную часть ключа надо скопировать и добавьте её в настройки аккаунта на сайте вашего гит-хостинга.

Создайте репозиторий на вашем гит-хостинге. В моём случае репозиторий будет называться `paprika_dumpdata`.

Заходим на сервер Паприки, переходим в папку бэкапов и клонируем репозиторий.

```bash
git clone ssh://git@host/username/paprika_dumpdata.git
```

ssh сообщит, что хост неизвестен и точно ли мы хотим подключится? Отвечаем `yes`.

### Добавляем запуск скрипта в Cron

Открываем файл `crontab` в текстовом редакторе. Если файл не существует, он будет создан. При первом запуске команда спросит какой текстовый редактор использовать:

```bash
crontab -e
```

Добавляем в файл строчку:

```crontab
0 */2 * * * /root/paprika/deploy/backup.sh
```

Это правило будет запускать указанный скрипт каждые 2 часа. Сохраняем и закрываем файл.

Обычно больше ничего делать не нужно, `сron` сам перечитает файл и подхватит изменения. Если нужно чтобы изменения подхватились немедленно, перезапустите сервис `сron`:

```bash
systemctl restart cron
```
