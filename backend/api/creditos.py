from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.dependencies import require_user
from backend.database.connection import get_engine
from backend.database.models import Usuario
from backend.services.credito_service import obter_conta, obter_transacoes

router = APIRouter()


def _usuario_id(username: str) -> int:
    with Session(get_engine()) as session:
        usuario_id = session.scalar(
            select(Usuario.id).where(
                Usuario.username == str(username).strip().lower(),
                Usuario.ativo.is_(True),
            )
        )
    if usuario_id is None:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo.")
    return int(usuario_id)


@router.get("/api/creditos")
def get_creditos(request: Request):
    usuario = require_user(request)
    try:
        return obter_conta(_usuario_id(usuario))
    except HTTPException:
        raise
    except Exception as erro:
        raise HTTPException(status_code=500, detail=str(erro))


@router.get("/api/creditos/transacoes")
def get_transacoes(request: Request, limite: int = 50, offset: int = 0):
    usuario = require_user(request)
    try:
        return {
            "transacoes": obter_transacoes(_usuario_id(usuario), limite=limite, offset=offset),
            "limite": min(max(int(limite), 1), 200),
            "offset": max(int(offset), 0),
        }
    except HTTPException:
        raise
    except Exception as erro:
        raise HTTPException(status_code=500, detail=str(erro))
