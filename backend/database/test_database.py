from __future__ import annotations

import secrets

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from backend.core.auth import get_user, login, logout, register
from backend.database.connection import get_engine, testar_conexao
from backend.database.init_db import criar_tabelas
from backend.database.migrate_json import executar
from backend.database.models import FeedItem, HistoricoPerfil, Monitoramento, PerfilSalvo, Sessao, Usuario


TABELAS = {
    "usuarios": Usuario,
    "sessoes": Sessao,
    "perfis_salvos": PerfilSalvo,
    "monitoramentos": Monitoramento,
    "historico_perfis": HistoricoPerfil,
    "feed_itens": FeedItem,
}


def _ok(nome: str) -> None:
    print(f"[OK] {nome}")


def executar_validacao() -> None:
    print("=== VALIDAÇÃO AUTOMÁTICA DO POSTGRESQL ===")

    if not testar_conexao():
        raise RuntimeError("Falha na conexão com PostgreSQL.")
    _ok("conexão PostgreSQL")

    criar_tabelas()
    engine = get_engine()
    tabelas = set(inspect(engine).get_table_names())
    faltantes = set(TABELAS) - tabelas
    if faltantes:
        raise RuntimeError(f"Tabelas ausentes: {sorted(faltantes)}")
    _ok("estrutura das tabelas")

    with engine.connect() as connection:
        connection.execute(text("SELECT 1 FROM usuarios LIMIT 1"))
        connection.execute(text("SELECT 1 FROM sessoes LIMIT 1"))
    _ok("consultas básicas")

    with Session(engine) as session:
        for nome, modelo in TABELAS.items():
            quantidade = session.scalar(select(text("count(*)")).select_from(modelo.__table__))
            print(f"[INFO] {nome}: {quantidade}")

        usuarios = {u.username for u in session.scalars(select(Usuario)).all()}
        sessoes = session.scalars(select(Sessao)).all()
        invalidas = [s.username for s in sessoes if s.username not in usuarios]
        if invalidas:
            raise RuntimeError(f"Sessões sem usuário correspondente: {invalidas}")
    _ok("integridade das sessões")

    antes = {}
    with Session(engine) as session:
        for nome, modelo in TABELAS.items():
            antes[nome] = session.scalar(select(text("count(*)")).select_from(modelo.__table__))

    resultado_dry = executar(dry_run=True)
    if not isinstance(resultado_dry, dict):
        raise RuntimeError("A migração em simulação não retornou um resultado válido.")
    _ok("migração em modo simulação")

    with Session(engine) as session:
        depois_dry = {
            nome: session.scalar(select(text("count(*)")).select_from(modelo.__table__))
            for nome, modelo in TABELAS.items()
        }
    if antes != depois_dry:
        raise RuntimeError("A simulação alterou os dados do PostgreSQL.")
    _ok("simulação sem escrita")

    resultado_apply = executar(dry_run=False)
    if not isinstance(resultado_apply, dict):
        raise RuntimeError("A migração não retornou um resultado válido.")
    _ok("migração real")

    with Session(engine) as session:
        depois_apply = {
            nome: session.scalar(select(text("count(*)")).select_from(modelo.__table__))
            for nome, modelo in TABELAS.items()
        }
    if any(depois_apply[nome] < antes[nome] for nome in TABELAS):
        raise RuntimeError("A migração reduziu a quantidade de registros.")
    _ok("migração sem perda aparente")

    # Verifica que uma segunda execução não duplica os registros já migrados.
    executar(dry_run=False)
    with Session(engine) as session:
        depois_idempotencia = {
            nome: session.scalar(select(text("count(*)")).select_from(modelo.__table__))
            for nome, modelo in TABELAS.items()
        }
    if depois_apply != depois_idempotencia:
        raise RuntimeError("A migração não é idempotente.")
    _ok("migração idempotente")

    # Teste isolado do fluxo de autenticação no banco.
    username = "__teste_db_" + secrets.token_hex(6)
    password = "TestePostgreSQL!2026"
    try:
        register(username, password, {"dispositivo": {"timezone": "America/Sao_Paulo"}})
        token, usuario = login(username, password, {})
        if usuario != username or get_user(token) != username:
            raise RuntimeError("Falha no ciclo de autenticação PostgreSQL.")
        logout(token)
        if get_user(token) is not None:
            raise RuntimeError("Logout não invalidou a sessão.")
        _ok("registro, login, sessão e logout")
    finally:
        with Session(engine) as session:
            session.execute(text("DELETE FROM sessoes WHERE username = :username"), {"username": username})
            session.execute(text("DELETE FROM usuarios WHERE username = :username"), {"username": username})
            session.commit()

    print("=== RESULTADO: APROVADO ===")


if __name__ == "__main__":
    executar_validacao()
