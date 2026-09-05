from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from backend.database.connection import get_engine, testar_conexao
from backend.database.init_db import criar_tabelas
from backend.database.models import AtividadeVisitante, FeedItem, HistoricoPerfil, Monitoramento, Notificacao, PerfilSalvo, Sessao, Usuario, Visitante

EXPECTED_TABLES = {
    "usuarios",
    "sessoes",
    "perfis_salvos",
    "monitoramentos",
    "historico_perfis",
    "feed_itens",
    "notificacoes",
    "visitantes",
    "atividades_visitante",
}

EXPECTED_COUNTS = {
    "usuarios": 6,
    "sessoes": 28,
    "perfis_salvos": 25,
    "monitoramentos": 25,
    "historico_perfis": 505,
    "feed_itens": 13,
}


def _count(session: Session, model) -> int:
    return len(session.execute(select(model.id)).all())


def _check_json_integrity() -> tuple[int, int]:
    root = Path(__file__).resolve().parents[2] / "sistema"
    total = 0
    invalid = 0
    for path in root.rglob("*.json"):
        if path.name == "sessoes.json":
            continue
        total += 1
        try:
            with path.open("r", encoding="utf-8") as arquivo:
                json.load(arquivo)
        except Exception:
            invalid += 1
    return total, invalid


def verificar(expect_migrated: bool = False) -> int:
    resultados: list[tuple[str, bool, str]] = []
    try:
        testar_conexao()
        resultados.append(("Conexão PostgreSQL", True, "OK"))
    except Exception as erro:
        resultados.append(("Conexão PostgreSQL", False, str(erro)))
        _print(resultados)
        return 1

    try:
        criar_tabelas()
        tabelas = set(inspect(get_engine()).get_table_names())
        faltantes = EXPECTED_TABLES - tabelas
        resultados.append(("Tabelas", not faltantes, "OK" if not faltantes else f"faltantes: {sorted(faltantes)}"))
    except Exception as erro:
        resultados.append(("Tabelas", False, str(erro)))
        _print(resultados)
        return 1

    modelos = {
        "usuarios": Usuario,
        "sessoes": Sessao,
        "perfis_salvos": PerfilSalvo,
        "monitoramentos": Monitoramento,
        "historico_perfis": HistoricoPerfil,
        "feed_itens": FeedItem,
        "notificacoes": Notificacao,
        "visitantes": Visitante,
        "atividades_visitante": AtividadeVisitante,
    }
    try:
        with Session(get_engine()) as session:
            for nome, modelo in modelos.items():
                quantidade = _count(session, modelo)
                if expect_migrated and nome in EXPECTED_COUNTS:
                    esperado = EXPECTED_COUNTS[nome]
                    ok = quantidade == esperado
                    detalhe = f"{quantidade}/{esperado}" if not ok else str(quantidade)
                else:
                    ok = quantidade >= 0
                    detalhe = str(quantidade)
                resultados.append((nome, ok, detalhe))
    except Exception as erro:
        resultados.append(("Contagem dos dados", False, str(erro)))

    try:
        with Session(get_engine()) as session:
            duplicados = session.execute(text("SELECT username, COUNT(*) FROM usuarios GROUP BY username HAVING COUNT(*) > 1")).all()
            resultados.append(("Integridade usuários", not duplicados, "OK" if not duplicados else str(duplicados)))
    except Exception as erro:
        resultados.append(("Integridade usuários", False, str(erro)))

    total_json, invalid_json = _check_json_integrity()
    resultados.append(("JSON legado", invalid_json == 0, f"{total_json} arquivos válidos" if invalid_json == 0 else f"{invalid_json} inválidos de {total_json}"))
    _print(resultados)
    return 0 if all(ok for _, ok, _ in resultados) else 1


def _print(resultados: list[tuple[str, bool, str]]) -> None:
    print("=" * 42)
    print("VALIDAÇÃO DO BANCO")
    print("=" * 42)
    for nome, ok, detalhe in resultados:
        print(f"{'OK' if ok else 'ERRO':5} {nome}: {detalhe}")
    print("=" * 42)
    print("RESULTADO:", "APROVADO" if all(ok for _, ok, _ in resultados) else "FALHOU")
    print("=" * 42)


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida a camada PostgreSQL do Farejador.")
    parser.add_argument("--expect-migrated", action="store_true", help="Exige as quantidades esperadas após a migração legada.")
    args = parser.parse_args()
    sys.exit(verificar(expect_migrated=args.expect_migrated))


if __name__ == "__main__":
    main()
