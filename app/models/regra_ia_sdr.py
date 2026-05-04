from app import db
from datetime import datetime

class RegraIASDR(db.Model):
    __tablename__ = "regras_ia_sdr"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(150), nullable=False)
    palavras_chave = db.Column(db.Text, nullable=False)
    resposta = db.Column(db.Text, nullable=False)

    etapa_pipeline = db.Column(db.String(100))
    criar_tarefa = db.Column(db.Boolean, default=False)
    titulo_tarefa = db.Column(db.String(150))
    tipo_tarefa = db.Column(db.String(50), default="Follow-up")
    horas_para_tarefa = db.Column(db.Integer, default=24)

    ativo = db.Column(db.Boolean, default=True)

    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)