# Alembic migrations environment

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Импортируем настройки и модели
from config.settings import DATABASE_URL
from database.models import Base

# Alembic Config object
config = context.config

# Конвертируем async URL в sync URL для миграций
sync_url = DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
if "postgresql://" in sync_url and "+psycopg2" not in sync_url:
    sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")

config.set_main_option("sqlalchemy.url", sync_url)

# Logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
