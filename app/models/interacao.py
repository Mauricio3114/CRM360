from app import db
from datetime import datetime

class Interacao(db.Model):
    __tablename__ = "interacoes"

    id = db.Column(db.Integer, primary_key=True)

    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    tipo = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.Text, nullable=False)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    lead = db.relationship("Lead", backref="interacoes")
    usuario = db.relationship("Usuario", backref="interacoes")