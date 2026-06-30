# Этот файл создает все таблицы приложения в настроенной базе данных.

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.base import Base  # noqa: E402
from app.database.db import engine  # noqa: E402
from app.database.initializer import initialize_database  # noqa: E402


def init_db() -> None:
    """Создает таблицы и совместимые изменения схемы без Alembic."""
    admin = initialize_database()
    print(f"Таблицы созданы: {', '.join(sorted(Base.metadata.tables))}")
    print(f"Администратор: {admin.username}")
    print(f"Подключение: {engine.url.render_as_string(hide_password=True)}")


if __name__ == "__main__":
    init_db()
