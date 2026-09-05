from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import FeedItem, HistoricoPerfil, Monitoramento, PerfilSalvo


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


def _chave_datetime(valor: Any) -> str:
    resultado = _datetime(valor)
    return resultado.isoformat() if resultado else ""


def sincronizar_perfil(cliente_usuario: str, dados: dict) -> None:
    perfil = dados.get("perfil") if isinstance(dados, dict) else None
    if not isinstance(perfil, dict) or perfil.get("pk") is None:
        return
    pk = str(perfil["pk"])
    agora = datetime.now(TZ_LOCAL)
    with Session(get_engine()) as session:
        registro = session.scalar(select(PerfilSalvo).where(PerfilSalvo.cliente_usuario == cliente_usuario, PerfilSalvo.instagram_pk == pk))
        if registro is None:
            registro = PerfilSalvo(cliente_usuario=cliente_usuario, instagram_pk=pk, username=str(perfil.get("username") or "") or None, perfil=perfil, caminho_historico_salvo=str(dados.get("caminho_historico_salvo") or "") or None, criado_em=agora, atualizado_em=agora)
            session.add(registro)
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
    agora = _datetime(dados.get("atualizado")) or datetime.now(TZ_LOCAL)
    with Session(get_engine()) as session:
        registro = session.scalar(select(Monitoramento).where(Monitoramento.cliente_usuario == cliente_usuario, Monitoramento.instagram_pk == pk))
        valores = dict(cliente_usuario=cliente_usuario, instagram_pk=pk, username=str(dados.get("username") or "") or None, monitorando=bool(dados.get("monitorando", False)), sleep=int(dados.get("sleep", 10) or 10), dados=dados, atualizado_em=agora)
        if registro is None:
            session.add(Monitoramento(**valores))
        else:
            for chave, valor in valores.items():
                if chave not in {"cliente_usuario", "instagram_pk"}:
                    setattr(registro, chave, valor)
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
            registro = session.scalar(select(HistoricoPerfil).where(HistoricoPerfil.cliente_usuario == cliente_usuario, HistoricoPerfil.instagram_pk == pk, HistoricoPerfil.dados["hash"].astext == hash_item))
        if registro is None and timestamp is not None:
            registro = session.scalar(select(HistoricoPerfil).where(HistoricoPerfil.cliente_usuario == cliente_usuario, HistoricoPerfil.instagram_pk == pk, HistoricoPerfil.timestamp_capture == timestamp))
        if registro is None:
            session.add(HistoricoPerfil(cliente_usuario=cliente_usuario, instagram_pk=pk, timestamp_capture=timestamp, perfil=perfil, dados=dados_extra))
        else:
            registro.timestamp_capture = timestamp
            registro.perfil = perfil
            registro.dados = dados_extra
        session.commit()


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


def remover_dados_perfil(cliente_usuario: str, pk: Any) -> None:
    pk = str(pk)
    with Session(get_engine()) as session:
        session.execute(delete(PerfilSalvo).where(PerfilSalvo.cliente_usuario == cliente_usuario, PerfilSalvo.instagram_pk == pk))
        session.execute(delete(Monitoramento).where(Monitoramento.cliente_usuario == cliente_usuario, Monitoramento.instagram_pk == pk))
        session.execute(delete(HistoricoPerfil).where(HistoricoPerfil.cliente_usuario == cliente_usuario, HistoricoPerfil.instagram_pk == pk))
        session.execute(delete(FeedItem).where(FeedItem.cliente_usuario == cliente_usuario, FeedItem.item["pk"].astext == pk))
        session.commit()
