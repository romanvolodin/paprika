"""The fixed list of permissions and the starter roles built from it.

A permission only means something if the code checks it, so the list lives
here and isn't editable from the interface. What a role is made of is
editable: `Role.permissions` holds a subset of these codes.
"""

from dataclasses import dataclass


COMPANY = "company"
PROJECT = "project"


@dataclass(frozen=True)
class Permission:
    code: str
    label: str
    description: str
    group: str
    level: str


class P:
    """Permission codes, for use in the checks."""

    COMPANY_EDIT = "company.edit"
    COMPANY_DELETE = "company.delete"
    COMPANY_MEMBERS = "company.members"
    COMPANY_ROLES = "company.roles"
    COMPANY_PIPELINE = "company.pipeline"
    PROJECT_CREATE = "project.create"

    PROJECT_EDIT = "project.edit"
    PROJECT_DELETE = "project.delete"
    PROJECT_MEMBERS = "project.members"
    FEED_VIEW = "feed.view"

    SHOT_CREATE = "shot.create"
    SHOT_EDIT = "shot.edit"
    SHOT_DELETE = "shot.delete"
    SHOT_IMPORT = "shot.import"
    GROUP_MANAGE = "group.manage"

    TASK_CREATE = "task.create"
    TASK_EDIT = "task.edit"
    TASK_DELETE = "task.delete"
    TASK_UPDATE_OWN = "task.update_own"

    VERSION_UPLOAD = "version.upload"
    VERSION_DELETE = "version.delete"
    VERSION_DELETE_OWN = "version.delete_own"

    CHAT_WRITE = "chat.write"
    CHAT_EDIT_ANY = "chat.edit_any"


PERMISSIONS: tuple[Permission, ...] = (
    Permission(
        P.COMPANY_EDIT,
        "Настройки компании",
        "Менять название и данные компании",
        "Компания",
        COMPANY,
    ),
    Permission(
        P.COMPANY_DELETE,
        "Удаление компании",
        "Удалить компанию целиком",
        "Компания",
        COMPANY,
    ),
    Permission(
        P.COMPANY_MEMBERS,
        "Участники компании",
        "Приглашать людей, создавать аккаунты, менять роли, убирать из компании",
        "Компания",
        COMPANY,
    ),
    Permission(
        P.COMPANY_ROLES,
        "Роли",
        "Создавать и настраивать роли",
        "Компания",
        COMPANY,
    ),
    Permission(
        P.COMPANY_PIPELINE,
        "Статусы и типы задач",
        "Настраивать статусы кадров, статусы задач и типы задач",
        "Компания",
        COMPANY,
    ),
    Permission(
        P.PROJECT_CREATE,
        "Создание проектов",
        "Заводить новые проекты в компании",
        "Компания",
        COMPANY,
    ),
    Permission(
        P.PROJECT_EDIT,
        "Настройки проекта",
        "Менять название, обложку и параметры проекта",
        "Проект",
        PROJECT,
    ),
    Permission(
        P.PROJECT_DELETE,
        "Удаление проекта",
        "Удалить проект целиком",
        "Проект",
        PROJECT,
    ),
    Permission(
        P.PROJECT_MEMBERS,
        "Участники проекта",
        "Добавлять людей в проект, менять их роли, убирать из проекта",
        "Проект",
        PROJECT,
    ),
    Permission(
        P.FEED_VIEW,
        "Лента событий",
        "Видеть ленту событий проекта",
        "Проект",
        PROJECT,
    ),
    Permission(P.SHOT_CREATE, "Создание кадров", "Добавлять кадры", "Кадры", PROJECT),
    Permission(
        P.SHOT_EDIT,
        "Редактирование кадров",
        "Менять данные кадров",
        "Кадры",
        PROJECT,
    ),
    Permission(P.SHOT_DELETE, "Удаление кадров", "Удалять кадры", "Кадры", PROJECT),
    Permission(
        P.SHOT_IMPORT,
        "Импорт кадров",
        "Загружать кадры из таблицы",
        "Кадры",
        PROJECT,
    ),
    Permission(
        P.GROUP_MANAGE,
        "Группы кадров",
        "Создавать, переименовывать и удалять группы",
        "Кадры",
        PROJECT,
    ),
    Permission(
        P.TASK_CREATE,
        "Создание задач",
        "Создавать задачи и ставить их на кадры",
        "Задачи",
        PROJECT,
    ),
    Permission(
        P.TASK_EDIT,
        "Редактирование задач",
        "Менять любые задачи и назначать исполнителей",
        "Задачи",
        PROJECT,
    ),
    Permission(P.TASK_DELETE, "Удаление задач", "Удалять задачи", "Задачи", PROJECT),
    Permission(
        P.TASK_UPDATE_OWN,
        "Смена статуса своих задач",
        "Менять статус только тех задач, где вы исполнитель",
        "Задачи",
        PROJECT,
    ),
    Permission(
        P.VERSION_UPLOAD,
        "Загрузка версий",
        "Загружать новые версии",
        "Версии и чат",
        PROJECT,
    ),
    Permission(
        P.VERSION_DELETE,
        "Удаление версий",
        "Удалять версии",
        "Версии и чат",
        PROJECT,
    ),
    Permission(
        P.VERSION_DELETE_OWN,
        "Удаление своих версий",
        "Удалять только те версии, которые загрузили вы",
        "Версии и чат",
        PROJECT,
    ),
    Permission(
        P.CHAT_WRITE,
        "Чат",
        "Писать сообщения, ставить реакции, прикладывать файлы",
        "Версии и чат",
        PROJECT,
    ),
    Permission(
        P.CHAT_EDIT_ANY,
        "Модерация чата",
        "Править и удалять чужие сообщения",
        "Версии и чат",
        PROJECT,
    ),
)

ALL_CODES: frozenset[str] = frozenset(p.code for p in PERMISSIONS)
COMPANY_CODES: frozenset[str] = frozenset(
    p.code for p in PERMISSIONS if p.level == COMPANY
)
PROJECT_CODES: frozenset[str] = ALL_CODES - COMPANY_CODES


@dataclass(frozen=True)
class RoleTemplate:
    name: str
    color: str
    permissions: frozenset[str]
    sees_all_projects: bool = False


_PROJECT_WORK = frozenset(
    {
        P.PROJECT_EDIT,
        P.PROJECT_MEMBERS,
        P.FEED_VIEW,
        P.SHOT_CREATE,
        P.SHOT_EDIT,
        P.SHOT_DELETE,
        P.SHOT_IMPORT,
        P.GROUP_MANAGE,
        P.TASK_CREATE,
        P.TASK_EDIT,
        P.TASK_DELETE,
        P.TASK_UPDATE_OWN,
        P.VERSION_UPLOAD,
        P.VERSION_DELETE,
        P.VERSION_DELETE_OWN,
        P.CHAT_WRITE,
        P.CHAT_EDIT_ANY,
    }
)

_PRODUCER = (
    _PROJECT_WORK
    | {P.PROJECT_DELETE}
    | {
        P.COMPANY_EDIT,
        P.COMPANY_MEMBERS,
        P.COMPANY_PIPELINE,
        P.PROJECT_CREATE,
    }
)

# Keys are used by the code that needs a particular starter role (tests,
# the migration of the old fixed roles); they are not stored.
DEFAULT_ROLES: dict[str, RoleTemplate] = {
    "admin": RoleTemplate("Админ", "#00A64F", ALL_CODES, sees_all_projects=True),
    "producer": RoleTemplate(
        "Продюсер", "#E8A90C", frozenset(_PRODUCER), sees_all_projects=True
    ),
    "coordinator": RoleTemplate(
        "Координатор", "#0A84DB", frozenset(_PROJECT_WORK - {P.PROJECT_DELETE})
    ),
    "executor": RoleTemplate(
        "Исполнитель",
        "#E971B8",
        frozenset(
            {
                P.FEED_VIEW,
                P.TASK_UPDATE_OWN,
                P.VERSION_UPLOAD,
                P.VERSION_DELETE_OWN,
                P.CHAT_WRITE,
            }
        ),
    ),
    "freelancer": RoleTemplate(
        "Фрилансер",
        "#12B5CB",
        frozenset(
            {P.TASK_UPDATE_OWN, P.VERSION_UPLOAD, P.VERSION_DELETE_OWN, P.CHAT_WRITE}
        ),
    ),
    "client": RoleTemplate("Клиент", "#8A8A8A", frozenset({P.CHAT_WRITE})),
}
