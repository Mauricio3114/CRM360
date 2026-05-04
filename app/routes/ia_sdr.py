from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.models.regra_ia_sdr import RegraIASDR

ia_sdr_bp = Blueprint("ia_sdr", __name__, url_prefix="/ia-sdr")


@ia_sdr_bp.route("/")
@login_required
def index():
    regras = RegraIASDR.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(RegraIASDR.id.desc()).all()

    return render_template("ia_sdr_regras.html", regras=regras)


@ia_sdr_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    if request.method == "POST":
        regra = RegraIASDR(
            nome=request.form["nome"],
            palavras_chave=request.form["palavras_chave"],
            resposta=request.form["resposta"],
            etapa_pipeline=request.form.get("etapa_pipeline") or None,
            criar_tarefa=True if request.form.get("criar_tarefa") == "on" else False,
            titulo_tarefa=request.form.get("titulo_tarefa"),
            tipo_tarefa=request.form.get("tipo_tarefa"),
            horas_para_tarefa=int(request.form.get("horas_para_tarefa") or 24),
            empresa_id=current_user.empresa_id
        )

        db.session.add(regra)
        db.session.commit()

        return redirect(url_for("ia_sdr.index"))

    return render_template("ia_sdr_form.html", regra=None)


@ia_sdr_bp.route("/editar/<int:regra_id>", methods=["GET", "POST"])
@login_required
def editar(regra_id):
    regra = RegraIASDR.query.filter_by(
        id=regra_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    if request.method == "POST":
        regra.nome = request.form["nome"]
        regra.palavras_chave = request.form["palavras_chave"]
        regra.resposta = request.form["resposta"]
        regra.etapa_pipeline = request.form.get("etapa_pipeline") or None
        regra.criar_tarefa = True if request.form.get("criar_tarefa") == "on" else False
        regra.titulo_tarefa = request.form.get("titulo_tarefa")
        regra.tipo_tarefa = request.form.get("tipo_tarefa")
        regra.horas_para_tarefa = int(request.form.get("horas_para_tarefa") or 24)

        db.session.commit()

        return redirect(url_for("ia_sdr.index"))

    return render_template("ia_sdr_form.html", regra=regra)


@ia_sdr_bp.route("/status/<int:regra_id>")
@login_required
def status(regra_id):
    regra = RegraIASDR.query.filter_by(
        id=regra_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    regra.ativo = not regra.ativo
    db.session.commit()

    return redirect(url_for("ia_sdr.index"))