import secrets
import string

from flask import Blueprint, request

from flask_mail import Message
from werkzeug.security import generate_password_hash

from app import db, mail
from app.models.assinatura import Assinatura
from app.models.empresa import Empresa
from app.models.usuario import Usuario


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
            asaas_customer_id=customer_id,
            status="aguardando_pagamento"
        ).first()

    if not assinatura:
        return {
            "ok": False,
            "erro": "Assinatura não encontrada"
        }, 404

    if assinatura.status == "ativa":
        return {
            "ok": True,
            "msg": "Assinatura já ativa"
        }, 200

    empresa = Empresa(
        nome=assinatura.nome_empresa,
        status="ativa"
    )

    db.session.add(empresa)
    db.session.flush()

    senha_temporaria = gerar_senha_temporaria()

    usuario = Usuario(
        nome=assinatura.nome_cliente,
        email=assinatura.email,
        senha=generate_password_hash(senha_temporaria),
        tipo="admin",
        empresa_id=empresa.id
    )

    db.session.add(usuario)
    db.session.flush()

    assinatura.empresa_id = empresa.id
    assinatura.usuario_id = usuario.id
    assinatura.status = "ativa"

    db.session.commit()

    try:

        msg = Message(
            subject="Seu acesso ao MaVa CRM",
            recipients=[usuario.email]
        )

        msg.body = f"""
Olá, {usuario.nome}!

Seu acesso ao MaVa CRM foi liberado com sucesso 🚀

Dados de acesso:

Link:
https://mavacrm.com.br/login

E-mail:
{usuario.email}

Senha temporária:
{senha_temporaria}

Recomendamos alterar sua senha após o primeiro acesso.

Bem-vindo ao MaVa CRM.
"""

        mail.send(msg)

        print("EMAIL ENVIADO COM SUCESSO")

    except Exception as e:
        print("ERRO AO ENVIAR EMAIL:", e)

    print("=" * 60)
    print("NOVO CLIENTE MaVa CRM ATIVADO")
    print("Empresa:", empresa.nome)
    print("Nome:", usuario.nome)
    print("Email:", usuario.email)
    print("Senha temporária:", senha_temporaria)
    print("=" * 60)

    return {
        "ok": True,
        "empresa_id": empresa.id,
        "usuario_id": usuario.id,
        "email": usuario.email
    }, 200