import re
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]
USER_ROOT = BASE / "sistema" / "user"
USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,64}$")


def _normalizar_username(username):
    return str(username or "").strip().lower()


def _validar_username(username):
    username = _normalizar_username(username)
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Usuário deve ter de 3 a 64 caracteres e usar apenas letras, números, ponto, hífen ou underscore.")
    return username

# Arquivos antigos são mantidos somente como fonte de migração/compatibilidade.
LEGACY_USERS_FILE = USER_ROOT / "usuarios.json"
LEGACY_SESSIONS_FILE = USER_ROOT / "sessoes.json"
LEGACY_ACTIVITY_DIR = USER_ROOT / "atividade"


def _user_dir(username):
    username = _validar_username(username)
    return USER_ROOT / username


def _user_file(username, nome):
    return _user_dir(username) / nome


def _load(path, default):
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _save(path, data):
    """Grava JSON de forma atômica."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporario = path.with_name(f".{path.name}.tmp")
    with temporario.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
    temporario.replace(path)


def _password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(),
        salt=bytes.fromhex(salt),
        n=2**14,
        r=8,
        p=1,
    )
    return salt, digest.hex()


def _verify(password, salt, expected):
    _, value = _password_hash(password, salt)
    return hmac.compare_digest(value, expected)


def _ensure_user_dir(username):
    root = _user_dir(username)
    root.mkdir(parents=True, exist_ok=True)
    (root / "dados").mkdir(parents=True, exist_ok=True)
    for nome, default in (
        ("sessoes.json", []),
        ("atividades.json", []),
    ):
        caminho = root / nome
        if not caminho.exists():
            _save(caminho, default)
    return root


def _migrate_legacy_user(username, legacy_user):
    """Cria o armazenamento individual sem apagar o legado."""
    root = _ensure_user_dir(username)
    usuario = root / "usuario.json"

    if not usuario.exists():
        _save(usuario, legacy_user)

    sessoes = root / "sessoes.json"
    atuais = _load(sessoes, [])
    if not isinstance(atuais, list):
        atuais = []

    legacy_sessions = _load(LEGACY_SESSIONS_FILE, [])
    tokens_atuais = {s.get("token") for s in atuais if isinstance(s, dict)}

    for sessao in legacy_sessions:
        if (
            isinstance(sessao, dict)
            and sessao.get("cliente_usuario") == username
            and sessao.get("token") not in tokens_atuais
        ):
            atuais.append(sessao)

    _save(sessoes, atuais)

    atividades = root / "atividades.json"
    atuais_atividades = _load(atividades, [])
    if not isinstance(atuais_atividades, list):
        atuais_atividades = []

    legacy_activity = _load(LEGACY_ACTIVITY_DIR / f"{username}.json", [])
    if not isinstance(legacy_activity, list):
        legacy_activity = []

    if not atuais_atividades and legacy_activity:
        _save(atividades, legacy_activity[-200:])


def _migrate_all_legacy_users():
    users = _load(LEGACY_USERS_FILE, [])
    if not isinstance(users, list):
        users = []

    for user in users:
        if not isinstance(user, dict):
            continue
        username = str(user.get("username") or "").strip().lower()
        if username:
            _migrate_legacy_user(username, user)



def preparar_usuarios():
    """Garante a estrutura individual dos usuários existentes."""
    _migrate_all_legacy_users()
    if not USER_ROOT.exists():
        return

    for pasta in USER_ROOT.iterdir():
        if not pasta.is_dir():
            continue
        usuario = pasta / "usuario.json"
        if usuario.exists():
            _ensure_user_dir(pasta.name)

def _load_user(username):
    username = str(username or "").strip().lower()
    if not username:
        return None

    _migrate_all_legacy_users()

    dados = _load(_user_file(username, "usuario.json"), None)
    return dados if isinstance(dados, dict) else None


def _log_activity(username, tipo, **dados):
    """Registra autenticação no diretório individual do cliente."""
    try:
        username = str(username or "").strip().lower()
        if not username:
            return

        caminho = _user_file(username, "atividades.json")
        registros = _load(caminho, [])
        if not isinstance(registros, list):
            registros = []

        registros.append({
            "tipo": tipo,
            "timestamp": datetime.now().isoformat(),
            **dados,
        })
        _save(caminho, registros[-200:])
    except Exception:
        # O histórico nunca impede login/cadastro/logout.
        pass


def register(username, password, dados_acesso=None):
    username = _validar_username(username)
    if len(password) < 6:
        raise ValueError("A senha deve ter pelo menos 6 caracteres.")

    _migrate_all_legacy_users()

    if _load_user(username):
        raise ValueError("Usuário já cadastrado.")

    salt, password_hash = _password_hash(password)
    agora = datetime.now().isoformat()
    usuario = {
        "cliente_usuario": username,
        "usuario": {
            "username": username
        },
        "conta": {
            "criado_em": agora,
            "ultimo_login": None,
            "ativo": True
        },
        "configuracoes": {
            "tema": "light",
            "idioma": "pt-BR",
            "timezone": dados_acesso.get("dispositivo", {}).get("timezone") if isinstance(dados_acesso, dict) else None
        },
        "seguranca": {
            "password_hash": password_hash,
            "salt": salt,
            "dois_fatores": {
                "ativo": False,
                "metodo": None
            }
        }
    }

    _ensure_user_dir(username)

    from toolFarejador.sistema.toolLimiteExibicaoDados import garantir_configuracao_usuario
    garantir_configuracao_usuario(username)

    _save(_user_file(username, "usuario.json"), usuario)
    _save(_user_file(username, "sessoes.json"), [])
    _save(_user_file(username, "atividades.json"), [])
    _log_activity(
        username,
        "cadastro",
        acesso=dados_acesso or {},
    )

    return username


def login(username, password, dados_acesso=None):
    username = _normalizar_username(username)
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Usuário ou senha inválidos.")

    user = _load_user(username)
    if not isinstance(user, dict):
        raise ValueError("Usuário ou senha inválidos.")

    seguranca = user.get("seguranca") or {}
    salt = seguranca.get("salt") or user.get("salt", "")
    password_hash = seguranca.get("password_hash") or user.get("password_hash", "")
    if not user or not _verify(password, salt, password_hash):
        raise ValueError("Usuário ou senha inválidos.")

    caminho = _user_file(username, "sessoes.json")
    sessions = _load(caminho, [])
    if not isinstance(sessions, list):
        sessions = []

    agora = datetime.now()
    valid = []

    for sessao in sessions:
        try:
            if datetime.fromisoformat(sessao["expira_em"]) > agora:
                valid.append(sessao)
        except (KeyError, TypeError, ValueError):
            continue

    token = secrets.token_urlsafe(32)
    session_id = secrets.token_hex(16)
    acesso = dados_acesso or {}

    sessao = {
        "session_id": session_id,
        "token": token,
        "cliente_usuario": username,
        "status": {
            "ativa": True,
            "criada_em": agora.isoformat(),
            "ultimo_acesso": agora.isoformat(),
            "expira_em": (agora + timedelta(days=7)).isoformat(),
        },
        "criado_em": agora.isoformat(),
        "expira_em": (agora + timedelta(days=7)).isoformat(),
        "acesso": {
            "conexao": acesso.get("conexao", {}),
            "origem": acesso.get("origem", {}),
            "dispositivo": acesso.get("dispositivo", {}),
        },
        "permissoes": acesso.get("permissoes", {}),
    }

    valid.append(sessao)
    _save(caminho, valid)

    usuario_atual = _load(_user_file(username, "usuario.json"), {})
    if isinstance(usuario_atual, dict):
        usuario_atual.setdefault("conta", {})
        usuario_atual["conta"]["ultimo_login"] = agora.isoformat()
        usuario_atual["conta"]["ativo"] = True
        _save(_user_file(username, "usuario.json"), usuario_atual)

    _log_activity(
        username,
        "login",
        session_id=session_id,
        acesso=sessao["acesso"],
        permissoes=sessao.get("permissoes", {}),
    )

    return token, username


def logout(token):
    if not token:
        return

    _migrate_all_legacy_users()

    for pasta in USER_ROOT.iterdir():
        if not pasta.is_dir():
            continue

        caminho = pasta / "sessoes.json"
        sessions = _load(caminho, [])
        if not isinstance(sessions, list):
            continue

        sessao = next(
            (s for s in sessions if isinstance(s, dict) and s.get("token") == token),
            None,
        )

        if sessao:
            _save(
                caminho,
                [
                    s for s in sessions
                    if not (isinstance(s, dict) and s.get("token") == token)
                ],
            )
            _log_activity(pasta.name, "logout", session_id=sessao.get("session_id") or sessao.get("token"), acesso=sessao.get("acesso", {"conexao": sessao.get("conexao", {}), "origem": sessao.get("origem", {}), "dispositivo": sessao.get("dispositivo", {})}))
            return


def get_user(token):
    if not token:
        return None

    _migrate_all_legacy_users()

    agora = datetime.now()

    for pasta in USER_ROOT.iterdir():
        if not pasta.is_dir():
            continue

        caminho = pasta / "sessoes.json"
        sessions = _load(caminho, [])
        if not isinstance(sessions, list):
            continue

        valid = []
        encontrado = None
        alterado = False

        for sessao in sessions:
            try:
                expirado = datetime.fromisoformat(
                    sessao["expira_em"]
                ) <= agora
            except (KeyError, TypeError, ValueError):
                expirado = True

            if expirado:
                alterado = True
                continue

            valid.append(sessao)

            if hmac.compare_digest(
                sessao.get("token", "") or sessao.get("session_id", ""),
                token,
            ):
                encontrado = sessao.get("cliente_usuario")
                agora_iso = agora.isoformat()
                sessao["ultimo_acesso"] = agora_iso
                sessao.setdefault("status", {})
                sessao["status"]["ativa"] = True
                sessao["status"]["ultimo_acesso"] = agora_iso
                sessao["status"]["expira_em"] = sessao.get("expira_em")
                alterado = True

        if alterado:
            _save(caminho, valid)

        if encontrado:
            return encontrado

    return None
