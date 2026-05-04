from app import db
from datetime import datetime

class MensagemWhatsApp(db.Model):
    __tablename__ = "mensagens_whatsapp"

    id = db.Column(db.Integer, primary_key=True)

    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey("leads.id"), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    telefone = db.Column(db.String(30), nullable=False)
    nome_contato = db.Column(db.String(150), nullable=True)

    direcao = db.Column(db.String(20), nullable=False)
    mensagem = db.Column(db.Text, nullable=True)

    tipo_mensagem = db.Column(db.String(30), default="texto")
    media_id = db.Column(db.String(255), nullable=True)
    media_url = db.Column(db.String(500), nullable=True)
    media_mime_type = db.Column(db.String(100), nullable=True)
    media_filename = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(30), default="recebida")
    lida = db.Column(db.Boolean, default=False)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    lead = db.relationship("Lead", backref="mensagens_whatsapp")
    usuario = db.relationship("Usuario", backref="mensagens_whatsapp")