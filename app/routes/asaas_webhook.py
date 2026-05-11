import secrets
import string

from flask import Blueprint, request

from flask_mail import Message

from app import db, mail
from app.models.assinatura import Assinatura


asaas_webhook_bp = Blueprint(
    "asaas_webhook",
    __name__,
    url_prefix="/webhook"
)


def gerar_senha_temporaria(tamanho=10):
    caracteres = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(caracteres)
        for _ in range(tamanho)
    )


@asaas_webhook_bp.route("/asaas", methods=["POST"])
def webhook_asaas():

    payload = request.get_json(silent=True) or {}

    evento = payload.get("event")
    pagamento = payload.get("payment", {})

    payment_id = pagamento.get("id")
    customer_id = pagamento.get("customer")

    eventos_confirmados = [
        "PAYMENT_CONFIRMED",
        "PAYMENT_RECEIVED"
    ]

    if evento not in eventos_confirmados:
        return {
            "ok": True,
            "ignorado": evento
        }, 200

    assinatura = None

    if payment_id:
        assinatura = Assinatura.query.filter_by(
            asaas_payment_id=payment_id
        ).first()

    if not assinatura and customer_id:
        assinatura = Assinatura.query.filter_by(
            asaas_customer_id=customer_id
        ).order_by(
            Assinatura.id.desc()
        ).first()

    if not assinatura:
        return {
            "ok": False,
            "erro": "Assinatura não encontrada"
        }, 404

    # =========================================
    # 🔥 NOVO FLUXO
    # NÃO CRIA EMPRESA/USUÁRIO NOVAMENTE
    # =========================================

    assinatura.status = "ativa"
    assinatura.status_trial = "encerrado"

    db.session.commit()

    try:

        msg = Message(
            subject="Pagamento confirmado - MaVa CRM",
            recipients=[assinatura.email]
        )

        msg.body = f"""
Olá, {assinatura.nome_cliente}!

Recebemos o pagamento da sua assinatura do MaVa CRM 🚀

Seu acesso permanece liberado normalmente.

Plano:
{assinatura.plano.upper()}

Obrigado por confiar no MaVa CRM.
"""

        mail.send(msg)

        print("EMAIL DE PAGAMENTO ENVIADO")

    except Exception as e:
        print("ERRO AO ENVIAR EMAIL:", e)

    print("=" * 60)
    print("ASSINATURA ATIVADA")
    print("Cliente:", assinatura.nome_cliente)
    print("Empresa:", assinatura.nome_empresa)
    print("Plano:", assinatura.plano)
    print("=" * 60)

    return {
        "ok": True,
        "assinatura_id": assinatura.id,
        "status": assinatura.status
    }, 200