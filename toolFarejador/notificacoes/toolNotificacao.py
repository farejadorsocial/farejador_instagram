from datetime import datetime

from backend.database.connection import get_engine
from backend.database.models import HistoricoPerfil, PerfilSalvo
from backend.database.sync import consultar_notificacoes, sincronizar_feed, sincronizar_notificacao
from sqlalchemy import select
from sqlalchemy.orm import Session


def carregar_perfis_salvos(cliente_usuario):
    """Carrega perfis salvos exclusivamente do PostgreSQL."""
    with Session(get_engine()) as session:
        registros = session.scalars(
            select(PerfilSalvo)
            .where(PerfilSalvo.cliente_usuario == cliente_usuario)
            .order_by(PerfilSalvo.id)
        ).all()
    lista = [
        {"perfil": r.perfil or {}}
        for r in registros
        if isinstance(r.perfil, dict)
    ]
    return {
        "usernames": [x.get("perfil", {}).get("username") for x in lista],
        "dados_perfis": lista,
    }


def consultar_id_pk(valor, cliente_usuario):
    valor = str(valor or "").strip().lstrip("@").lower()
    with Session(get_engine()) as session:
        registro = session.scalar(
            select(PerfilSalvo).where(
                PerfilSalvo.cliente_usuario == cliente_usuario,
                PerfilSalvo.username == valor,
            )
        )
        if registro:
            return {"pk": registro.instagram_pk}

        registros = session.scalars(
            select(PerfilSalvo).where(PerfilSalvo.cliente_usuario == cliente_usuario)
        ).all()
        for item in registros:
            perfil = item.perfil or {}
            if perfil.get("username") == valor or perfil.get("nome") == valor:
                return {"pk": item.instagram_pk}
    return None


def _historico_total(cliente_usuario, pk):
    with Session(get_engine()) as session:
        return len(session.scalars(
            select(HistoricoPerfil).where(
                HistoricoPerfil.cliente_usuario == cliente_usuario,
                HistoricoPerfil.instagram_pk == str(pk),
            )
        ).all())


def notificacao_movimento(lista_usernames, cliente_usuario):
    """Atualiza notificações e feed usando somente dados do PostgreSQL."""
    for username in lista_usernames or []:
        identificacao = consultar_id_pk(username, cliente_usuario)
        if not identificacao:
            continue

        pk = identificacao["pk"]
        total_atual = _historico_total(cliente_usuario, pk)

        existentes = {
            str(item.get("pk")): item
            for item in consultar_notificacoes(cliente_usuario)
        }
        anterior = existentes.get(str(pk))

        if anterior is None:
            notificacao = {
                "pk": pk,
                "username": username,
                "total": total_atual,
                "movimento": None,
                "timestamp_capture": datetime.now().isoformat(),
                "icone": "👤✨",
                "texto": "Novo usuário detectado",
                "mensagem": f"👤✨ Novo usuário detectado: {username}",
            }
        elif total_atual > int(anterior.get("total", 0) or 0):
            notificacao = {
                "pk": pk,
                "username": username,
                "total": total_atual,
                "movimento": True,
                "timestamp_capture": datetime.now().isoformat(),
                "icone": "🚨",
                "texto": "Movimento detectado no perfil do usuário",
                "mensagem": f"🚨 Movimento detectado no perfil do usuário: {username}",
            }
        else:
            notificacao = {
                "pk": pk,
                "username": username,
                "total": total_atual,
                "movimento": False,
                "timestamp_capture": datetime.now().isoformat(),
                "icone": "💤",
                "texto": "Sem movimento no perfil do usuário",
                "mensagem": f"💤 Sem movimento no perfil do usuário: {username}",
            }

        sincronizar_notificacao(cliente_usuario, notificacao)

        # O feed continua sendo derivado das notificações, mas agora a
        # persistência definitiva ocorre no PostgreSQL.
        sincronizar_feed(cliente_usuario, consultar_notificacoes(cliente_usuario))

        if notificacao["movimento"]:
            return notificacao


def carregar_feed(cliente_usuario):
    from backend.database.models import FeedItem
    with Session(get_engine()) as session:
        registros = session.scalars(
            select(FeedItem)
            .where(FeedItem.cliente_usuario == cliente_usuario)
            .order_by(FeedItem.timestamp_capture.desc(), FeedItem.id.desc())
        ).all()
    return [r.item for r in registros if isinstance(r.item, dict)]


if __name__ == "__main__":
    cliente_usuario = "admin"
    lista_usernames = carregar_perfis_salvos(cliente_usuario)["usernames"]
    notificacao_movimento(lista_usernames, cliente_usuario)
    feed = carregar_feed(cliente_usuario)
