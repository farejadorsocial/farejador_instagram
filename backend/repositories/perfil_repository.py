from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import PerfilSalvo, Monitoramento, HistoricoPerfil
from backend.services.common import PUBLIC_CLIENTE


def _db_profiles(cliente_usuario):
    with Session(get_engine()) as session:
        registros = session.scalars(select(PerfilSalvo).where(PerfilSalvo.cliente_usuario == cliente_usuario).order_by(PerfilSalvo.id)).all()
        monitoring = {
            str(r.instagram_pk): (r.dados or {"pk": r.instagram_pk, "username": r.username, "monitorando": r.monitorando, "sleep": r.sleep})
            for r in session.scalars(select(Monitoramento).where(Monitoramento.cliente_usuario == cliente_usuario)).all()
        }
        return [
            {
                "perfil": r.perfil or {},
                "monitoramento": monitoring.get(str(r.instagram_pk), {"monitorando": False, "sleep": 10}),
                "caminho_historico_salvo": r.caminho_historico_salvo,
            }
            for r in registros
        ]


def get_saved_profiles(cliente_usuario):
    # PostgreSQL é a fonte oficial. Não existe fallback silencioso para JSON.
    return _db_profiles(cliente_usuario)


def get_profile_by_pk(cliente_usuario, pk):
    with Session(get_engine()) as session:
        registro = session.scalar(select(PerfilSalvo).where(PerfilSalvo.cliente_usuario == cliente_usuario, PerfilSalvo.instagram_pk == str(pk)))
        if not registro:
            return {}
        return {"perfil": registro.perfil or {}, "caminho_historico_salvo": registro.caminho_historico_salvo}


def get_history(cliente_usuario, pk):
    with Session(get_engine()) as session:
        registros = session.scalars(
            select(HistoricoPerfil)
            .where(HistoricoPerfil.cliente_usuario == cliente_usuario, HistoricoPerfil.instagram_pk == str(pk))
            .order_by(HistoricoPerfil.timestamp_capture, HistoricoPerfil.id)
        ).all()
    return [
        {
            "perfil": r.perfil or {},
            **(r.dados or {}),
            "timestamp_capture": r.timestamp_capture.isoformat() if r.timestamp_capture else None,
        }
        for r in registros
    ]
