from __future__ import annotations

import json
from pathlib import Path

from backend.database.connection import get_engine
from backend.database.init_db import criar_tabelas
from backend.database.sync import sincronizar_notificacao

BASE = Path(__file__).resolve().parents[2]
USER_ROOT = BASE / "sistema" / "user"
PUBLIC_ROOT = BASE / "sistema" / "dados" / "publico"


def executar() -> int:
    criar_tabelas()
    quantidade = 0
    caminhos = list(USER_ROOT.glob("*/dados/notificacoes/*.json"))
    caminhos += list(PUBLIC_ROOT.glob("notificacoes/*.json"))

    for caminho in sorted(caminhos):
        try:
            with caminho.open("r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(dados, dict) or dados.get("pk") is None:
            continue

        try:
            relativo = caminho.relative_to(USER_ROOT)
            cliente = relativo.parts[0]
        except ValueError:
            cliente = "publico"

        sincronizar_notificacao(cliente, dados)
        quantidade += 1

    return quantidade
