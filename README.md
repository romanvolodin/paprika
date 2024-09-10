# paprika

## Деплой

Находимся в `/root`. Рабочая папка соответственно будет `/root/paprika`

```bash
apt install git
# прописать имя и почту юзера для гита. Если не планируется пушить, то можно забить
apt install python3-pip
apt install python3-venv

git clone git@github.com:romanvolodin/paprika.git
# если не проброшен ssh ключ, то
# git clone https://github.com/romanvolodin/paprika.git

cd paprika/
python -m venv venv
. venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

nano .env  # переменные окружения

./backend/manage.py migrate
./backend/manage.py createsuperuser
./backend/manage.py collectstatic

sudo ln -s /root/paprika/deploy/paprika.service /etc/systemd/system/paprika.service
sudo systemctl daemon-reload
sudo systemctl start paprika.service
sudo systemctl status paprika.service
```

Обновление:

```bash
git pull
sudo systemctl restart paprika.service
```

## Бэкап данных

Не сохраняются `auth.permissions` и `contenttypes`, чтобы избежать ошибки `IntegrityError` при дальнейшей загрузке данных. Происходит она потому, что Джанго заново генерит id записей. Эту ошибку должны исправить ключи `--natural-primary` и `--natural-foreing`, но указанные таблицы пока всё равно не сохраняются. Считай это данью традиции.

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
manage.py loaddata dump.json
```
