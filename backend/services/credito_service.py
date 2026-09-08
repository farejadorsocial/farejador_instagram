from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import CreditoUsuario, TransacaoCredito, Usuario


TIPO_CREDITO = "credito"
TIPO_DEBITO = "debito"


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _normalizar_usuario(usuario_id: int) -> int:
    try:
        valor = int(usuario_id)
    except (TypeError, ValueError):
        raise ValueError("Usuário inválido.")
    if valor <= 0:
        raise ValueError("Usuário inválido.")
    return valor


def _obter_conta_bloqueada(session: Session, usuario_id: int) -> CreditoUsuario:
    usuario_id = _normalizar_usuario(usuario_id)

    # Garante a existência da carteira sem depender de corrida entre
    # requisições concorrentes. O conflito é resolvido pelo PostgreSQL.
    session.execute(
        insert(CreditoUsuario)
        .values(usuario_id=usuario_id, saldo=0, atualizado_em=_agora())
        .on_conflict_do_nothing(index_elements=[CreditoUsuario.usuario_id])
    )

    conta = session.scalar(
        select(CreditoUsuario)
        .where(CreditoUsuario.usuario_id == usuario_id)
        .with_for_update()
    )
    if conta is None:
        raise RuntimeError("Não foi possível obter a conta de créditos.")
    return conta


def _verificar_usuario(session: Session, usuario_id: int) -> None:
    existe = session.scalar(
        select(Usuario.id).where(Usuario.id == usuario_id, Usuario.ativo.is_(True))
    )
    if existe is None:
        raise ValueError("Usuário não encontrado ou inativo.")


def obter_saldo(usuario_id: int) -> int:
    usuario_id = _normalizar_usuario(usuario_id)
    with Session(get_engine()) as session:
        conta = session.scalar(
            select(CreditoUsuario.saldo).where(CreditoUsuario.usuario_id == usuario_id)
        )
        return int(conta or 0)


def creditar(
    usuario_id: int,
    quantidade: int,
    *,
    tipo: str = "credito",
    descricao: Optional[str] = None,
    referencia_id: Optional[str] = None,
    chave_idempotencia: Optional[str] = None,
    dados: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return _movimentar(
        usuario_id,
        quantidade,
        tipo=tipo,
        descricao=descricao,
        referencia_id=referencia_id,
        chave_idempotencia=chave_idempotencia,
        dados=dados,
    )


def debitar(
    usuario_id: int,
    quantidade: int,
    *,
    tipo: str = "debito",
    descricao: Optional[str] = None,
    referencia_id: Optional[str] = None,
    chave_idempotencia: Optional[str] = None,
    dados: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    quantidade = _normalizar_quantidade(quantidade)
    return _movimentar(
        usuario_id,
        -quantidade,
        tipo=tipo,
        descricao=descricao,
        referencia_id=referencia_id,
        chave_idempotencia=chave_idempotencia,
        dados=dados,
    )


def _normalizar_quantidade(quantidade: int) -> int:
    try:
        valor = int(quantidade)
    except (TypeError, ValueError):
        raise ValueError("Quantidade de créditos inválida.")
    if valor <= 0:
        raise ValueError("A quantidade de créditos deve ser maior que zero.")
    return valor


def _movimentar(
    usuario_id: int,
    quantidade: int,
    *,
    tipo: str,
    descricao: Optional[str],
    referencia_id: Optional[str],
    chave_idempotencia: Optional[str],
    dados: Optional[dict[str, Any]],
) -> dict[str, Any]:
    usuario_id = _normalizar_usuario(usuario_id)
    if not isinstance(tipo, str) or not tipo.strip():
        raise ValueError("Tipo de transação inválido.")

    delta = int(quantidade)
    if delta == 0:
        raise ValueError("A movimentação de créditos não pode ser zero.")

    with Session(get_engine()) as session:
        _verificar_usuario(session, usuario_id)
        conta = _obter_conta_bloqueada(session, usuario_id)

        # O bloqueio da carteira serializa operações concorrentes do mesmo
        # usuário. Assim, a checagem e a alteração do saldo são atômicas.
        if chave_idempotencia:
            existente = session.scalar(
                select(TransacaoCredito)
                .where(
                    TransacaoCredito.usuario_id == usuario_id,
                    TransacaoCredito.chave_idempotencia == chave_idempotencia,
                )
            )
            if existente is not None:
                session.commit()
                return _resultado_transacao(existente)

        saldo_anterior = int(conta.saldo)
        saldo_posterior = saldo_anterior + delta
        if saldo_posterior < 0:
            raise ValueError("Créditos insuficientes para realizar esta operação.")

        agora = _agora()
        conta.saldo = saldo_posterior
        conta.atualizado_em = agora

        transacao = TransacaoCredito(
            usuario_id=usuario_id,
            tipo=tipo.strip()[:32],
            quantidade=delta,
            saldo_anterior=saldo_anterior,
            saldo_posterior=saldo_posterior,
            descricao=descricao,
            referencia_id=str(referencia_id)[:128] if referencia_id is not None else None,
            chave_idempotencia=str(chave_idempotencia)[:128] if chave_idempotencia else None,
            dados=dados if isinstance(dados, dict) else {},
            criado_em=agora,
        )
        session.add(transacao)
        session.commit()
        session.refresh(transacao)
        return _resultado_transacao(transacao)


def _resultado_transacao(transacao: TransacaoCredito) -> dict[str, Any]:
    return {
        "id": transacao.id,
        "usuario_id": transacao.usuario_id,
        "tipo": transacao.tipo,
        "quantidade": transacao.quantidade,
        "saldo_anterior": transacao.saldo_anterior,
        "saldo_posterior": transacao.saldo_posterior,
        "descricao": transacao.descricao,
        "referencia_id": transacao.referencia_id,
        "chave_idempotencia": transacao.chave_idempotencia,
        "dados": transacao.dados or {},
        "criado_em": transacao.criado_em.isoformat() if transacao.criado_em else None,
        "idempotente": bool(transacao.chave_idempotencia),
    }


def obter_transacoes(usuario_id: int, limite: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    usuario_id = _normalizar_usuario(usuario_id)
    limite = min(max(int(limite), 1), 200)
    offset = max(int(offset), 0)

    with Session(get_engine()) as session:
        transacoes = session.scalars(
            select(TransacaoCredito)
            .where(TransacaoCredito.usuario_id == usuario_id)
            .order_by(TransacaoCredito.criado_em.desc(), TransacaoCredito.id.desc())
            .offset(offset)
            .limit(limite)
        ).all()
        return [_resultado_transacao(item) for item in transacoes]


def obter_conta(usuario_id: int) -> dict[str, Any]:
    usuario_id = _normalizar_usuario(usuario_id)
    with Session(get_engine()) as session:
        _verificar_usuario(session, usuario_id)
        conta = _obter_conta_bloqueada(session, usuario_id)
        saldo = int(conta.saldo)
        atualizado_em = conta.atualizado_em.isoformat() if conta.atualizado_em else None
        session.commit()
        return {
            "usuario_id": usuario_id,
            "saldo": saldo,
            "atualizado_em": atualizado_em,
        }
