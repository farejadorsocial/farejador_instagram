import secrets

from fastapi import Request

from backend.core.security import dados_acesso_request
from backend.database.sync import registrar_visitante as registrar_visitante_db


def registrar_visitante(request: Request, dispositivo_cliente=None):
    visitante_id = request.cookies.get("farejador_visitante") or secrets.token_urlsafe(18)
    acesso = dados_acesso_request(request, dispositivo_cliente)
    return registrar_visitante_db(visitante_id, acesso)
