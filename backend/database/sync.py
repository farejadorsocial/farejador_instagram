from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import AtividadeVisitante, FeedItem, HistoricoPerfil, Monitoramento, Notificacao, PerfilSalvo, Visitante

TZ_LOCAL = ZoneInfo("America/Sao_Paulo")


def _datetime(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    if isinstance(valor, datetime):
        resultado = valor
    else:
        try:
            resultado = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if resultado.tzinfo is None:
        resultado = resultado.replace(tzinfo=TZ_LOCAL)
    return resultado


def sincronizar_perfil(cliente_usuario: str, dados: dict) -> None:
    perfil = dados.get("perfil") if isinstance(dados, dict) else None
    if not isinstance(perfil, dict) or perfil.get("pk") is None:
        return
    pk = str(perfil["pk"])
    agora = datetime.now(TZ_LOCAL)
    with Session(get_engine()) as session:
        registro = session.scalar(select(PerfilSalvo).where(PerfilSalvo.cliente_usuario == cliente_usuario, PerfilSalvo.instagram_pk == pk))
        if registro is None:
            session.add(PerfilSalvo(cliente_usuario=cliente_usuario, instagram_pk=pk, username=str(perfil.get("username") or "") or None, perfil=perfil, caminho_historico_salvo=str(dados.get("caminho_historico_salvo") or "") or None, criado_em=agora, atualizado_em=agora))
        else:
            registro.username = str(perfil.get("username") or "") or None
            registro.perfil = perfil
            registro.caminho_historico_salvo = str(dados.get("caminho_historico_salvo") or "") or None
            registro.atualizado_em = agora
        session.commit()


def sincronizar_monitoramento(cliente_usuario: str, dados: dict) -> None:
    if not isinstance(dados, dict) or dados.get("pk") is None:
        return
    pk = str(dados["pk"])
    try:
        sleep = max(1, int(dados.get("sleep", 10) or 10))
    except (TypeError, ValueError):
        sleep = 10
    agora = _datetime(dados.get("atualizado")) or datetime.now(TZ_LOCAL)
    with Session(get_engine()) as session:
        registro = session.scalar(select(Monitoramento).where(Monitoramento.cliente_usuario == cliente_usuario, Monitoramento.instagram_pk == pk))
        if registro is None:
            session.add(Monitoramento(cliente_usuario=cliente_usuario, instagram_pk=pk, username=str(dados.get("username") or "") or None, monitorando=bool(dados.get("monitorando", False)), sleep=sleep, dados=dados, atualizado_em=agora))
        else:
            registro.username = str(dados.get("username") or "") or None
            registro.monitorando = bool(dados.get("monitorando", False))
            registro.sleep = sleep
            registro.dados = dados
            registro.atualizado_em = agora
        session.commit()


def sincronizar_historico(cliente_usuario: str, item: dict) -> None:
    if not isinstance(item, dict):
        return
    perfil = item.get("perfil") if isinstance(item.get("perfil"), dict) else {}
    if perfil.get("pk") is None:
        return
    pk = str(perfil["pk"])
    timestamp = _datetime(item.get("timestamp_capture"))
    hash_item = str(item.get("hash") or "").strip()
    dados_extra = {k: v for k, v in item.items() if k != "perfil"}
    with Session(get_engine()) as session:
        registro = None
        if hash_item:
            registro = session.scalar(select(HistoricoPerfil).where(HistoricoPerfil.cliente_usuario == cliente_usuario, HistoricoPerfil.instagram_pk == pk, HistoricoPerfil.dados["hash"].as_string() == hash_item))
        if registro is None and timestamp is not None:
            registro = session.scalar(select(HistoricoPerfil).where(HistoricoPerfil.cliente_usuario == cliente_usuario, HistoricoPerfil.instagram_pk == pk, HistoricoPerfil.timestamp_capture == timestamp))
        if registro is None:
            session.add(HistoricoPerfil(cliente_usuario=cliente_usuario, instagram_pk=pk, timestamp_capture=timestamp, perfil=perfil, dados=dados_extra))
        else:
            registro.timestamp_capture = timestamp
            registro.perfil = perfil
            registro.dados = dados_extra
        session.commit()


def sincronizar_notificacao(cliente_usuario: str, dados: dict) -> None:
    if not isinstance(dados, dict) or dados.get("pk") is None:
        return
    pk = str(dados["pk"])
    timestamp = _datetime(dados.get("timestamp_capture")) or datetime.now(TZ_LOCAL)
    try:
        total = max(0, int(dados.get("total", 0) or 0))
    except (TypeError, ValueError):
        total = 0
    campos = dict(username=str(dados.get("username") or "") or None, total=total, movimento=dados.get("movimento") if isinstance(dados.get("movimento"), bool) else None, timestamp_capture=timestamp, icone=str(dados.get("icone") or "") or None, texto=str(dados.get("texto") or "") or None, mensagem=str(dados.get("mensagem") or "") or None, dados={k: v for k, v in dados.items() if k not in {"pk", "username", "total", "movimento", "timestamp_capture", "icone", "texto", "mensagem"}})
    with Session(get_engine()) as session:
        registro = session.scalar(select(Notificacao).where(Notificacao.cliente_usuario == cliente_usuario, Notificacao.instagram_pk == pk))
        if registro is None:
            session.add(Notificacao(cliente_usuario=cliente_usuario, instagram_pk=pk, **campos))
        else:
            for chave, valor in campos.items():
                setattr(registro, chave, valor)
        session.commit()


def consultar_notificacoes(cliente_usuario: str) -> list[dict]:
    with Session(get_engine()) as session:
        registros = session.scalars(select(Notificacao).where(Notificacao.cliente_usuario == cliente_usuario).order_by(Notificacao.timestamp_capture.desc(), Notificacao.id.desc())).all()
    return [{"pk": r.instagram_pk, "username": r.username, "total": r.total, "movimento": r.movimento, "timestamp_capture": r.timestamp_capture.isoformat() if r.timestamp_capture else None, "icone": r.icone, "texto": r.texto, "mensagem": r.mensagem, **(r.dados or {})} for r in registros]


def sincronizar_feed(cliente_usuario: str, itens: list[dict]) -> None:
    if not isinstance(itens, list):
        return
    with Session(get_engine()) as session:
        for item in itens:
            if not isinstance(item, dict):
                continue
            timestamp = _datetime(item.get("timestamp_capture"))
            consulta = select(FeedItem).where(FeedItem.cliente_usuario == cliente_usuario, FeedItem.timestamp_capture == timestamp, FeedItem.item == item)
            if session.scalar(consulta) is None:
                session.add(FeedItem(cliente_usuario=cliente_usuario, timestamp_capture=timestamp, movimento=item.get("movimento") if isinstance(item.get("movimento"), bool) else None, item=item))
        session.commit()


def registrar_visitante(visitante_id: str, acesso: dict, timestamp: Any = None) -> str:
    visitante_id = str(visitante_id or "").strip()
    if not visitante_id:
        raise ValueError("visitante_id é obrigatório.")
    acesso = acesso if isinstance(acesso, dict) else {}
    momento = _datetime(timestamp) or datetime.now(TZ_LOCAL)
    with Session(get_engine()) as session:
        visitante = session.scalar(select(Visitante).where(Visitante.visitante_id == visitante_id))
        if visitante is None:
            visitante = Visitante(visitante_id=visitante_id, criado_em=momento, ultimo_acesso=momento, total_acessos=0, acesso=acesso)
            session.add(visitante)
        visitante.ultimo_acesso = momento
        visitante.total_acessos = max(0, int(visitante.total_acessos or 0)) + 1
        visitante.acesso = acesso
        session.add(AtividadeVisitante(visitante_id=visitante_id, tipo="visita", timestamp=momento, acesso=acesso))
        session.commit()
    return visitante_id


def remover_dados_perfil(cliente_usuario: str, pk: Any) -> None:
    pk = str(pk)
    with Session(get_engine()) as session:
        session.execute(delete(PerfilSalvo).where(PerfilSalvo.cliente_usuario == cliente_usuario, PerfilSalvo.instagram_pk == pk))
        session.execute(delete(Monitoramento).where(Monitoramento.cliente_usuario == cliente_usuario, Monitoramento.instagram_pk == pk))
        session.execute(delete(HistoricoPerfil).where(HistoricoPerfil.cliente_usuario == cliente_usuario, HistoricoPerfil.instagram_pk == pk))
        session.execute(delete(Notificacao).where(Notificacao.cliente_usuario == cliente_usuario, Notificacao.instagram_pk == pk))
        session.execute(delete(FeedItem).where(FeedItem.cliente_usuario == cliente_usuario, FeedItem.item["pk"].as_string() == pk))
        session.commit()
