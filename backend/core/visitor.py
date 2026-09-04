import json
import secrets
from datetime import datetime
from pathlib import Path
from fastapi import Request
from backend.core.config import BASE
from backend.core.security import dados_acesso_request

VISITOR_ROOT = BASE / "sistema" / "user" / "visitante"
VISITOR_SESSIONS = VISITOR_ROOT / "sessoes.json"
VISITOR_ACTIVITIES = VISITOR_ROOT / "atividades.json"
VISITOR_USERS = VISITOR_ROOT / "visitantes.json"

def _json_load(path, default):
    try:
        if not path.exists(): return default
        with path.open("r", encoding="utf-8") as f: return json.load(f)
    except (OSError, json.JSONDecodeError): return default

def _json_save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2); f.flush()
    tmp.replace(path)

def registrar_visitante(request: Request, dispositivo_cliente=None):
    visitante_id = request.cookies.get("farejador_visitante") or secrets.token_urlsafe(18)
    acesso = dados_acesso_request(request, dispositivo_cliente)
    agora_iso = datetime.now().isoformat()
    visitantes = _json_load(VISITOR_USERS, [])
    if not isinstance(visitantes, list): visitantes = []
    registro = next((x for x in visitantes if isinstance(x, dict) and x.get("visitante_id") == visitante_id), None)
    if registro is None:
        registro = {"visitante_id": visitante_id, "criado_em": agora_iso, "ultimo_acesso": agora_iso, "total_acessos": 0, "acesso": acesso}
        visitantes.append(registro)
    registro["ultimo_acesso"] = agora_iso
    registro["total_acessos"] = int(registro.get("total_acessos") or 0) + 1
    registro["acesso"] = acesso
    _json_save(VISITOR_USERS, visitantes[-5000:])
    atividades = _json_load(VISITOR_ACTIVITIES, [])
    if not isinstance(atividades, list): atividades = []
    atividades.append({"tipo": "visita", "timestamp": agora_iso, "visitante_id": visitante_id, "acesso": acesso})
    _json_save(VISITOR_ACTIVITIES, atividades[-5000:])
    sessoes = _json_load(VISITOR_SESSIONS, [])
    if not isinstance(sessoes, list): sessoes = []
    sessoes.append({"visitante_id": visitante_id, "ultima_visita": agora_iso, "acesso": acesso})
    _json_save(VISITOR_SESSIONS, sessoes[-2000:])
    return visitante_id
