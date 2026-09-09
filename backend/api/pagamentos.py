from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.core.dependencies import require_user
from backend.services.credito_service import obter_usuario_id
from backend.services.pagamento_service import (
    criar_checkout,
    listar_pacotes,
    obter_pagamento_usuario,
    processar_webhook,
    validar_assinatura_webhook,
)


router = APIRouter()


class CheckoutCreditoBody(BaseModel):
    pacote: str = Field(min_length=1, max_length=32)
    idempotency_key: Optional[str] = Field(default=None, max_length=128)


@router.get("/api/pagamentos/pacotes")
def get_pacotes():
    return {"pacotes": listar_pacotes()}


@router.post("/api/pagamentos/checkout")
def post_checkout(body: CheckoutCreditoBody, request: Request):
    usuario = require_user(request)
    try:
        usuario_id = obter_usuario_id(usuario)
        resultado = criar_checkout(usuario_id, body.pacote, body.idempotency_key)
        if not resultado.get("checkout_url"):
            raise HTTPException(
                status_code=503,
                detail="O checkout do Mercado Pago não está disponível. Configure o ambiente de pagamentos.",
            )
        return resultado
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))
    except RuntimeError as erro:
        raise HTTPException(status_code=503, detail=str(erro))
    except Exception as erro:
        raise HTTPException(status_code=500, detail=str(erro))


@router.get("/api/pagamentos/{referencia}")
def get_pagamento(referencia: str, request: Request):
    usuario = require_user(request)
    try:
        return obter_pagamento_usuario(obter_usuario_id(usuario), referencia)
    except ValueError as erro:
        raise HTTPException(status_code=404, detail=str(erro))
    except Exception as erro:
        raise HTTPException(status_code=500, detail=str(erro))


@router.post("/api/pagamentos/webhook")
async def webhook(request: Request):
    data_id = request.query_params.get("data.id") or request.query_params.get("id")
    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")

    if not validar_assinatura_webhook(x_signature, x_request_id, str(data_id or "")):
        raise HTTPException(status_code=401, detail="Assinatura do webhook inválida.")

    try:
        payload = await request.json()
        processar_webhook(payload, data_id=data_id)
        return {"recebido": True}
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))
    except Exception as erro:
        raise HTTPException(status_code=500, detail=str(erro))
