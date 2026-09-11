from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import PagamentoCredito
from backend.services.credito_service import creditar


MERCADOPAGO_API = "https://api.mercadopago.com"
PACOTES_CREDITOS = {
    "inicial": {"creditos": 50, "valor_centavos": 1500, "nome": "50 créditos"},
}


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _token() -> str:
    return str(os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")).strip()


def _base_publica() -> str:
    return str(os.getenv("FAREJADOR_PUBLIC_URL", "")).strip().rstrip("/")


def _webhook_secret() -> str:
    return str(os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "")).strip()


def listar_pacotes() -> list[dict[str, Any]]:
    return [
        {
            "id": pacote_id,
            "nome": dados["nome"],
            "creditos": dados["creditos"],
            "valor_centavos": dados["valor_centavos"],
            "valor": dados["valor_centavos"] / 100,
            "moeda": "BRL",
        }
        for pacote_id, dados in PACOTES_CREDITOS.items()
    ]


def _pacote(pacote_id: str) -> dict[str, Any]:
    pacote = PACOTES_CREDITOS.get(str(pacote_id or "").strip().lower())
    if not pacote:
        raise ValueError("Pacote de créditos inválido.")
    return pacote


def _mp_request(method: str, path: str, payload: Optional[dict[str, Any]] = None, idempotency_key: Optional[str] = None) -> dict[str, Any]:
    token = _token()
    if not token:
        raise RuntimeError("Mercado Pago não configurado. Defina MERCADOPAGO_ACCESS_TOKEN.")

    url = f"{MERCADOPAGO_API}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = UrlRequest(url, data=body, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as erro:
        detalhe = erro.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Mercado Pago retornou HTTP {erro.code}: {detalhe[:500]}") from erro
    except URLError as erro:
        raise RuntimeError(f"Não foi possível conectar ao Mercado Pago: {erro.reason}") from erro

    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as erro:
        raise RuntimeError("Mercado Pago retornou uma resposta inválida.") from erro


def criar_checkout(usuario_id: int, pacote_id: str, idempotency_key: Optional[str] = None) -> dict[str, Any]:
    pacote = _pacote(pacote_id)
    chave = str(idempotency_key or "").strip() or f"checkout:{usuario_id}:{pacote_id}:{uuid.uuid4()}"
    referencia = str(uuid.uuid4())
    agora = _agora()
    base_publica = _base_publica()

    with Session(get_engine()) as session:
        existente = session.scalar(
            select(PagamentoCredito)
            .where(PagamentoCredito.usuario_id == int(usuario_id), PagamentoCredito.chave_idempotencia == chave)
        )
        if existente is not None:
            return _resultado_pagamento(existente)

        pagamento = PagamentoCredito(
            usuario_id=int(usuario_id),
            pacote=str(pacote_id).strip().lower(),
            creditos=int(pacote["creditos"]),
            valor_centavos=int(pacote["valor_centavos"]),
            moeda="BRL",
            status="pendente",
            referencia_externa=referencia,
            chave_idempotencia=chave,
            dados={"pacote": pacote},
            criado_em=agora,
            atualizado_em=agora,
        )
        session.add(pagamento)
        session.commit()
        session.refresh(pagamento)

        payload = {
            "items": [
                {
                    "id": f"farejador-{pacote_id}",
                    "title": f"Farejador — {pacote['nome']}",
                    "description": "Créditos para análise, salvamento e monitoramento de perfis.",
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": pacote["valor_centavos"] / 100,
                }
            ],
            "external_reference": referencia,
            "statement_descriptor": "FAREJADOR",
            "metadata": {
                "usuario_id": int(usuario_id),
                "pacote": str(pacote_id).strip().lower(),
                "creditos": int(pacote["creditos"]),
            },
        }
        if base_publica:
            payload["back_urls"] = {
                "success": f"{base_publica}/?pagamento=sucesso",
                "pending": f"{base_publica}/?pagamento=pendente",
                "failure": f"{base_publica}/?pagamento=falha",
            }
            payload["auto_return"] = "approved"
            payload["notification_url"] = f"{base_publica}/api/pagamentos/webhook"

        preference = _mp_request("POST", "/checkout/preferences", payload, idempotency_key=chave)
        pagamento.preferencia_id = str(preference.get("id") or "")[:128] or None
        pagamento.dados = {**(pagamento.dados or {}), "preference": preference}
        pagamento.atualizado_em = _agora()
        session.commit()
        session.refresh(pagamento)
        return _resultado_pagamento(pagamento, preference=preference)


def consultar_pagamento_mercado_pago(pagamento_id: str) -> dict[str, Any]:
    pagamento_id = str(pagamento_id or "").strip()
    if not pagamento_id:
        raise ValueError("Pagamento inválido.")
    return _mp_request("GET", f"/v1/payments/{pagamento_id}")


def _associar_e_creditar(pagamento_id: str) -> dict[str, Any]:
    pagamento_mp = consultar_pagamento_mercado_pago(pagamento_id)
    referencia = str(pagamento_mp.get("external_reference") or "").strip()
    if not referencia:
        raise ValueError("Pagamento sem referência externa.")

    with Session(get_engine()) as session:
        pagamento = session.scalar(select(PagamentoCredito).where(PagamentoCredito.referencia_externa == referencia))
        if pagamento is None:
            raise ValueError("Pedido de créditos não encontrado.")

        status_mp = str(pagamento_mp.get("status") or "").strip().lower()
        mapa = {
            "approved": "aprovado",
            "pending": "pendente",
            "in_process": "pendente",
            "rejected": "recusado",
            "cancelled": "cancelado",
            "refunded": "estornado",
            "charged_back": "estornado",
        }
        novo_status = mapa.get(status_mp, "pendente")
        agora = _agora()

        if pagamento.pagamento_id and str(pagamento.pagamento_id) != str(pagamento_id):
            raise ValueError("Pedido associado a outro pagamento.")

        pagamento.pagamento_id = str(pagamento_id)[:128]
        pagamento.status = novo_status
        pagamento.dados = {**(pagamento.dados or {}), "payment": pagamento_mp}
        pagamento.atualizado_em = agora

        if novo_status == "aprovado" and pagamento.creditado_em is None:
            chave_credito = f"compra:{pagamento.referencia_externa}"
            transacao = creditar(
                pagamento.usuario_id,
                pagamento.creditos,
                tipo="compra",
                descricao=f"Compra do pacote {pagamento.creditos} créditos",
                referencia_id=pagamento.referencia_externa,
                chave_idempotencia=chave_credito,
                dados={
                    "pagamento_id": str(pagamento_id),
                    "mercado_pago_status": status_mp,
                    "pacote": pagamento.pacote,
                    "valor_centavos": pagamento.valor_centavos,
                },
            )
            pagamento.creditado_em = transacao.get("criado_em") and datetime.fromisoformat(transacao["criado_em"])
            pagamento.status = "creditado"

        session.commit()
        session.refresh(pagamento)
        return _resultado_pagamento(pagamento, payment=pagamento_mp)


def processar_webhook(payload: dict[str, Any], data_id: Optional[str] = None) -> dict[str, Any]:
    tipo = str(payload.get("type") or "").strip().lower()
    if tipo != "payment":
        return {"recebido": True, "ignorado": True, "motivo": "evento_nao_payment"}

    pagamento_id = str(data_id or payload.get("data", {}).get("id") or "").strip()
    if not pagamento_id:
        raise ValueError("Webhook sem ID do pagamento.")
    return _associar_e_creditar(pagamento_id)


def validar_assinatura_webhook(x_signature: str, x_request_id: str, data_id: str) -> bool:
    secret = _webhook_secret()
    if not secret:
        return False

    assinatura = str(x_signature or "")
    partes: dict[str, str] = {}
    for parte in assinatura.split(","):
        if "=" in parte:
            chave, valor = parte.split("=", 1)
            partes[chave.strip()] = valor.strip()

    ts = partes.get("ts")
    v1 = partes.get("v1")
    data_id = str(data_id or "").strip()
    x_request_id = str(x_request_id or "").strip()

    if not ts or not v1 or not data_id:
        return False

    # O Mercado Pago determina que cada par só entra no manifesto
    # quando o respectivo valor existe na notificação recebida.
    partes_manifesto = [f"id:{data_id};"]
    if x_request_id:
        partes_manifesto.append(f"request-id:{x_request_id};")
    partes_manifesto.append(f"ts:{ts};")
    manifest = "".join(partes_manifesto)

    calculado = hmac.new(
        secret.encode("utf-8"),
        manifest.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(calculado, v1)


def obter_pagamento_usuario(usuario_id: int, referencia: str) -> dict[str, Any]:
    with Session(get_engine()) as session:
        pagamento = session.scalar(
            select(PagamentoCredito).where(
                PagamentoCredito.usuario_id == int(usuario_id),
                PagamentoCredito.referencia_externa == str(referencia).strip(),
            )
        )
        if pagamento is None:
            raise ValueError("Compra não encontrada.")
        return _resultado_pagamento(pagamento)


def _resultado_pagamento(pagamento: PagamentoCredito, preference: Optional[dict[str, Any]] = None, payment: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    dados = pagamento.dados or {}
    pref = preference or dados.get("preference") or {}
    return {
        "id": pagamento.id,
        "referencia_externa": pagamento.referencia_externa,
        "pacote": pagamento.pacote,
        "creditos": pagamento.creditos,
        "valor_centavos": pagamento.valor_centavos,
        "valor": pagamento.valor_centavos / 100,
        "moeda": pagamento.moeda,
        "status": pagamento.status,
        "preferencia_id": pagamento.preferencia_id,
        "pagamento_id": pagamento.pagamento_id,
        "creditado_em": pagamento.creditado_em.isoformat() if pagamento.creditado_em else None,
        "criado_em": pagamento.criado_em.isoformat() if pagamento.criado_em else None,
        "atualizado_em": pagamento.atualizado_em.isoformat() if pagamento.atualizado_em else None,
        "checkout_url": pref.get("init_point") or pref.get("sandbox_init_point"),
        "payment": payment or dados.get("payment"),
    }
