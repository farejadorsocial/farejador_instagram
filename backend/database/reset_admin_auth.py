"""Limpeza única dos dados de autenticação/atividade do usuário admin.

Remove somente os dados diretamente ligados à autenticação do ``admin``:
- registro do usuário ``admin``;
- sessões vinculadas ao ``admin``;
- registros da tabela legada ``atividades`` quando ela existir e possuir
  uma coluna de identificação do usuário.

NÃO remove perfis salvos, monitoramentos, histórico de perfis, feed,
notificações, visitantes ou atividades de visitantes.

Pode ser executado pelo caminho do arquivo ou como módulo:
    python backend/database/reset_admin_auth.py
    python -m backend.database.reset_admin_auth
"""

from pathlib import Path
import sys

# Permite executar diretamente pelo caminho completo no Windows.
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import delete, inspect, text
from sqlalchemy.orm import sessionmaker

from backend.database.connection import get_engine
from backend.database.models import Sessao, Usuario


USERNAME = "admin"


def _criar_session_local():
    return sessionmaker(bind=get_engine(), future=True)


def _remover_atividades_legadas(connection) -> int:
    """Remove atividades da tabela legada ``atividades`` ligadas ao admin.

    A tabela ``atividades_visitante`` nunca é tocada.
    Se a tabela legada não existir, ou não tiver uma coluna identificadora
    inequívoca do usuário, nada é removido.
    """
    inspector = inspect(connection)
    if "atividades" not in inspector.get_table_names():
        return 0

    colunas = {c["name"] for c in inspector.get_columns("atividades")}

    coluna_usuario = next(
        (c for c in ("cliente_usuario", "username", "usuario", "user") if c in colunas),
        None,
    )
    if coluna_usuario is None:
        return 0

    resultado = connection.execute(
        text(f'DELETE FROM "atividades" WHERE "{coluna_usuario}" = :username'),
        {"username": USERNAME},
    )
    return resultado.rowcount or 0


def reset_admin_auth() -> tuple[int, int, int]:
    SessionLocal = _criar_session_local()

    with SessionLocal() as db:
        try:
            atividades_removidas = _remover_atividades_legadas(db.connection())

            sessoes_result = db.execute(
                delete(Sessao).where(Sessao.username == USERNAME)
            )
            sessoes_removidas = sessoes_result.rowcount or 0

            usuario_result = db.execute(
                delete(Usuario).where(Usuario.username == USERNAME)
            )
            usuarios_removidos = usuario_result.rowcount or 0

            db.commit()
            return usuarios_removidos, sessoes_removidas, atividades_removidas
        except Exception:
            db.rollback()
            raise


def main() -> None:
    usuarios, sessoes, atividades = reset_admin_auth()

    print("[reset-admin] Limpeza concluída.")
    print(f"[reset-admin] Usuários admin removidos: {usuarios}")
    print(f"[reset-admin] Sessões admin removidas: {sessoes}")
    print(f"[reset-admin] Atividades admin removidas: {atividades}")
    print("[reset-admin] Perfis, monitoramentos, histórico, feed e notificações preservados.")
    print("[reset-admin] Dados de visitantes e atividades_visitante preservados.")
    print("[reset-admin] Agora o usuário admin pode ser cadastrado novamente com uma nova senha.")


if __name__ == "__main__":
    main()
