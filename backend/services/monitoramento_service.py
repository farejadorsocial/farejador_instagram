from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import Monitoramento
from backend.repositories.perfil_repository import get_saved_profiles
from backend.repositories.monitoramento_repository import (
    set_monitoring_data,
    solicitar_atualizacao as repository_solicitar_atualizacao,
    notificar_movimentos,
)
from backend.services.common import normalizar_username
from backend.services.feed_service import feed
from backend.services.credito_service import obter_usuario_id, obter_saldo, debitar, creditar

DURACAO_MONITORAMENTO_DIAS = 30
CUSTO_MONITORAMENTO = 10


def _agora():
    return datetime.now(timezone.utc)


def _chave_lock(usuario_id, pk):
    return f"farejador:monitor:{int(usuario_id)}:{str(pk)}"


def _normalizar_datas(inicio, fim):
    if inicio and inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    if fim and fim.tzinfo is None:
        fim = fim.replace(tzinfo=timezone.utc)
    return inicio, fim


def _estado_monitoramento(session, cliente_usuario, pk):
    registro = session.scalar(
        select(Monitoramento).where(
            Monitoramento.cliente_usuario == cliente_usuario,
            Monitoramento.instagram_pk == str(pk),
        )
    )
    if registro is None:
        return None

    inicio, fim = _normalizar_datas(registro.inicio_monitoramento, registro.fim_monitoramento)
    agora = _agora()
    if registro.monitorando and fim and fim <= agora:
        registro.monitorando = False
        registro.inicio_monitoramento = None
        registro.fim_monitoramento = None
        dados = dict(registro.dados or {})
        dados["monitorando"] = False
        dados["monitoramento_expirado"] = True
        registro.dados = dados
        registro.atualizado_em = agora
        session.flush()
        return registro

    return registro


def verificar_monitoramento_ativo(cliente_usuario, username):
    username = normalizar_username(username)
    if not username:
        return False
    with Session(get_engine()) as session:
        registro = session.scalar(
            select(Monitoramento).where(
                Monitoramento.cliente_usuario == cliente_usuario,
                Monitoramento.username == username,
            )
        )
        if registro is None:
            return False
        registro = _estado_monitoramento(session, cliente_usuario, registro.instagram_pk)
        session.commit()
        return bool(registro and registro.monitorando)


def status_monitoramento(cliente_usuario, username):
    username = normalizar_username(username)
    if not username:
        return {"monitorando": False, "inicio_monitoramento": None, "fim_monitoramento": None, "dias_restantes": 0}
    with Session(get_engine()) as session:
        registro = session.scalar(
            select(Monitoramento).where(
                Monitoramento.cliente_usuario == cliente_usuario,
                Monitoramento.username == username,
            )
        )
        if registro is None:
            return {"monitorando": False, "inicio_monitoramento": None, "fim_monitoramento": None, "dias_restantes": 0}
        registro = _estado_monitoramento(session, cliente_usuario, registro.instagram_pk)
        agora = _agora()
        fim = registro.fim_monitoramento
        dias = max(0, (fim - agora).days + (1 if fim and (fim - agora).seconds > 0 else 0)) if registro.monitorando and fim else 0
        session.commit()
        return {
            "monitorando": bool(registro.monitorando),
            "inicio_monitoramento": registro.inicio_monitoramento.isoformat() if registro.inicio_monitoramento else None,
            "fim_monitoramento": fim.isoformat() if fim else None,
            "dias_restantes": dias,
        }


def set_monitoring(cliente_usuario, username, enabled):
    username = normalizar_username(username)
    profiles = get_saved_profiles(cliente_usuario)
    selected = next(
        (p for p in profiles if normalizar_username(p["perfil"].get("username")) == username),
        None,
    )
    if not selected:
        raise ValueError("Perfil não encontrado entre os usuários salvos.")

    pk = selected["perfil"].get("pk")
    usuario_id = obter_usuario_id(cliente_usuario)
    agora = _agora()
    lock_session = Session(get_engine())
    debitado = False
    try:
        lock_session.execute(select(func.pg_advisory_xact_lock(func.hashtext(_chave_lock(usuario_id, pk)))))
        registro = _estado_monitoramento(lock_session, cliente_usuario, pk)

        if enabled:
            if registro and registro.monitorando:
                fim = registro.fim_monitoramento
                dias = max(0, (fim - agora).days + (1 if fim and (fim - agora).seconds > 0 else 0)) if fim else 0
                lock_session.commit()
                return {
                    "monitorando": True,
                    "inicio_monitoramento": registro.inicio_monitoramento.isoformat() if registro.inicio_monitoramento else None,
                    "fim_monitoramento": fim.isoformat() if fim else None,
                    "dias_restantes": dias,
                    "creditos_consumidos": 0,
                    "novo_monitoramento": False,
                }

            saldo = obter_saldo(usuario_id)
            if saldo < CUSTO_MONITORAMENTO:
                lock_session.rollback()
                raise ValueError("Você não possui créditos suficientes para iniciar o monitoramento. São necessários 10 créditos.")

            chave = f"monitor:{usuario_id}:{pk}:{agora.isoformat()}"
            transacao = debitar(
                usuario_id,
                CUSTO_MONITORAMENTO,
                descricao="Iniciar monitoramento por 30 dias",
                referencia_id=str(pk),
                chave_idempotencia=chave,
                dados={"operacao": "monitoramento", "username": username, "pk": str(pk), "duracao_dias": DURACAO_MONITORAMENTO_DIAS},
            )
            debitado = not bool(transacao.get("idempotente"))

            # Mantém o mecanismo existente responsável por ativar o monitor real.
            resultado = set_monitoring_data(cliente_usuario, selected, True)
            inicio = agora
            fim = agora + timedelta(days=DURACAO_MONITORAMENTO_DIAS)

            registro = lock_session.scalar(
                select(Monitoramento).where(
                    Monitoramento.cliente_usuario == cliente_usuario,
                    Monitoramento.instagram_pk == str(pk),
                )
            )
            if registro is None:
                raise RuntimeError("Não foi possível registrar o monitoramento no PostgreSQL.")
            registro.monitorando = True
            registro.inicio_monitoramento = inicio
            registro.fim_monitoramento = fim
            dados = dict(registro.dados or resultado or {})
            dados.update({
                "pk": pk,
                "username": username,
                "monitorando": True,
                "inicio_monitoramento": inicio.isoformat(),
                "fim_monitoramento": fim.isoformat(),
                "duracao_dias": DURACAO_MONITORAMENTO_DIAS,
            })
            registro.dados = dados
            registro.atualizado_em = agora
            lock_session.commit()
            solicitar_atualizacao()
            return {
                "monitorando": True,
                "inicio_monitoramento": inicio.isoformat(),
                "fim_monitoramento": fim.isoformat(),
                "dias_restantes": DURACAO_MONITORAMENTO_DIAS,
                "creditos_consumidos": CUSTO_MONITORAMENTO,
                "novo_monitoramento": True,
                "transacao_credito": transacao,
            }

        if registro and registro.monitorando:
            lock_session.rollback()
            raise ValueError("O monitoramento está ativo pelos próximos 30 dias e não pode ser interrompido antes do vencimento.")

        resultado = set_monitoring_data(cliente_usuario, selected, False)
        lock_session.commit()
        solicitar_atualizacao()
        return {
            "monitorando": False,
            "inicio_monitoramento": None,
            "fim_monitoramento": None,
            "dias_restantes": 0,
            "creditos_consumidos": 0,
            "novo_monitoramento": False,
            "resultado": resultado,
        }
    except Exception:
        if debitado:
            try:
                creditar(
                    usuario_id,
                    CUSTO_MONITORAMENTO,
                    descricao="Estorno de monitoramento não registrado",
                    referencia_id=str(pk),
                    chave_idempotencia=f"refund:{usuario_id}:{pk}:{agora.isoformat()}",
                    dados={"operacao": "estorno_monitoramento", "username": username, "pk": str(pk)},
                )
            except Exception:
                pass
        try:
            lock_session.rollback()
        except Exception:
            pass
        raise
    finally:
        lock_session.close()


def refresh_notifications(cliente_usuario):
    """Atualiza notificações usando somente os dados persistidos no PostgreSQL."""
    usernames = [
        p["perfil"].get("username")
        for p in get_saved_profiles(cliente_usuario)
        if p["perfil"].get("username")
    ]
    if usernames:
        notificar_movimentos(usernames, cliente_usuario)
    return feed(cliente_usuario)


def analisar_comportamento(*args, **kwargs):
    from toolFarejador.monitoramento.toolResultadoMonitoramento import analisando_comportamento
    return analisando_comportamento(*args, **kwargs)


def solicitar_atualizacao():
    return repository_solicitar_atualizacao()
