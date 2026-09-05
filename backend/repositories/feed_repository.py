from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import FeedItem
from backend.services.common import data_root, load_json, limitar


def _feed_postgresql(cliente_usuario):
    with Session(get_engine()) as session:
        registros = session.scalars(
            select(FeedItem)
            .where(FeedItem.cliente_usuario == cliente_usuario)
            .order_by(FeedItem.timestamp_capture.desc(), FeedItem.id.desc())
        ).all()
    return [r.item for r in registros if isinstance(r.item, dict)]


def feed(cliente_usuario):
    try:
        data = _feed_postgresql(cliente_usuario)
        if data:
            return limitar(cliente_usuario, "feed", data, 10)
    except Exception as erro:
        print(f"[postgres] Falha ao consultar feed: {erro}")

    data = load_json(data_root(cliente_usuario) / "feed" / "feed.json", [])
    ordenado = sorted(
        data,
        key=lambda x: x.get("timestamp_capture", ""),
        reverse=True,
    )
    return limitar(cliente_usuario, "feed", ordenado, 10)
