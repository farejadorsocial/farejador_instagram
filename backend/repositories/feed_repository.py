from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import FeedItem
from backend.services.common import limitar


def _feed_postgresql(cliente_usuario):
    with Session(get_engine()) as session:
        registros = session.scalars(
            select(FeedItem)
            .where(FeedItem.cliente_usuario == cliente_usuario)
            .order_by(FeedItem.timestamp_capture.desc(), FeedItem.id.desc())
        ).all()
    return [r.item for r in registros if isinstance(r.item, dict)]


def feed(cliente_usuario):
    """Lê o feed exclusivamente do PostgreSQL."""
    return limitar(cliente_usuario, "feed", _feed_postgresql(cliente_usuario), 10)
