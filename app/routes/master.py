from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.lead import Lead
from app.models.lancamento_financeiro import LancamentoFinanceiro
from app.models.mensagem_whatsapp import MensagemWhatsApp
from app.models.assinatura import Assinatura

master_bp = Blueprint("master", __name__, url_prefix="/master")


def somente_master():
    return current_user.is_authenticated and current_user.tipo == "master"


@master_bp.route("/")
@login_required
def index():
    if not somente_master():
        return redirect(url_for("dashboard.home"))

    agora = datetime.utcnow()

    empresas = Empresa.query.order_by(Empresa.nome.asc()).all()

    total_empresas = Empresa.query.count()
    total_usuarios = Usuario.query.count()

    assinaturas_total = Assinatura.query.count()

    assinaturas_pagas = Assinatura.query.filter(
        Assinatura.status.in_(["pago", "ativo", "confirmado", "recebido"])
    ).count()

    assinaturas_aguardando = Assinatura.query.filter(
        Assinatura.status.in_(["aguardando_pagamento", "pendente"])
    ).count()

    trials_ativos = Assinatura.query.filter(
        Assinatura.trial_ate != None,
        Assinatura.trial_ate >= agora,
        Assinatura.status_trial == "ativo"
    ).count()

    trials_vencidos = Assinatura.query.filter(
        Assinatura.trial_ate != None,
        Assinatura.trial_ate < agora
    ).count()

    assinaturas_bloqueadas = Assinatura.query.filter(
        Assinatura.bloqueado_em != None
    ).count()

    receita_mensal_estimada = db.session.query(
        db.func.coalesce(db.func.sum(Assinatura.valor), 0)
    ).filter(
        Assinatura.status.in_(["pago", "ativo", "confirmado", "recebido"])
    ).scalar() or 0

    resumo_saas = {
        "total_empresas": total_empresas,
        "total_usuarios": total_usuarios,
        "assinaturas_total": assinaturas_total,
        "assinaturas_pagas": assinaturas_pagas,
        "assinaturas_aguardando": assinaturas_aguardando,
        "trials_ativos": trials_ativos,
        "trials_vencidos": trials_vencidos,
        "assinaturas_bloqueadas": assinaturas_bloqueadas,
        "receita_mensal_estimada": receita_mensal_estimada,
    }

    cards = []

    for empresa in empresas:
        total_usuarios_empresa = Usuario.query.filter_by(
            empresa_id=empresa.id
        ).count()

        total_leads = Lead.query.filter_by(
            empresa_id=empresa.id
        ).count()

        entradas = LancamentoFinanceiro.query.filter_by(
            empresa_id=empresa.id,
            tipo="entrada"
        ).all()

        receita = sum(item.valor for item in entradas)

        mensagens_nao_lidas = MensagemWhatsApp.query.filter_by(
            empresa_id=empresa.id,
            direcao="recebida",
            lida=False
        ).count()

        assinatura = Assinatura.query.filter_by(
            empresa_id=empresa.id
        ).order_by(
            Assinatura.criado_em.desc()
        ).first()

        status_assinatura = "sem_assinatura"
        dias_trial = None

        if assinatura:
            status_assinatura = assinatura.status

            if assinatura.trial_ate:
                diferenca = assinatura.trial_ate - agora
                dias_trial = max(diferenca.days, 0)

        cards.append({
            "empresa": empresa,
            "total_usuarios": total_usuarios_empresa,
            "total_leads": total_leads,
            "receita": receita,
            "mensagens_nao_lidas": mensagens_nao_lidas,
            "assinatura": assinatura,
            "status_assinatura": status_assinatura,
            "dias_trial": dias_trial,
        })

    return render_template(
        "master_dashboard.html",
        cards=cards,
        resumo_saas=resumo_saas
    )


@master_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova_empresa():
    if not somente_master():
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        nome_empresa = request.form["nome_empresa"].strip()
        plano = request.form.get("plano", "basico")
        limite_usuarios = int(request.form.get("limite_usuarios") or 3)

        nome_admin = request.form["nome_admin"].strip()
        email_admin = request.form["email_admin"].strip().lower()
        senha_admin = generate_password_hash(request.form["senha_admin"])

        existe = Usuario.query.filter_by(email=email_admin).first()
        if existe:
            return render_template(
                "master_empresa_form.html",
                erro="Já existe usuário com esse e-mail."
            )

        empresa = Empresa(
            nome=nome_empresa,
            plano=plano,
            limite_usuarios=limite_usuarios
        )

        db.session.add(empresa)
        db.session.flush()

        usuario = Usuario(
            nome=nome_admin,
            email=email_admin,
            senha=senha_admin,
            tipo="admin",
            empresa_id=empresa.id,
            percentual_comissao=0
        )

        db.session.add(usuario)
        db.session.commit()

        return redirect(url_for("master.index"))

    return render_template("master_empresa_form.html")


@master_bp.route("/entrar/<int:empresa_id>")
@login_required
def entrar_empresa(empresa_id):
    if not somente_master():
        return redirect(url_for("dashboard.home"))

    empresa = Empresa.query.get_or_404(empresa_id)

    current_user.empresa_id = empresa.id
    db.session.commit()

    return redirect(url_for("dashboard.home"))