# paprika

Команда для бэкапа данных в Джанго.

Не сохраняются `auth.permissions` и `contenttypes`, чтобы избежать ошибки `IntegrityError` при дальнейшей загрузке данных. Происходит она потому, что Джанго заново генерит id записей. Эту ошибку должны исправить ключи `--natural-primary` и `--natural-foreing`, но указанные таблицы пока всё равно не сохраняются. Считай это данью традиции.

Таблицы `sessions.session` и `admin.logentry` игнорируются, ибо не содержат важных данных (это сессии и лог действий в админке).

```bash
manage.py dumpdata --format=json --indent=2 \
  --natural-primary \
  --natural-foreign \
  --exclude sessions.session \
  --exclude auth.permission \
  --exclude admin.logentry \
  --exclude contenttypes \
  --output dump_$(date "+%Y-%m-%d_%H-%M-%S").json
```

Чтобы залить бэкап:

```bash
manage.py loaddata dump.json
```
