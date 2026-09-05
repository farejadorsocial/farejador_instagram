"""Publicação dos dados administrativos no espaço público do PostgreSQL."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import FeedItem, HistoricoPerfil, Monitoramento, Notificacao, PerfilSalvo


def sincronizar_dados_publicos() -> dict:
    """Replica somente os dados públicos do admin para o cliente 'publico'."""
    with Session(get_engine()) as session:
        perfis = session.scalars(select(PerfilSalvo).where(PerfilSalvo.cliente_usuario == "admin")).all()
        monitoramentos = session.scalars(select(Monitoramento).where(Monitoramento.cliente_usuario == "admin")).all()
        historicos = session.scalars(select(HistoricoPerfil).where(HistoricoPerfil.cliente_usuario == "admin")).all()
        notificacoes = session.scalars(select(Notificacao).where(Notificacao.cliente_usuario == "admin")).all()
        feeds = session.scalars(select(FeedItem).where(FeedItem.cliente_usuario == "admin")).all()

        session.execute(delete(PerfilSalvo).where(PerfilSalvo.cliente_usuario == "publico"))
        session.execute(delete(Monitoramento).where(Monitoramento.cliente_usuario == "publico"))
        session.execute(delete(HistoricoPerfil).where(HistoricoPerfil.cliente_usuario == "publico"))
        session.execute(delete(Notificacao).where(Notificacao.cliente_usuario == "publico"))
        session.execute(delete(FeedItem).where(FeedItem.cliente_usuario == "publico"))

        for r in perfis:
            session.add(PerfilSalvo(
                cliente_usuario="publico", instagram_pk=r.instagram_pk, username=r.username,
                perfil=r.perfil, caminho_historico_salvo=r.caminho_historico_salvo,
                criado_em=r.criado_em, atualizado_em=r.atualizado_em,
            ))
        for r in monitoramentos:
            session.add(Monitoramento(
                cliente_usuario="publico", instagram_pk=r.instagram_pk, username=r.username,
                monitorando=r.monitorando, sleep=r.sleep, dados=r.dados, atualizado_em=r.atualizado_em,
            ))
        for r in historicos:
            session.add(HistoricoPerfil(
                cliente_usuario="publico", instagram_pk=r.instagram_pk, timestamp_capture=r.timestamp_capture,
                perfil=r.perfil, dados=r.dados,
            ))
        for r in notificacoes:
            session.add(Notificacao(
                cliente_usuario="publico", instagram_pk=r.instagram_pk, username=r.username,
                total=r.total, movimento=r.movimento, timestamp_capture=r.timestamp_capture,
                icone=r.icone, texto=r.texto, mensagem=r.mensagem, dados=r.dados,
            ))
        for r in feeds:
            session.add(FeedItem(
                cliente_usuario="publico", timestamp_capture=r.timestamp_capture,
                movimento=r.movimento, item=r.item,
            ))

        session.commit()

    return {
        "origem": "admin",
        "destino": "publico",
        "perfis": len(perfis),
        "monitoramentos": len(monitoramentos),
        "historico": len(historicos),
        "notificacoes": len(notificacoes),
        "feed": len(feeds),
    }
