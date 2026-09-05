"""Limpeza única dos dados de autenticação do usuário admin.

Remove somente:
- registro do usuário ``admin``;
- sessões vinculadas ao ``admin``.

Não remove perfis salvos, monitoramentos, histórico, feed ou notificações.
Também não remove dados de visitantes, pois são independentes da conta admin.

Execute uma única vez, com o backend parado:
    python -m backend.database.reset_admin_auth

Depois, o cadastro normal pode criar novamente o usuário admin com a nova senha.
"""

from sqlalchemy import delete, select

from backend.database.connection import SessionLocal
from backend.database.models import Sessao, Usuario


USERNAME = "admin"


def reset_admin_auth() -> tuple[int, int]:
    """Remove sessões e usuário admin, preservando os demais dados."""
    with SessionLocal() as db:
        try:
            sessoes_result = db.execute(
                delete(Sessao).where(Sessao.username == USERNAME)
            )
            sessoes_removidas = sessoes_result.rowcount or 0

            usuario_result = db.execute(
                delete(Usuario).where(Usuario.username == USERNAME)
            )
            usuarios_removidos = usuario_result.rowcount or 0

            db.commit()
            return usuarios_removidos, sessoes_removidas
        except Exception:
            db.rollback()
            raise


def main() -> None:
    usuarios, sessoes = reset_admin_auth()

    print("[reset-admin] Limpeza concluída.")
    print(f"[reset-admin] Usuários admin removidos: {usuarios}")
    print(f"[reset-admin] Sessões admin removidas: {sessoes}")
    print("[reset-admin] Perfis, monitoramentos, histórico, feed e notificações preservados.")
    print("[reset-admin] Agora o usuário admin pode ser cadastrado novamente com uma nova senha.")


if __name__ == "__main__":
    main()
