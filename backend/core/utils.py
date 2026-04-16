import threading

import requests
from django.conf import settings


def calc_shot_status(statuses):
    if set() == set(statuses):
        return "Нет задач"

    if set(("Отмена",)) == set(statuses):
        return "Отмена"

    if set(("На паузе",)) == set(statuses) or set(("Отмена", "На паузе")) == set(statuses):
        return "На паузе"

    if (
        set(("Не начата",)) == set(statuses)
        or set(("Не начата", "На паузе")) == set(statuses)
        or set(("Отмена", "Не начата", "На паузе")) == set(statuses)
    ):
        return "Не начат"

    if set(("Принята",)) == set(statuses) or set(("Отмена", "Принята", "На паузе")) == set(
        statuses
    ):
        return "Принят"

    if set(("Готова",)) == set(statuses) or set(("Отмена", "Готова", "На паузе")) == set(statuses):
        return "Готов"

    if set(("Отдано",)) == set(statuses) or set(("Отмена", "Отдано", "На паузе")) == set(statuses):
        return "Отдан"

    if "Есть комментарий" in statuses:
        return "Есть комментарий"

    return "В работе"


def send_telegram_notification_async(chat_ids, text, parse_mode="MarkdownV2"):
    if not settings.TELEGRAM_BOT_TOKEN:
        return

    def send():
        for chat_id in chat_ids:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    data={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                    },
                    timeout=10,
                )
            except Exception:
                pass

    thread = threading.Thread(target=send)
    thread.daemon = True
    thread.start()
