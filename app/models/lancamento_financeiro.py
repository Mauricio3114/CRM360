from app import db
from datetime import datetime

class LancamentoFinanceiro(db.Model):
    __tablename__ = "lancamentos_financeiros"

    id = db.Column(db.Integer, primary_key=True)

    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)  # entrada ou saida
    categoria = db.Column(db.String(100))
    valor = db.Column(db.Float, nullable=False, default=0.0)
    data_lancamento = db.Column(db.DateTime, default=datetime.utcnow)

    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"))
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    lead = db.relationship("Lead", backref="lancamentos_financeiros")