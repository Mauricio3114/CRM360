from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.empresa import Empresa

config_bp = Blueprint("config", __name__, url_prefix="/config")

@config_bp.route("/whatsapp", methods=["GET", "POST"])
@login_required
def whatsapp():
    empresa = Empresa.query.get(current_user.empresa_id)

    if request.method == "POST":
        empresa.whatsapp_token = request.form.get("token")
        empresa.whatsapp_phone_number_id = request.form.get("phone_id")
        empresa.whatsapp_business_id = request.form.get("business_id")
        empresa.whatsapp_ativo = True if request.form.get("ativo") == "on" else False

        db.session.commit()

        return redirect(url_for("config.whatsapp"))

    return render_template("config_whatsapp.html", empresa=empresa)


@config_bp.route("/empresa", methods=["GET", "POST"])
@login_required
def empresa():
    empresa = Empresa.query.get(current_user.empresa_id)

    if request.method == "POST":
        empresa.nome = request.form.get("nome")
        empresa.logo = request.form.get("logo")
        empresa.plano = request.form.get("plano")
        empresa.limite_usuarios = int(request.form.get("limite_usuarios") or 3)

        db.session.commit()

        return redirect(url_for("config.empresa"))

    return render_template("config_empresa.html", empresa=empresa)