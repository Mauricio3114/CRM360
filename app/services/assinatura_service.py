from datetime import datetime

from app.models.assinatura import Assinatura


class AssinaturaService:

    @staticmethod
    def assinatura_da_empresa(empresa_id):
        if not empresa_id:
            return None

        return Assinatura.query.filter_by(
            empresa_id=empresa_id
        ).order_by(
            Assinatura.id.desc()
        ).first()

    @staticmethod
    def trial_expirado(assinatura):
        if not assinatura:
            return False

        if assinatura.status == "ativa":
            return False

        if not assinatura.trial_ate:
            return False

        return datetime.utcnow() > assinatura.trial_ate

    @staticmethod
    def dias_restantes_trial(assinatura):
        if not assinatura or not assinatura.trial_ate:
            return 0

        dias = (assinatura.trial_ate - datetime.utcnow()).days

        return max(dias, 0)