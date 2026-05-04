from app import db, login_manager
from flask_login import UserMixin


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)

    tipo = db.Column(db.String(50), default="vendedor")

    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"))

    # comissão (%)
    percentual_comissao = db.Column(db.Float, default=0.0)


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))