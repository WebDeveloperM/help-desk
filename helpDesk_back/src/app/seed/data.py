"""Declarative demo fixtures for local/dev seeding.

Pure data — no DB access. The seeder resolves ``department_code`` and
``category_code`` to real rows (seeded by migrations 007/012) at run time.
All demo accounts share one documented password so the environment is easy to
demo; never enable demo seeding in production (see ``SEED_DEMO_DATA``).
"""

from app.core.enums import Role, TicketPriority, TicketStatus

# Shared password for every demo (non-admin) account.
DEMO_PASSWORD = "Password123!"

# Demo users. ``department_code`` maps to a Department seeded by migration 012.
DEMO_USERS: list[dict] = [
    {
        "username": "d.rashidov",
        "full_name": "Диёр Рашидов",
        "email": "d.rashidov@example.com",
        "role": Role.DEPARTMENT_HEAD,
        "department_code": "WS-62",  # Рақамли технологиялар хизмати
        "position": "Начальник службы цифровых технологий",
        "phone": "+998 90 111 22 33",
    },
    {
        "username": "s.azizov",
        "full_name": "Санжар Азизов",
        "email": "s.azizov@example.com",
        "role": Role.EXECUTOR,
        "department_code": "WS-62",
        "position": "Инженер-программист",
        "phone": "+998 90 222 33 44",
    },
    {
        "username": "m.karimova",
        "full_name": "Мадина Каримова",
        "email": "m.karimova@example.com",
        "role": Role.EXECUTOR,
        "department_code": "WS-44",  # Ўлчов-назорат асбоблари ва автоматика цехи
        "position": "Инженер КИПиА",
        "phone": "+998 90 333 44 55",
    },
    {
        "username": "n.yusupova",
        "full_name": "Нигора Юсупова",
        "email": "n.yusupova@example.com",
        "role": Role.DEPARTMENT_HEAD,
        "department_code": "DEPT-21",  # HR хизмати
        "position": "Начальник службы HR",
        "phone": "+998 90 444 55 66",
    },
    {
        "username": "f.toshev",
        "full_name": "Фаррух Тошев",
        "email": "f.toshev@example.com",
        "role": Role.USER,
        "department_code": "DEPT-29",  # Ҳисобхона
        "position": "Бухгалтер",
        "phone": "+998 90 555 66 77",
    },
    {
        "username": "a.qodirov",
        "full_name": "Азиз Қодиров",
        "email": "a.qodirov@example.com",
        "role": Role.USER,
        "department_code": "DEPT-27",  # Киберхавфсизлик бўлими
        "position": "Специалист по кибербезопасности",
        "phone": "+998 90 666 77 88",
    },
]

# department_code -> username to appoint as that department's head.
DEPARTMENT_HEADS: dict[str, str] = {
    "WS-62": "d.rashidov",
    "DEPT-21": "n.yusupova",
}

# Demo tickets. ``seed_key`` is stored in ticket_metadata and used for
# idempotency. ``category_code`` maps to a category seeded by migration 007.
DEMO_TICKETS: list[dict] = [
    {
        "seed_key": "seed-001",
        "title": "Не работает принтер в бухгалтерии",
        "description": "Сетевой принтер HP на 2 этаже не печатает, горит красный индикатор.",
        "category_code": "it",
        "creator_username": "f.toshev",
        "executor_usernames": ["s.azizov"],
        "priority": TicketPriority.NORMAL,
        "status": TicketStatus.ASSIGNED,
        "is_urgent": False,
        "progress_percent": 0,
    },
    {
        "seed_key": "seed-002",
        "title": "Настроить доступ к 1С для нового сотрудника",
        "description": "Принят новый бухгалтер, нужна учётная запись и права в 1С.",
        "category_code": "it",
        "creator_username": "n.yusupova",
        "executor_usernames": ["s.azizov"],
        "priority": TicketPriority.HIGH,
        "status": TicketStatus.IN_PROGRESS,
        "is_urgent": False,
        "progress_percent": 40,
    },
    {
        "seed_key": "seed-003",
        "title": "Поверка датчика давления на установке",
        "description": "Плановая поверка КИП: датчик давления, линия №3.",
        "category_code": "general",
        "creator_username": "a.qodirov",
        "executor_usernames": ["m.karimova"],
        "priority": TicketPriority.LOW,
        "status": TicketStatus.COMPLETED,
        "is_urgent": False,
        "progress_percent": 100,
    },
    {
        "seed_key": "seed-004",
        "title": "Подозрительная сетевая активность",
        "description": "Зафиксированы аномальные подключения к внутреннему сегменту сети.",
        "category_code": "it",
        "creator_username": "a.qodirov",
        "executor_usernames": ["s.azizov", "d.rashidov"],
        "priority": TicketPriority.URGENT,
        "status": TicketStatus.ASSIGNED,
        "is_urgent": True,
        "progress_percent": 10,
    },
    {
        "seed_key": "seed-005",
        "title": "Обновление ОС на рабочих станциях цеха",
        "description": "Запланировать обновление операционных систем на 15 рабочих станциях.",
        "category_code": "it",
        "creator_username": "d.rashidov",
        "executor_usernames": ["s.azizov"],
        "priority": TicketPriority.NORMAL,
        "status": TicketStatus.DRAFT,
        "is_urgent": False,
        "progress_percent": 0,
    },
    {
        "seed_key": "seed-006",
        "title": "Ошибка при формировании квартального отчёта",
        "description": "При выгрузке отчёта в 1С возникает ошибка, требуется уточнение по данным.",
        "category_code": "accounting",
        "creator_username": "f.toshev",
        "executor_usernames": ["s.azizov"],
        "priority": TicketPriority.HIGH,
        "status": TicketStatus.WAITING_INFO,
        "is_urgent": False,
        "progress_percent": 25,
    },
]
