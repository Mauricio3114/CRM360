from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user

from app import db
from app.models.usuario import Usuario
from app.models.empresa import Empresa
from app.services.assinatura_service import AssinaturaService

from werkzeug.security import generate_password_hash, check_password_hash


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        user = Usuario.query.filter_by(email=email).first()

        if user and check_password_hash(user.senha, senha):

            login_user(user)

            if user.empresa_id:

                assinatura = AssinaturaService.assinatura_da_empresa(
                    user.empresa_id
                )

                if AssinaturaService.trial_expirado(assinatura):

                    flash(
                        "Seu teste grátis expirou. Regularize sua assinatura para continuar.",
                        "warning"
                    )

                    return redirect(
                        url_for("assinatura.minha_assinatura")
                    )

            return redirect(url_for("dashboard.home"))

        flash("Login inválido")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome_empresa = request.form["nome_empresa"].strip()
        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = generate_password_hash(request.form["senha"])

        usuario_existente = Usuario.query.filter_by(email=email).first()

        if usuario_existente:
            flash("Já existe um usuário com esse e-mail.")
            return redirect(url_for("auth.register"))

        empresa = Empresa(
            nome=nome_empresa,
            plano="basico",
            limite_usuarios=3
        )

        db.session.add(empresa)
        db.session.flush()

        user = Usuario(
            nome=nome,
            email=email,
            senha=senha,
            tipo="admin",
            empresa_id=empresa.id,
            percentual_comissao=0
        )

        db.session.add(user)
        db.session.commit()

        flash("Empresa e usuário administrador criados com sucesso.")
        return redirect(url_for("auth.login"))

    return render_template("register.html")