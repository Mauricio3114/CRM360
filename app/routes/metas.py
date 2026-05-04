from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user

from app import db
from app.models.meta import Meta
from app.models.lancamento_financeiro import LancamentoFinanceiro

# 👇 ISSO TEM QUE EXISTIR EXATAMENTE ASSIM
metas_bp = Blueprint("metas", __name__, url_prefix="/metas")


@metas_bp.route("/")
@login_required
def index():
    metas = Meta.query.filter_by(
        empresa_id=current_user.empresa_id
    ).all()

    lancamentos = LancamentoFinanceiro.query.filter_by(
        empresa_id=current_user.empresa_id,
        tipo="entrada"
    ).all()

    total_entradas = sum(l.valor for l in lancamentos)

    metas_calculadas = []

    for meta in metas:
        progresso = (total_entradas / meta.valor_meta * 100) if meta.valor_meta > 0 else 0

        metas_calculadas.append({
            "meta": meta,
            "realizado": total_entradas,
            "progresso": progresso
        })

    return render_template("metas.html", metas=metas_calculadas)


@metas_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    if request.method == "POST":
        meta = Meta(
            nome=request.form["nome"],
            valor_meta=float(request.form["valor"]),
            empresa_id=current_user.empresa_id
        )

        db.session.add(meta)
        db.session.commit()

        return redirect(url_for("metas.index"))

    return render_template("meta_form.html")