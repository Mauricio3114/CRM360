from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.lead import Lead
from app.models.lancamento_financeiro import LancamentoFinanceiro
from app.models.mensagem_whatsapp import MensagemWhatsApp

master_bp = Blueprint("master", __name__, url_prefix="/master")


def somente_master():
    return current_user.is_authenticated and current_user.tipo == "master"


@master_bp.route("/")
@login_required
def index():
    if not somente_master():
        return redirect(url_for("dashboard.home"))

    empresas = Empresa.query.order_by(Empresa.nome.asc()).all()

    cards = []

    for empresa in empresas:
        total_usuarios = Usuario.query.filter_by(empresa_id=empresa.id).count()
        total_leads = Lead.query.filter_by(empresa_id=empresa.id).count()

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

        cards.append({
            "empresa": empresa,
            "total_usuarios": total_usuarios,
            "total_leads": total_leads,
            "receita": receita,
            "mensagens_nao_lidas": mensagens_nao_lidas
        })

    return render_template("master_dashboard.html", cards=cards)


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