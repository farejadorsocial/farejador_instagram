from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.init_db import criar_tabelas
from backend.database.models import AtividadeVisitante, Visitante
from backend.database.sync import _datetime, registrar_visitante

BASE = Path(__file__).resolve().parents[2]
VISITOR_ROOT = BASE / "sistema" / "user" / "visitante"
VISITOR_USERS = VISITOR_ROOT / "visitantes.json"
VISITOR_ACTIVITIES = VISITOR_ROOT / "atividades.json"


def _ler(caminho: Path, padrao):
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        return padrao


def executar() -> dict[str, int]:
    criar_tabelas()
    visitantes = _ler(VISITOR_USERS, [])
    atividades = _ler(VISITOR_ACTIVITIES, [])
    if not isinstance(visitantes, list):
        visitantes = []
    if not isinstance(atividades, list):
        atividades = []

    ids = {str(item.get("visitante_id")) for item in visitantes if isinstance(item, dict) and item.get("visitante_id")}
    atividades_validas = [item for item in atividades if isinstance(item, dict) and item.get("visitante_id")]

    processadas = 0
    ignoradas = 0
    for item in atividades_validas:
        visitante_id = str(item["visitante_id"])
        timestamp = _datetime(item.get("timestamp"))
        tipo = str(item.get("tipo") or "visita")
        with Session(get_engine()) as session:
            existente = session.scalar(select(AtividadeVisitante.id).where(AtividadeVisitante.visitante_id == visitante_id, AtividadeVisitante.tipo == tipo, AtividadeVisitante.timestamp == timestamp))
        if existente is not None:
            ignoradas += 1
            continue
        registrar_visitante(visitante_id, item.get("acesso") if isinstance(item.get("acesso"), dict) else {}, item.get("timestamp"))
        processadas += 1

    preservados = 0
    for item in visitantes:
        if not isinstance(item, dict) or not item.get("visitante_id"):
            continue
        visitante_id = str(item["visitante_id"])
        with Session(get_engine()) as session:
            existente = session.scalar(select(Visitante.id).where(Visitante.visitante_id == visitante_id))
        if existente is not None:
            continue
        registrar_visitante(visitante_id, item.get("acesso") if isinstance(item.get("acesso"), dict) else {}, item.get("ultimo_acesso") or item.get("criado_em"))
        preservados += 1

    return {"visitantes_origem": len(ids), "atividades_origem": len(atividades_validas), "atividades_processadas": processadas, "atividades_ja_migradas": ignoradas, "visitantes_preservados_sem_atividade": preservados}


if __name__ == "__main__":
    print(executar())
