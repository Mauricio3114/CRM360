from datetime import datetime
from app import db


class Assinatura(db.Model):
    __tablename__ = "assinaturas"

    id = db.Column(db.Integer, primary_key=True)

    empresa_id = db.Column(
        db.Integer,
        db.ForeignKey("empresas.id"),
        nullable=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=True
    )

    nome_cliente = db.Column(
        db.String(150),
        nullable=False
    )

    nome_empresa = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        nullable=False
    )

    telefone = db.Column(
        db.String(30),
        nullable=True
    )

    plano = db.Column(
        db.String(50),
        nullable=False
    )

    valor = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    asaas_customer_id = db.Column(
        db.String(100),
        nullable=True
    )

    asaas_payment_id = db.Column(
        db.String(100),
        nullable=True
    )

    status = db.Column(
        db.String(50),
        nullable=False,
        default="aguardando_pagamento"
    )

    origem = db.Column(
        db.String(50),
        nullable=True,
        default="contratacao_online"
    )

    trial_ate = db.Column(
        db.DateTime,
        nullable=True
    )

    status_trial = db.Column(
        db.String(30),
        default="ativo"
    )

    data_vencimento = db.Column(
        db.DateTime,
        nullable=True
    )

    bloqueado_em = db.Column(
        db.DateTime,
        nullable=True
    )

    criado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )