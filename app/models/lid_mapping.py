from datetime import datetime
from app import db


class LidMapping(db.Model):
    __tablename__ = "lid_mappings"

    id = db.Column(db.Integer, primary_key=True)

    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=True)

    instance_name = db.Column(db.String(100), nullable=False, default="mava_empresa_teste_3")

    lid_jid = db.Column(db.String(150), nullable=False, index=True)
    numero_real = db.Column(db.String(30), nullable=False)

    nome_contato = db.Column(db.String(150), nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )