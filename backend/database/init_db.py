from backend.database.base import Base
from backend.database.connection import get_engine
from backend.database import models  # noqa: F401


def criar_tabelas() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
