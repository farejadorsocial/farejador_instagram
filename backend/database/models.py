from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    criado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    configuracoes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    sessoes: Mapped[list["Sessao"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")
    creditos: Mapped[Optional["CreditoUsuario"]] = relationship(back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    transacoes_creditos: Mapped[list["TransacaoCredito"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")


class Sessao(Base):
    __tablename__ = "sessoes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), ForeignKey("usuarios.username", ondelete="CASCADE"), index=True, nullable=False)
    criada_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_acesso: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expira_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    acesso: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    permissoes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    usuario: Mapped["Usuario"] = relationship(back_populates="sessoes")


class CreditoUsuario(Base):
    __tablename__ = "creditos_usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    saldo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    atualizado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usuario: Mapped["Usuario"] = relationship(back_populates="creditos")


class TransacaoCredito(Base):
    __tablename__ = "transacoes_creditos"
    __table_args__ = (
        Index("ix_transacao_credito_usuario_data", "usuario_id", "criado_em"),
        Index("ix_transacao_credito_referencia", "referencia_id"),
        UniqueConstraint("usuario_id", "chave_idempotencia", name="uq_transacao_credito_idempotencia"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), index=True, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    saldo_anterior: Mapped[int] = mapped_column(Integer, nullable=False)
    saldo_posterior: Mapped[int] = mapped_column(Integer, nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referencia_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    chave_idempotencia: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    dados: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    criado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usuario: Mapped["Usuario"] = relationship(back_populates="transacoes_creditos")


class PerfilSalvo(Base):
    __tablename__ = "perfis_salvos"
    __table_args__ = (UniqueConstraint("cliente_usuario", "instagram_pk", name="uq_perfil_cliente_instagram_pk"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_usuario: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    instagram_pk: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    perfil: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    caminho_historico_salvo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    atualizado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Monitoramento(Base):
    __tablename__ = "monitoramentos"
    __table_args__ = (UniqueConstraint("cliente_usuario", "instagram_pk", name="uq_monitoramento_cliente_instagram_pk"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_usuario: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    instagram_pk: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    monitorando: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    inicio_monitoramento: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fim_monitoramento: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sleep: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    dados: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    atualizado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class HistoricoPerfil(Base):
    __tablename__ = "historico_perfis"
    __table_args__ = (Index("ix_historico_cliente_perfil_data", "cliente_usuario", "instagram_pk", "timestamp_capture"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_usuario: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    instagram_pk: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    timestamp_capture: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    perfil: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    dados: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class FeedItem(Base):
    __tablename__ = "feed_itens"
    __table_args__ = (Index("ix_feed_cliente_data", "cliente_usuario", "timestamp_capture"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_usuario: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    timestamp_capture: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    movimento: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    item: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class Notificacao(Base):
    __tablename__ = "notificacoes"
    __table_args__ = (UniqueConstraint("cliente_usuario", "instagram_pk", name="uq_notificacao_cliente_instagram_pk"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_usuario: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    instagram_pk: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    movimento: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    timestamp_capture: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    icone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    texto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mensagem: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dados: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class Visitante(Base):
    __tablename__ = "visitantes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visitante_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    criado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_acesso: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_acessos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    acesso: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class AtividadeVisitante(Base):
    __tablename__ = "atividades_visitante"
    __table_args__ = (Index("ix_atividade_visitante_data", "visitante_id", "timestamp"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    visitante_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    acesso: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
