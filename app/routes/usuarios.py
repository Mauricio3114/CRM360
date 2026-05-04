from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user

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
    limite = empresa.limite_usuarios or 0

    return render_template(
        "usuarios.html",
        usuarios=usuarios,
        total_usuarios=total_usuarios,
        limite_usuarios=limite
    )


# 🔥 CRIAR NOVO USUÁRIO COM TRAVA DE PLANO
@usuarios_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if current_user.tipo not in ["admin", "master"]:
        return redirect(url_for("dashboard.home"))

    empresa = Empresa.query.get(current_user.empresa_id)

    total_usuarios = Usuario.query.filter_by(
        empresa_id=current_user.empresa_id
    ).count()

    limite = empresa.limite_usuarios or 0

    # 🔒 BLOQUEIO DO PLANO
    if total_usuarios >= limite:
        usuarios = Usuario.query.filter_by(
            empresa_id=current_user.empresa_id
        ).all()

        return render_template(
            "usuarios.html",
            usuarios=usuarios,
            total_usuarios=total_usuarios,
            limite_usuarios=limite,
            erro="Seu plano atingiu o limite de usuários. Faça upgrade para adicionar mais."
        )

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]
        tipo = request.form.get("tipo", "vendedor")

        usuario = Usuario(
            nome=nome,
            email=email,
            senha=senha,
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