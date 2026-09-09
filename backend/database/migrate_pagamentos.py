from __future__ import annotations

from sqlalchemy import text

from backend.database.connection import get_engine
from backend.database.init_db import criar_tabelas


SQL = """
CREATE TABLE IF NOT EXISTS pagamentos_creditos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    pacote VARCHAR(32) NOT NULL,
    creditos INTEGER NOT NULL CHECK (creditos > 0),
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
    moeda VARCHAR(8) NOT NULL DEFAULT 'BRL',
    status VARCHAR(32) NOT NULL DEFAULT 'pendente',
    referencia_externa VARCHAR(128) NOT NULL UNIQUE,
    preferencia_id VARCHAR(128) NULL,
    pagamento_id VARCHAR(128) NULL UNIQUE,
    chave_idempotencia VARCHAR(128) NOT NULL UNIQUE,
    dados JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em TIMESTAMPTZ NOT NULL,
    atualizado_em TIMESTAMPTZ NOT NULL,
    creditado_em TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_pagamentos_creditos_usuario_data
    ON pagamentos_creditos (usuario_id, criado_em);

CREATE INDEX IF NOT EXISTS ix_pagamentos_creditos_status
    ON pagamentos_creditos (status);

CREATE INDEX IF NOT EXISTS ix_pagamentos_creditos_preferencia
    ON pagamentos_creditos (preferencia_id);
"""


def executar() -> None:
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(SQL))
    criar_tabelas()


if __name__ == "__main__":
    executar()
    print("Migração de pagamentos de créditos concluída.")
