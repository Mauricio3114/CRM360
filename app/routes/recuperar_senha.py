from flask import Blueprint
from flask import render_template
from flask import request
from flask import flash
from flask import redirect
from flask import url_for

from werkzeug.security import generate_password_hash

from flask_mail import Message

from app import db
from app import mail

from app.models.usuario import Usuario


recuperar_senha_bp = Blueprint(
    "recuperar_senha",
    __name__,
    url_prefix="/recuperar-senha"
)


@recuperar_senha_bp.route("/", methods=["GET", "POST"])
def recuperar():

    if request.method == "POST":

        email = request.form.get("email")

        usuario = Usuario.query.filter_by(
            email=email
        ).first()

        if not usuario:

            flash(
                "Nenhum usuário encontrado com esse e-mail.",
                "warning"
            )

            return redirect(
                url_for("recuperar_senha.recuperar")
            )

        nova_senha = "123456"

        usuario.senha = generate_password_hash(
            nova_senha
        )

        db.session.commit()

        try:

            msg = Message(
                subject="Recuperação de senha - MaVa CRM",
                recipients=[email]
            )

            msg.body = f"""
Olá, {usuario.nome}

Sua senha foi redefinida com sucesso.

Nova senha temporária:

{nova_senha}

Acesse:
https://www.mavacrm.com.br/login

Recomendamos alterar após login.
"""

            mail.send(msg)

        except Exception as e:
            print(e)

        flash(
            "Nova senha enviada para seu e-mail.",
            "success"
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "recuperar_senha.html"
    )