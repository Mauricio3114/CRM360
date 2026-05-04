from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from app.models.tarefa import Tarefa
from app.models.lead import Lead

agenda_bp = Blueprint("agenda", __name__, url_prefix="/agenda")


@agenda_bp.route("/")
@login_required
def index():
    tarefas = Tarefa.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(Tarefa.data_tarefa.asc()).all()

    return render_template("agenda.html", tarefas=tarefas)


@agenda_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    leads = Lead.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(Lead.nome.asc()).all()

    if request.method == "POST":
        data_texto = request.form["data_tarefa"]
        data_tarefa = datetime.strptime(data_texto, "%Y-%m-%dT%H:%M")

        lead_id = request.form.get("lead_id") or None

        enviar_whatsapp = True if request.form.get("enviar_whatsapp") == "on" else False

        tarefa = Tarefa(
            titulo=request.form["titulo"],
            descricao=request.form.get("descricao"),
            tipo=request.form.get("tipo"),
            data_tarefa=data_tarefa,
            lead_id=lead_id,
            empresa_id=current_user.empresa_id,
            enviar_whatsapp=enviar_whatsapp,
            mensagem_whatsapp=request.form.get("mensagem_whatsapp")
        )

        db.session.add(tarefa)
        db.session.commit()

        return redirect(url_for("agenda.index"))

    return render_template("agenda_form.html", leads=leads)


@agenda_bp.route("/concluir/<int:tarefa_id>")
@login_required
def concluir(tarefa_id):
    tarefa = Tarefa.query.filter_by(
        id=tarefa_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    tarefa.status = "concluida"
    db.session.commit()

    return redirect(url_for("agenda.index"))


@agenda_bp.route("/reabrir/<int:tarefa_id>")
@login_required
def reabrir(tarefa_id):
    tarefa = Tarefa.query.filter_by(
        id=tarefa_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    tarefa.status = "pendente"
    db.session.commit()

    return redirect(url_for("agenda.index"))