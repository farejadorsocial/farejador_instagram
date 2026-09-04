import os
from typing import Optional

from sqlalchemy import Engine, create_engine, text


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def _normalizar_database_url(url: str) -> str:
    url = str(url or "").strip()

    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]

    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]

    return url


_engine: Optional[Engine] = None


def get_engine() -> Engine:
    global _engine

    if _engine is not None:
        return _engine

    url = _normalizar_database_url(DATABASE_URL)

    if not url:
        raise RuntimeError(
            "DATABASE_URL não configurada. "
            "Defina a conexão do PostgreSQL no arquivo .env."
        )

    _engine = create_engine(
        url,
        pool_pre_ping=True,
        future=True,
    )

    return _engine


def testar_conexao() -> bool:
    engine = get_engine()

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return True
