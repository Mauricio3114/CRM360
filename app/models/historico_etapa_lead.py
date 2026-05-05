from app import db
from datetime import datetime


class HistoricoEtapaLead(db.Model):
    __tablename__ = "historico_etapas_lead"

    id = db.Column(db.Integer, primary_key=True)

    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"))
    pipeline_id = db.Column(db.Integer, db.ForeignKey("pipelines.id"))

    entrou_em = db.Column(db.DateTime, default=datetime.utcnow)
    saiu_em = db.Column(db.DateTime)

    tempo_segundos = db.Column(db.Integer)

    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"))

    lead = db.relationship("Lead", backref="historico_etapas")
    pipeline = db.relationship("Pipeline")