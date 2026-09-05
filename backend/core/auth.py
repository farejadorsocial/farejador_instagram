import re
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.connection import get_engine
from backend.database.models import Sessao, Usuario


USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,64}$")
SESSION_DAYS = 7


def _normalizar_username(username):
    return str(username or "").strip().lower()


def _validar_username(username):
    username = _normalizar_username(username)
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Usuário deve ter de 3 a 64 caracteres e usar apenas letras, números, ponto, hífen ou underscore.")
    return username


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


def _hash_token(token):
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _agora():
    return datetime.now(timezone.utc)


def register(username, password, dados_acesso=None):
    username = _validar_username(username)
    if len(password) < 6:
        raise ValueError("A senha deve ter pelo menos 6 caracteres.")

    salt, password_hash = _password_hash(password)
    agora = _agora()
    acesso = dados_acesso if isinstance(dados_acesso, dict) else {}

    with Session(get_engine()) as session:
        existente = session.scalar(select(Usuario).where(Usuario.username == username))
        if existente:
            raise ValueError("Usuário já cadastrado.")

        usuario = Usuario(
            username=username,
            password_hash=password_hash,
            salt=salt,
            criado_em=agora,
            ultimo_login=None,
            ativo=True,
            configuracoes={
                "tema": "light",
                "idioma": "pt-BR",
                "timezone": acesso.get("dispositivo", {}).get("timezone") if isinstance(acesso.get("dispositivo"), dict) else None,
            },
        )
        session.add(usuario)
        session.commit()

    return username


def login(username, password, dados_acesso=None):
    username = _normalizar_username(username)
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("Usuário ou senha inválidos.")

    acesso = dados_acesso if isinstance(dados_acesso, dict) else {}
    agora = _agora()
    token = secrets.token_urlsafe(32)
    session_id = secrets.token_hex(16)
    expira_em = agora + timedelta(days=SESSION_DAYS)

    with Session(get_engine()) as session:
        usuario = session.scalar(select(Usuario).where(Usuario.username == username))
        if not usuario or not usuario.ativo:
            raise ValueError("Usuário ou senha inválidos.")

        if not _verify(password, usuario.salt, usuario.password_hash):
            raise ValueError("Usuário ou senha inválidos.")

        sessao = Sessao(
            session_id=session_id,
            token_hash=_hash_token(token),
            username=username,
            criada_em=agora,
            ultimo_acesso=agora,
            expira_em=expira_em,
            ativa=True,
            acesso={
                "conexao": acesso.get("conexao", {}),
                "origem": acesso.get("origem", {}),
                "dispositivo": acesso.get("dispositivo", {}),
            },
            permissoes=acesso.get("permissoes", {}),
        )
        session.add(sessao)

        usuario.ultimo_login = agora
        usuario.ativo = True
        session.commit()

    return token, username


def logout(token):
    if not token:
        return

    token_hash = _hash_token(token)
    agora = _agora()

    with Session(get_engine()) as session:
        sessao = session.scalar(
            select(Sessao).where(
                Sessao.token_hash == token_hash,
                Sessao.ativa.is_(True),
            )
        )
        if not sessao:
            return

        sessao.ativa = False
        sessao.ultimo_acesso = agora
        session.commit()


def get_user(token):
    if not token:
        return None

    token_hash = _hash_token(token)
    agora = _agora()

    with Session(get_engine()) as session:
        sessao = session.scalar(
            select(Sessao).where(
                Sessao.token_hash == token_hash,
                Sessao.ativa.is_(True),
            )
        )

        if not sessao:
            return None

        if not sessao.expira_em or sessao.expira_em <= agora:
            sessao.ativa = False
            session.commit()
            return None

        sessao.ultimo_acesso = agora
        session.commit()
        return sessao.username
