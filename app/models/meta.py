from app import db
from datetime import datetime

class Meta(db.Model):
    __tablename__ = "metas"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(150), nullable=False)
    valor_meta = db.Column(db.Float, nullable=False, default=0.0)

    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)