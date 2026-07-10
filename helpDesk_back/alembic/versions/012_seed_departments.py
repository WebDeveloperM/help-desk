"""seed_departments

Seeds organizational units for «Бухоро нефтни қайта ишлаш заводи» МЧЖ.
Source: цех_ва_булим_номлари.xlsx (structure as of 17.04.2026).

Loads 55 units — 20 departments (#18–37) and 35 workshops (#38–72) from the
source list. The 17 management positions (#1–17) are intentionally excluded:
a person's position is stored on the user profile (User.position), not as a
department row.

`code` carries the unit type as a prefix — DEPT-NN for departments, WS-NN for
workshops, where NN is the row number from the source spreadsheet. `number`
is left to the table's IDENTITY sequence. Idempotent: re-running upgrade skips
codes that already exist.

Revision ID: 012
Revises: 011
Create Date: 2026-05-17

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (code, name) — Uzbek names from the source list. id via gen_random_uuid().

# Бўлим ва хизматлар — departments & services (#18–37).
DEPARTMENTS = [
    ("DEPT-18", "Юридик хизмат"),
    ("DEPT-19", "Техник бўлим"),
    ("DEPT-20", "Иқтисод, режалаштириш ва нарх шакллантириш бўлими"),
    ("DEPT-21", "HR хизмати"),
    ("DEPT-22", "Бош механик бўлими"),
    ("DEPT-23", "Бош метролог бўлими"),
    ("DEPT-24", "Бош энергетик бўлими"),
    ("DEPT-25", "Махсус ишлар бўлими"),
    ("DEPT-26", "Мобилизация ишлари ва фуқаро ҳимояси бўлими"),
    ("DEPT-27", "Киберхавфсизлик бўлими"),
    ("DEPT-28", "Молия ва активлар бўлими"),
    ("DEPT-29", "Ҳисобхона"),
    ("DEPT-30", "Молиявий ҳисобот юритишнинг халқаро стандартларини жорий қилиш бўлими"),
    ("DEPT-31", "Лойиҳа-конструкторлик бюроси"),
    ("DEPT-32", "Харидлар хизмати"),
    ("DEPT-33", "Операцион самарадорлик хизмати"),
    ("DEPT-34", "Инновацион лойиҳалар ва технологияларни ишлаб чиқаришга тадбиқ этиш бўлими"),
    ("DEPT-35", "Жамоатчилик билан алоқалар, гендер тенглик ва ижтимоий сиёсат хизмати"),
    ("DEPT-36", "Ғазначилик бўлими"),
    ("DEPT-37", "Бухоро НҚИЗни модернизация қилиш лойиҳаси офиси"),
]

# Цехлар — workshops (#38–72).
WORKSHOPS = [
    ("WS-38", "Асосий ишлаб чиқариш цехи"),
    ("WS-39", "Хом-ашё ва тайёр маҳсулотлар цехи"),
    ("WS-40", "Буғҳавогазтаъминоти цехи"),
    ("WS-41", "Сув таъминоти ва оқава цехи"),
    ("WS-42", "Таъмир-механика цехи"),
    ("WS-43", "Электр таъминоти цехи"),
    ("WS-44", "Ўлчов-назорат асбоблари ва автоматика цехи"),
    ("WS-45", "Автонақлиёт цехи"),
    ("WS-46", "Темир йўл цехи"),
    ("WS-47", "Импорт хом ашёси ва нефт маҳсулотлари тижорат савдоси хизмати"),
    ("WS-48", "Завод марказий таҳлилхонаси"),
    ("WS-49", "Ҳарбийлаштирилган газдан қутқариш отряди"),
    ("WS-50", "Экология ва атроф-муҳитни муҳофазалаш бўлими"),
    ("WS-51", "Қўриқлаш хизмати"),
    ("WS-52", "Тадқиқотлар таҳлилхонаси"),
    ("WS-53", "Ижтимоий объектлар, уй-жойдан фойдаланиш ва коммунал хўжаликси цехи"),
    ("WS-54", "Маҳсулот жўнатиш бўлими"),
    ("WS-55", "Капитал қурилиш бўлими"),
    ("WS-56", "Жўнатилган нефт маҳсулотлари ҳисобини юритиш хизмати"),
    ("WS-57", "Ускуналар базаси"),
    ("WS-58", "Хўжаликни бошқариш цехи"),
    ("WS-59", "Бино ва иншоотларни ишлатиш ва таъмирлаш бўлими"),
    ("WS-60", "Тиббий-санитария қисми"),
    ("WS-61", "Қурилиш-монтаж цехи"),
    ("WS-62", "Рақамли технологиялар хизмати"),
    ("WS-63", "Зафаробод нефт қуйиш ва тўкиб олиш эстакадаси"),
    ("WS-64", "Сифатни бошқариш тизими бўлими"),
    ("WS-65", "Коммунал хизматлар ва тўловлар ҳисобини юритиш хизмати"),
    ("WS-66", "Саноат хавфсизлиги, меҳнат муҳофазаси ва хавфсизлик техникаси хизмати"),
    ("WS-67", "Қоровулбозор нефт қуйиш ва тўкиб олиш эстакадаси"),
    ("WS-68", "Ускуналар ишончлилигини бошқариш ва таъмирлашни режалаштириш хизмати"),
    ("WS-69", "Маъмурий ишлар ва хўжаликни бошқариш хизмати"),
    ("WS-70", "Жондор туманидаги спорт-соғломлаштириш мажмуаси"),
    ("WS-71", "Қозонхона"),
    ("WS-72", "Ишлаб чиқариш жараёнларини мувофиқлаштириш хизмати"),
]

SEED_UNITS = DEPARTMENTS + WORKSHOPS


def upgrade() -> None:
    conn = op.get_bind()
    for code, name in SEED_UNITS:
        # Distinct bind names for the two `code` uses so asyncpg does not
        # deduce inconsistent parameter types (see migration 007).
        conn.execute(
            text("""
                INSERT INTO departments (id, code, name, is_active)
                SELECT gen_random_uuid(), :code_val, :name, true
                WHERE NOT EXISTS (
                    SELECT 1 FROM departments WHERE code = :code_check
                )
            """),
            {"code_val": code, "name": name, "code_check": code},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for code, _name in SEED_UNITS:
        conn.execute(
            text("DELETE FROM departments WHERE code = :code"),
            {"code": code},
        )
