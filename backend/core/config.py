import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
FRONTEND = BASE / "frontend"
PERMISSOES_CONFIG = BASE / "sistema" / "config" / "permissoes_navegador.json"

def carregar_permissoes_navegador() -> dict:
    padrao = {
        "ativo": True,
        "login": {"localizacao": False, "camera": False, "microfone": False, "notificacoes": False},
        "cadastro": {"localizacao": False, "camera": False, "microfone": False, "notificacoes": False},
        "registrar_status_sem_solicitar": True,
        "mensagens": {
            "localizacao": "Para continuar, permita sua localização.",
            "camera": "Para continuar, permita o acesso à câmera.",
            "microfone": "Para continuar, permita o acesso ao microfone.",
            "notificacoes": "Para continuar, permita as notificações."
        }
    }
    try:
        if PERMISSOES_CONFIG.exists():
            with PERMISSOES_CONFIG.open("r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, dict):
                dados.setdefault("login", {})
                dados.setdefault("cadastro", {})
                for recurso in ("localizacao", "camera", "microfone", "notificacoes"):
                    dados["login"].setdefault(recurso, bool(dados.get(f"{recurso}_login", False)))
                    dados["cadastro"].setdefault(recurso, bool(dados.get(f"{recurso}_cadastro", False)))
                return dados
    except Exception as erro:
        print(f"[permissoes] Falha ao carregar configuração: {erro}")
    return padrao
