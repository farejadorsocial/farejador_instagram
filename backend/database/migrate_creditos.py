from __future__ import annotations

from sqlalchemy import text

from backend.database.connection import get_engine
from backend.database.init_db import criar_tabelas


SQL = """
CREATE TABLE IF NOT EXISTS creditos_usuarios (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    saldo INTEGER NOT NULL DEFAULT 0 CHECK (saldo >= 0),
    atualizado_em TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_creditos_usuarios_usuario_id
    ON creditos_usuarios (usuario_id);

CREATE TABLE IF NOT EXISTS transacoes_creditos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo VARCHAR(32) NOT NULL,
    quantidade INTEGER NOT NULL,
    saldo_anterior INTEGER NOT NULL,
    saldo_posterior INTEGER NOT NULL,
    descricao TEXT NULL,
    referencia_id VARCHAR(128) NULL,
    chave_idempotencia VARCHAR(128) NULL,
    dados JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em TIMESTAMPTZ NULL,
    CONSTRAINT uq_transacao_credito_idempotencia
        UNIQUE (usuario_id, chave_idempotencia),
    CONSTRAINT ck_transacao_credito_saldos
        CHECK (saldo_anterior >= 0 AND saldo_posterior >= 0)
);

CREATE INDEX IF NOT EXISTS ix_transacoes_creditos_usuario_id
    ON transacoes_creditos (usuario_id);

CREATE INDEX IF NOT EXISTS ix_transacao_credito_usuario_data
    ON transacoes_creditos (usuario_id, criado_em);

CREATE INDEX IF NOT EXISTS ix_transacao_credito_referencia
    ON transacoes_creditos (referencia_id);

ALTER TABLE monitoramentos
    ADD COLUMN IF NOT EXISTS inicio_monitoramento TIMESTAMPTZ NULL;

ALTER TABLE monitoramentos
    ADD COLUMN IF NOT EXISTS fim_monitoramento TIMESTAMPTZ NULL;
"""


def executar() -> None:
    engine = get_engine()

    with engine.begin() as connection:
        connection.execute(text(SQL))

    # Mantém o comportamento existente para bancos recém-criados.
    criar_tabelas()


if __name__ == "__main__":
    executar()
    print("Migração de créditos concluída.")
