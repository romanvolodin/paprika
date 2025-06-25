# Как узнать свободное место на диске

Здесь и далее `paprika-prod` — это [ssh алиас](ssh-alias.md) для рабочего сервера.

Узнать занятое/свободное место на диске можно командой `df -h`:

```bash
$ ssh paprika-prod "df -h"
Filesystem      Size  Used Avail Use% Mounted on
tmpfs            96M  1.3M   95M   2% /run
/dev/sda1        15G  7.0G  7.7G  48% /
tmpfs           479M     0  479M   0% /dev/shm
tmpfs           5.0M     0  5.0M   0% /run/lock
/dev/sdb1        98G  669M   93G   1% /mnt/NAS
...
```

Можно указать точку монтирования:

```bash
$ ssh paprika-prod "df -h  /"
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        15G  7.0G  7.7G  48% /
```

Или конкретный диск:

```bash
$ ssh paprika-prod "df -h  /dev/sdb1"
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdb1        98G  669M   93G   1% /mnt/NAS
```
