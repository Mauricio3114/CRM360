from datetime import datetime

from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.models.assinatura import Assinatura
from app.services.asaas_service import AsaasService


assinatura_bp = Blueprint(
    "assinatura",
    __name__,
    url_prefix="/assinatura"
)


@assinatura_bp.route("/")
@login_required
def minha_assinatura():

    assinatura = Assinatura.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(
        Assinatura.id.desc()
    ).first()

    if not assinatura:
        flash("Nenhuma assinatura encontrada.", "warning")
        return redirect(url_for("dashboard.dashboard"))

    hoje = datetime.utcnow()
    dias_restantes = 0

    if assinatura.trial_ate:
        dias_restantes = (assinatura.trial_ate - hoje).days

        if dias_restantes < 0:
            dias_restantes = 0

    return render_template(
        "assinatura/minha_assinatura.html",
        assinatura=assinatura,
        dias_restantes=dias_restantes
    )


@assinatura_bp.route("/assinar")
@login_required
def assinar_agora():

    assinatura = Assinatura.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(
        Assinatura.id.desc()
    ).first()

    if not assinatura:
        flash("Assinatura não encontrada.", "danger")
        return redirect(url_for("assinatura.minha_assinatura"))

    try:
        asaas = AsaasService()

        customer_id = assinatura.asaas_customer_id

        if not customer_id:
            cliente = asaas.criar_cliente(
                nome=f"{assinatura.nome_cliente} - {assinatura.nome_empresa}",
                email=assinatura.email,
                telefone=assinatura.telefone
            )

            customer_id = cliente.get("id")

            if not customer_id:
                flash("Erro ao criar cliente no Asaas.", "danger")
                return redirect(url_for("assinatura.minha_assinatura"))

            assinatura.asaas_customer_id = customer_id
            db.session.commit()

        cobranca = asaas.criar_cobranca(
            customer_id=customer_id,
            valor=assinatura.valor,
            descricao=f"Assinatura MaVa CRM - Plano {assinatura.plano.upper()}"
        )

        payment_id = cobranca.get("id")

        if payment_id:
            assinatura.asaas_payment_id = payment_id
            assinatura.status = "aguardando_pagamento"
            db.session.commit()

        link_pagamento = (
            cobranca.get("invoiceUrl")
            or cobranca.get("bankSlipUrl")
            or cobranca.get("pixTransaction", {}).get("qrCode")
        )

        if link_pagamento:
            return redirect(link_pagamento)

        flash("Não foi possível gerar o link de pagamento.", "warning")

    except Exception as e:
        flash(f"Erro ao gerar pagamento: {e}", "danger")

    return redirect(url_for("assinatura.minha_assinatura"))