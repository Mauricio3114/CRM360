from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from app.models.usuario import Usuario
from app.models.empresa import Empresa

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@usuarios_bp.route("/")
@login_required
def lista():
    if current_user.tipo not in ["admin", "master"]:
        return redirect(url_for("dashboard.home"))

    usuarios = Usuario.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(Usuario.nome.asc()).all()

    empresa = Empresa.query.get(current_user.empresa_id)

    total_usuarios = len(usuarios)
    limite = empresa.limite_usuarios or 0 if empresa else 0

    return render_template(
        "usuarios.html",
        usuarios=usuarios,
        total_usuarios=total_usuarios,
        limite_usuarios=limite
    )


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if current_user.tipo not in ["admin", "master"]:
        return redirect(url_for("dashboard.home"))

    empresa = Empresa.query.get(current_user.empresa_id)

    total_usuarios = Usuario.query.filter_by(
        empresa_id=current_user.empresa_id
    ).count()

    limite = empresa.limite_usuarios or 0 if empresa else 0

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()
        tipo = request.form.get("tipo", "vendedor")

        if not nome or not email or not senha:
            return render_template(
                "usuario_form.html",
                erro="Preencha nome, e-mail e senha."
            )

        usuario_existente = Usuario.query.filter_by(
            email=email
        ).first()

        if usuario_existente:
            return render_template(
                "usuario_form.html",
                erro="Este e-mail já está cadastrado. Use outro e-mail."
            )

        if limite and total_usuarios >= limite:
            usuarios = Usuario.query.filter_by(
                empresa_id=current_user.empresa_id
            ).order_by(Usuario.nome.asc()).all()

            return render_template(
                "usuarios.html",
                usuarios=usuarios,
                total_usuarios=total_usuarios,
                limite_usuarios=limite,
                erro="Seu plano atingiu o limite de usuários. Faça upgrade para adicionar mais."
            )

        usuario = Usuario(
            nome=nome,
            email=email,
            senha=generate_password_hash(senha),
            tipo=tipo,
            empresa_id=current_user.empresa_id
        )

        db.session.add(usuario)
        db.session.commit()

        return redirect(url_for("usuarios.lista"))

    return render_template("usuario_form.html")


@usuarios_bp.route("/<int:usuario_id>/comissao", methods=["POST"])
@login_required
def atualizar_comissao(usuario_id):
    if current_user.tipo not in ["admin", "master"]:
        return redirect(url_for("dashboard.home"))

    usuario = Usuario.query.filter_by(
        id=usuario_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    percentual = request.form.get("percentual", "0")

    try:
        percentual = float(percentual)
    except:
        percentual = 0

    usuario.percentual_comissao = percentual

    db.session.commit()

    return redirect(url_for("usuarios.lista"))