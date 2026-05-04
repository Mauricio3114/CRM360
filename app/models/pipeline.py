from app import db

class Pipeline(db.Model):
    __tablename__ = "pipelines"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ordem = db.Column(db.Integer, nullable=False)

    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"))

    leads = db.relationship("Lead", backref="pipeline", lazy=True)