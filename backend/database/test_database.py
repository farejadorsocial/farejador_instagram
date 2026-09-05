from __future__ import annotations

import secrets

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from backend.core.auth import get_user, login, logout, register
from backend.database.connection import get_engine, testar_conexao
from backend.database.init_db import criar_tabelas
from backend.database.migrate_json import executar
from backend.database.models import FeedItem, HistoricoPerfil, Monitoramento, Notificacao, PerfilSalvo, Sessao, Usuario


TABELAS = {
    "usuarios": Usuario,
    "sessoes": Sessao,
    "perfis_salvos": PerfilSalvo,
    "monitoramentos": Monitoramento,
    "historico_perfis": HistoricoPerfil,
    "feed_itens": FeedItem,
    "notificacoes": Notificacao,
}


def _ok(nome: str) -> None:
    print(f"[OK] {nome}")


def _contagens(session: Session) -> dict[str, int]:
    return {nome: int(session.scalar(select(func.count()).select_from(modelo.__table__)) or 0) for nome, modelo in TABELAS.items()}


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
        for nome in TABELAS:
            connection.execute(text(f'SELECT 1 FROM "{nome}" LIMIT 1'))
    _ok("consultas básicas")

    with Session(engine) as session:
        contagens = _contagens(session)
        for nome, quantidade in contagens.items():
            print(f"[INFO] {nome}: {quantidade}")
        usuarios = {u.username for u in session.scalars(select(Usuario)).all()}
        sessoes = session.scalars(select(Sessao)).all()
        invalidas = [s.username for s in sessoes if s.username not in usuarios]
        if invalidas:
            raise RuntimeError(f"Sessões sem usuário correspondente: {invalidas}")
    _ok("integridade das sessões")

    with Session(engine) as session:
        antes = _contagens(session)

    resultado_dry = executar(dry_run=True)
    if not isinstance(resultado_dry, dict):
        raise RuntimeError("A migração em simulação não retornou um resultado válido.")
    _ok("migração em modo simulação")

    with Session(engine) as session:
        depois_dry = _contagens(session)
    if antes != depois_dry:
        raise RuntimeError(f"A simulação alterou os dados do PostgreSQL: antes={antes}, depois={depois_dry}")
    _ok("simulação sem escrita")

    resultado_apply = executar(dry_run=False)
    if not isinstance(resultado_apply, dict):
        raise RuntimeError("A migração não retornou um resultado válido.")
    _ok("migração real")

    with Session(engine) as session:
        depois_apply = _contagens(session)
    if any(depois_apply[nome] < antes[nome] for nome in TABELAS):
        raise RuntimeError(f"A migração reduziu a quantidade de registros: antes={antes}, depois={depois_apply}")
    _ok("migração sem perda aparente")

    resultado_idempotencia = executar(dry_run=False)
    with Session(engine) as session:
        depois_idempotencia = _contagens(session)
    if depois_apply != depois_idempotencia:
        diferencas = {nome: (depois_apply[nome], depois_idempotencia[nome]) for nome in TABELAS if depois_apply[nome] != depois_idempotencia[nome]}
        raise RuntimeError(f"A migração não é idempotente. Diferenças={diferencas}; segunda_execução={resultado_idempotencia}")
    if any(int(valor or 0) != 0 for valor in resultado_idempotencia.values()):
        raise RuntimeError(f"A segunda migração informou novas inserções: {resultado_idempotencia}")
    _ok("migração idempotente")

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
