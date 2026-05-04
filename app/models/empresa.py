from app import db

class Empresa(db.Model):
    __tablename__ = "empresas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    logo = db.Column(db.String(200))
    plano = db.Column(db.String(50), default="basico")
    limite_usuarios = db.Column(db.Integer, default=3)

    # WhatsApp API Meta - preencher depois
    whatsapp_token = db.Column(db.Text, nullable=True)
    whatsapp_phone_number_id = db.Column(db.String(100), nullable=True)
    whatsapp_business_id = db.Column(db.String(100), nullable=True)
    whatsapp_ativo = db.Column(db.Boolean, default=False)

    usuarios = db.relationship("Usuario", backref="empresa", lazy=True)