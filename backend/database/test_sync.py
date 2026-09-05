from __future__ import annotations

import secrets

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.init_db import criar_tabelas
from backend.database.models import HistoricoPerfil
from backend.database.sync import sincronizar_historico


def executar_validacao() -> None:
    criar_tabelas()
    cliente = "__teste_sync_" + secrets.token_hex(6)
    pk = "__pk_" + secrets.token_hex(6)
    item = {
        "perfil": {"pk": pk, "username": "teste"},
        "hash": "hash-teste-fixo",
        "timestamp_capture": "2026-01-01T12:00:00",
        "conteudo": {"seguidores": 10},
    }

    try:
        sincronizar_historico(cliente, item)
        sincronizar_historico(cliente, item)

        with Session(get_engine()) as session:
            registros = session.scalars(
                select(HistoricoPerfil).where(
                    HistoricoPerfil.cliente_usuario == cliente,
                    HistoricoPerfil.instagram_pk == pk,
                )
            ).all()
            if len(registros) != 1:
                raise RuntimeError(
                    f"sincronizar_historico criou {len(registros)} registros; esperado: 1"
                )

        item_alterado = dict(item)
        item_alterado["conteudo"] = {"seguidores": 11}
        sincronizar_historico(cliente, item_alterado)

        with Session(get_engine()) as session:
            registros = session.scalars(
                select(HistoricoPerfil).where(
                    HistoricoPerfil.cliente_usuario == cliente,
                    HistoricoPerfil.instagram_pk == pk,
                )
            ).all()
            if len(registros) != 1:
                raise RuntimeError(
                    "A sincronização pelo hash não atualizou o registro existente."
                )
            if registros[0].dados.get("conteudo", {}).get("seguidores") != 11:
                raise RuntimeError("O registro existente não foi atualizado corretamente.")

        print("=== RESULTADO SYNC: APROVADO ===")
    finally:
        with Session(get_engine()) as session:
            session.execute(
                delete(HistoricoPerfil).where(
                    HistoricoPerfil.cliente_usuario == cliente,
                    HistoricoPerfil.instagram_pk == pk,
                )
            )
            session.commit()


if __name__ == "__main__":
    executar_validacao()
