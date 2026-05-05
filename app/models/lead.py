from app import db
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Fortaleza")


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)

    nome = db.Column(db.String(150), nullable=False)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(150))

    instagram = db.Column(db.String(150))
    instagram_id = db.Column(db.String(200))

    valor = db.Column(db.Float, default=0.0)
    plano = db.Column(db.String(100))
    status = db.Column(db.String(30), default="aberto")

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔥 quando entrou/mudou para a etapa atual
    etapa_atualizada_em = db.Column(db.DateTime, default=datetime.utcnow)

    origem = db.Column(db.String(100))
    produto_interesse = db.Column(db.String(150))

    pipeline_id = db.Column(db.Integer, db.ForeignKey("pipelines.id"))
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresas.id"))

    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    usuario = db.relationship("Usuario", backref="leads")

    @property
    def tempo_na_etapa_texto(self):
        inicio = self.etapa_atualizada_em or self.criado_em

        if not inicio:
            return "Sem registro"

        agora = datetime.now()

        if inicio.tzinfo is not None:
            inicio = inicio.replace(tzinfo=None)

        diferenca = agora - inicio

        dias = diferenca.days
        horas = diferenca.seconds // 3600
        minutos = (diferenca.seconds % 3600) // 60

        if dias >= 30:
            return "30+ dias nesta etapa"

        if dias > 0:
            return f"{dias} dia(s) nesta etapa"

        if horas > 0:
            return f"{horas}h nesta etapa"

        return f"{minutos}min nesta etapa"