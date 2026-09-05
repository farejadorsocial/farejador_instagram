from __future__ import annotations

import json
from pathlib import Path

from backend.database.init_db import criar_tabelas
from backend.database.sync import registrar_visitante

BASE = Path(__file__).resolve().parents[2]
VISITOR_ROOT = BASE / "sistema" / "user" / "visitante"
VISITOR_USERS = VISITOR_ROOT / "visitantes.json"
VISITOR_ACTIVITIES = VISITOR_ROOT / "atividades.json"


def _ler(caminho: Path, padrao):
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados
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

    ids = {
        str(item.get("visitante_id"))
        for item in visitantes
        if isinstance(item, dict) and item.get("visitante_id")
    }
    atividades_validas = [
        item for item in atividades
        if isinstance(item, dict) and item.get("visitante_id")
    ]

    # Reconstroi o histórico de visitas a partir das atividades, preservando
    # a ordem original. O registro agregado de cada visitante é atualizado
    # pelo próprio sincronizador.
    processadas = 0
    for item in atividades_validas:
        registrar_visitante(
            str(item["visitante_id"]),
            item.get("acesso") if isinstance(item.get("acesso"), dict) else {},
            item.get("timestamp"),
        )
        processadas += 1

    # Visitantes sem atividade histórica também são preservados.
    preservados = 0
    for item in visitantes:
        if not isinstance(item, dict) or not item.get("visitante_id"):
            continue
        visitante_id = str(item["visitante_id"])
        if visitante_id in ids and not any(str(a.get("visitante_id")) == visitante_id for a in atividades_validas):
            registrar_visitante(
                visitante_id,
                item.get("acesso") if isinstance(item.get("acesso"), dict) else {},
                item.get("ultimo_acesso") or item.get("criado_em"),
            )
            preservados += 1

    return {
        "visitantes_origem": len(ids),
        "atividades_origem": len(atividades_validas),
        "atividades_processadas": processadas,
        "visitantes_preservados_sem_atividade": preservados,
    }


if __name__ == "__main__":
    print(executar())
