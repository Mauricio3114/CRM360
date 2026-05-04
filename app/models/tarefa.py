from app import db
from datetime import datetime

class Tarefa(db.Model):
    __tablename__ = "tarefas"

    id = db.Column(db.Integer, primary_key=True)

    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text)
    data_tarefa = db.Column(db.DateTime, nullable=False)

    status = db.Column(db.String(30), default="pendente")
    tipo = db.Column(db.String(50), default="Follow-up")

    enviar_whatsapp = db.Column(db.Boolean, default=False)
    mensagem_whatsapp = db.Column(db.Text)

    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"))
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    lead = db.relationship("Lead", backref="tarefas")
    usuario = db.relationship("Usuario", backref="tarefas")