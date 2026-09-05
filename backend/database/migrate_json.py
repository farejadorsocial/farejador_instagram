from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.init_db import criar_tabelas
from backend.database.models import FeedItem, HistoricoPerfil, Monitoramento, PerfilSalvo, Sessao, Usuario


BASE = Path(__file__).resolve().parents[2]
USER_ROOT = BASE / "sistema" / "user"
PUBLIC_ROOT = BASE / "sistema" / "dados" / "publico"
TZ_LOCAL = ZoneInfo("America/Sao_Paulo")


def carregar_json(caminho: Path, padrao: Any) -> Any:
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (OSError, json.JSONDecodeError):
        return padrao


def normalizar_datetime(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    try:
        resultado = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        if resultado.tzinfo is None:
            resultado = resultado.replace(tzinfo=TZ_LOCAL)
        return resultado
    except (TypeError, ValueError):
        return None


def chave_datetime(valor: Any) -> str:
    resultado = normalizar_datetime(valor)
    return resultado.isoformat() if resultado else ""


def iterar_json(diretorio: Path, nome: str) -> Iterable[Path]:
    if not diretorio.exists():
        return []
    return diretorio.rglob(nome)


def extrair_cliente(caminho: Path) -> Optional[str]:
    try:
        relativo = caminho.relative_to(USER_ROOT)
        partes = relativo.parts
        if partes:
            return partes[0]
    except ValueError:
        pass
    try:
        caminho.relative_to(PUBLIC_ROOT)
        return "publico"
    except ValueError:
        return None


def ler_lista(caminho: Path) -> list[dict]:
    dados = carregar_json(caminho, [])
    if isinstance(dados, list):
        return [item for item in dados if isinstance(item, dict)]
    if isinstance(dados, dict):
        return [dados]
    return []


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def usuarios_legados_disponiveis() -> set[str]:
    return {
        caminho.parent.name
        for caminho in USER_ROOT.glob("*/usuario.json")
        if caminho.is_file()
    }


def migrar_usuarios(session: Session, dry_run: bool) -> int:
    inseridos = 0
    for caminho in sorted(USER_ROOT.glob("*/usuario.json")):
        username = caminho.parent.name
        dados = carregar_json(caminho, {})
        if not isinstance(dados, dict):
            continue
        usuario = dados.get("usuario") or {}
        conta = dados.get("conta") or {}
        seguranca = dados.get("seguranca") or {}
        configuracoes = dados.get("configuracoes") or {}
        password_hash = str(seguranca.get("password_hash") or "").strip()
        salt = str(seguranca.get("salt") or "").strip()
        if not password_hash or not salt:
            print(f"[usuarios] ignorado sem credenciais válidas: {username}")
            continue
        existente = session.scalar(select(Usuario).where(Usuario.username == username))
        if existente:
            continue
        if not dry_run:
            session.add(Usuario(username=str(usuario.get("username") or username).strip().lower(), password_hash=password_hash, salt=salt, criado_em=normalizar_datetime(conta.get("criado_em")), ultimo_login=normalizar_datetime(conta.get("ultimo_login")), ativo=bool(conta.get("ativo", True)), configuracoes=configuracoes if isinstance(configuracoes, dict) else {}))
        inseridos += 1
    return inseridos


def migrar_sessoes(session: Session, dry_run: bool) -> int:
    inseridos = 0
    usuarios_legados = usuarios_legados_disponiveis() if dry_run else set()
    for caminho in sorted(iterar_json(USER_ROOT, "sessoes.json")):
        cliente = extrair_cliente(caminho)
        if not cliente or cliente in {"publico", "visitante"}:
            continue
        for dados in ler_lista(caminho):
            session_id = str(dados.get("session_id") or "").strip()
            token = str(dados.get("token") or "").strip()
            if not session_id or not token:
                continue
            usuario_existe = cliente in usuarios_legados if dry_run else session.scalar(select(Usuario).where(Usuario.username == cliente)) is not None
            if not usuario_existe:
                print(f"[sessoes] usuário não encontrado, ignorando: {cliente}")
                continue
            existente = session.scalar(select(Sessao).where(Sessao.session_id == session_id))
            if existente:
                continue
            if not dry_run:
                status = dados.get("status") or {}
                session.add(Sessao(session_id=session_id, token_hash=hash_token(token), username=cliente, criada_em=normalizar_datetime(dados.get("criada_em") or status.get("criada_em")), ultimo_acesso=normalizar_datetime(dados.get("ultimo_acesso") or status.get("ultimo_acesso")), expira_em=normalizar_datetime(dados.get("expira_em") or status.get("expira_em")), ativa=bool(status.get("ativa", True)), acesso=dados.get("acesso") if isinstance(dados.get("acesso"), dict) else {}, permissoes=dados.get("permissoes") if isinstance(dados.get("permissoes"), dict) else {}))
            inseridos += 1
    return inseridos


def migrar_perfis_salvos(session: Session, dry_run: bool) -> int:
    inseridos = 0
    caminhos = list(iterar_json(USER_ROOT, "perfil_salvos/*.json"))
    caminhos += list(iterar_json(PUBLIC_ROOT, "perfil_salvos/*.json"))
    for caminho in sorted(caminhos):
        cliente = extrair_cliente(caminho)
        if not cliente:
            continue
        dados = carregar_json(caminho, {})
        if not isinstance(dados, dict):
            continue
        perfil = dados.get("perfil")
        if not isinstance(perfil, dict):
            continue
        instagram_pk = str(perfil.get("pk") or caminho.stem).strip()
        if not instagram_pk:
            continue
        existente = session.scalar(select(PerfilSalvo).where(PerfilSalvo.cliente_usuario == cliente, PerfilSalvo.instagram_pk == instagram_pk))
        if existente:
            continue
        if not dry_run:
            session.add(PerfilSalvo(cliente_usuario=cliente, instagram_pk=instagram_pk, username=str(perfil.get("username") or "").strip() or None, perfil=perfil, caminho_historico_salvo=str(dados.get("caminho_historico_salvo") or "").strip() or None))
        inseridos += 1
    return inseridos


def migrar_monitoramentos(session: Session, dry_run: bool) -> int:
    inseridos = 0
    caminhos = list(iterar_json(USER_ROOT, "monitoramento/*.json"))
    caminhos += list(iterar_json(PUBLIC_ROOT, "monitoramento/*.json"))
    for caminho in sorted(caminhos):
        cliente = extrair_cliente(caminho)
        if not cliente:
            continue
        dados = carregar_json(caminho, {})
        if not isinstance(dados, dict):
            continue
        instagram_pk = str(dados.get("pk") or caminho.stem).strip()
        if not instagram_pk:
            continue
        existente = session.scalar(select(Monitoramento).where(Monitoramento.cliente_usuario == cliente, Monitoramento.instagram_pk == instagram_pk))
        if existente:
            continue
        if not dry_run:
            session.add(Monitoramento(cliente_usuario=cliente, instagram_pk=instagram_pk, username=str(dados.get("username") or "").strip() or None, monitorando=bool(dados.get("monitorando", False)), sleep=int(dados.get("sleep", 10) or 10), dados=dados, atualizado_em=normalizar_datetime(dados.get("atualizado"))))
        inseridos += 1
    return inseridos


def chave_historico(cliente: str, item: dict) -> tuple[str, str, str, str]:
    perfil = item.get("perfil") if isinstance(item.get("perfil"), dict) else {}
    return (cliente, str(perfil.get("pk") or ""), chave_datetime(item.get("timestamp_capture")), str(item.get("hash") or ""))


def migrar_historicos(session: Session, dry_run: bool) -> int:
    inseridos = 0
    caminhos = list(iterar_json(USER_ROOT, "historico/*.json"))
    caminhos += list(iterar_json(PUBLIC_ROOT, "historico/*.json"))
    existentes: set[tuple[str, str, str, str]] = set()
    if not dry_run:
        for registro in session.scalars(select(HistoricoPerfil)).all():
            dados = registro.dados if isinstance(registro.dados, dict) else {}
            existentes.add((registro.cliente_usuario, registro.instagram_pk, chave_datetime(registro.timestamp_capture), str(dados.get("hash") or "")))
    for caminho in sorted(caminhos):
        cliente = extrair_cliente(caminho)
        if not cliente:
            continue
        for item in ler_lista(caminho):
            perfil = item.get("perfil") if isinstance(item.get("perfil"), dict) else {}
            instagram_pk = str(perfil.get("pk") or caminho.stem).strip()
            timestamp = normalizar_datetime(item.get("timestamp_capture"))
            chave = chave_historico(cliente, item)
            if chave in existentes:
                continue
            dados_extra = {k: v for k, v in item.items() if k != "perfil"}
            if not dry_run:
                session.add(HistoricoPerfil(cliente_usuario=cliente, instagram_pk=instagram_pk, timestamp_capture=timestamp, perfil=perfil, dados=dados_extra))
            existentes.add(chave)
            inseridos += 1
    return inseridos


def chave_feed(item: dict) -> tuple[str, str, str, str, str]:
    return (str(item.get("cliente_usuario") or ""), str(item.get("pk") or ""), chave_datetime(item.get("timestamp_capture")), str(item.get("username") or ""), str(item.get("hash_atividade") or item.get("mensagem") or ""))


def migrar_feed(session: Session, dry_run: bool) -> int:
    inseridos = 0
    caminhos = list(iterar_json(USER_ROOT, "feed/feed.json"))
    caminhos += list(iterar_json(PUBLIC_ROOT, "feed/feed.json"))
    existentes: set[tuple[str, str, str, str, str]] = set()
    if not dry_run:
        for registro in session.scalars(select(FeedItem)).all():
            item = registro.item if isinstance(registro.item, dict) else {}
            existentes.add(chave_feed(item))
    for caminho in sorted(caminhos):
        cliente = extrair_cliente(caminho)
        if not cliente:
            continue
        for item in ler_lista(caminho):
            item = dict(item)
            item.setdefault("cliente_usuario", cliente)
            chave = chave_feed(item)
            if chave in existentes:
                continue
            if not dry_run:
                session.add(FeedItem(cliente_usuario=cliente, timestamp_capture=normalizar_datetime(item.get("timestamp_capture")), movimento=item.get("movimento") if isinstance(item.get("movimento"), bool) else None, item=item))
            existentes.add(chave)
            inseridos += 1
    return inseridos


def executar(dry_run: bool = False) -> dict[str, int]:
    criar_tabelas()
    engine = get_engine()
    resultados: dict[str, int] = {}
    etapas = (("usuarios", migrar_usuarios), ("sessoes", migrar_sessoes), ("perfis_salvos", migrar_perfis_salvos), ("monitoramentos", migrar_monitoramentos), ("historico_perfis", migrar_historicos), ("feed_itens", migrar_feed))
    for nome, funcao in etapas:
        with Session(engine) as session:
            try:
                with session.begin():
                    quantidade = funcao(session, dry_run)
                resultados[nome] = quantidade
            except Exception:
                session.rollback()
                raise
    return resultados


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra os JSONs legados para PostgreSQL sem apagar os arquivos originais.")
    parser.add_argument("--apply", action="store_true", help="Executa a gravação no PostgreSQL. Sem esta opção, apenas simula.")
    args = parser.parse_args()
    dry_run = not args.apply
    resultados = executar(dry_run=dry_run)
    modo = "SIMULAÇÃO" if dry_run else "MIGRAÇÃO"
    print(f"\n[{modo}] resultado:")
    for tabela, quantidade in resultados.items():
        print(f"- {tabela}: {quantidade}")
    if dry_run:
        print("\nNenhum dado foi gravado. Para executar, use: python -m backend.database.migrate_json --apply")


if __name__ == "__main__":
    main()
