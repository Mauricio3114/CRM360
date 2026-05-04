from app import db

class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(150), nullable=False)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(150))

    origem = db.Column(db.String(100))
    produto_interesse = db.Column(db.String(150))

    pipeline_id = db.Column(db.Integer, db.ForeignKey("pipelines.id"))
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"))

    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    usuario = db.relationship("Usuario", backref="leads")