from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from app.models.lancamento_financeiro import LancamentoFinanceiro
from app.models.lead import Lead

financeiro_bp = Blueprint("financeiro", __name__, url_prefix="/financeiro")


CATEGORIAS_FINANCEIRAS = [
    "Venda",
    "Comissão",
    "Marketing",
    "Operacional",
    "Pessoal",
    "Estrutura",
    "Impostos",
    "Ferramentas",
    "Outros",
]


def somente_admin_master():
    return current_user.tipo in ["admin", "master"]


@financeiro_bp.route("/")
@login_required
def index():

    if not somente_admin_master():
        return redirect(url_for("dashboard.home"))

    data_inicio = request.args.get("data_inicio")
    data_fim = request.args.get("data_fim")
    categoria = request.args.get("categoria")
    tipo = request.args.get("tipo")

    query = LancamentoFinanceiro.query.filter_by(
        empresa_id=current_user.empresa_id
    )

    if data_inicio:
        inicio = datetime.strptime(data_inicio, "%Y-%m-%d")
        query = query.filter(LancamentoFinanceiro.data_lancamento >= inicio)

    if data_fim:
        fim = datetime.strptime(data_fim, "%Y-%m-%d")
        query = query.filter(LancamentoFinanceiro.data_lancamento <= fim)

    if categoria:
        query = query.filter(LancamentoFinanceiro.categoria == categoria)

    if tipo:
        query = query.filter(LancamentoFinanceiro.tipo == tipo)

    lancamentos = query.order_by(
        LancamentoFinanceiro.data_lancamento.desc()
    ).all()

    total_entradas = sum(l.valor for l in lancamentos if l.tipo == "entrada")
    total_saidas = sum(l.valor for l in lancamentos if l.tipo == "saida")
    lucro = total_entradas - total_saidas

    total_por_categoria = {}

    for item in lancamentos:
        nome_categoria = item.categoria or "Sem categoria"
        total_por_categoria[nome_categoria] = total_por_categoria.get(nome_categoria, 0) + item.valor

    return render_template(
        "financeiro.html",
        lancamentos=lancamentos,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
        lucro=lucro,
        categorias=CATEGORIAS_FINANCEIRAS,
        total_por_categoria=total_por_categoria,
        filtro_data_inicio=data_inicio or "",
        filtro_data_fim=data_fim or "",
        filtro_categoria=categoria or "",
        filtro_tipo=tipo or ""
    )


@financeiro_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():

    if not somente_admin_master():
        return redirect(url_for("dashboard.home"))

    leads = Lead.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(Lead.nome.asc()).all()

    if request.method == "POST":
        data_texto = request.form.get("data_lancamento")

        if data_texto:
            data_lancamento = datetime.strptime(data_texto, "%Y-%m-%d")
        else:
            data_lancamento = datetime.utcnow()

        lead_id = request.form.get("lead_id") or None
        valor = request.form["valor"].replace(",", ".")

        lancamento = LancamentoFinanceiro(
            descricao=request.form["descricao"],
            tipo=request.form["tipo"],
            categoria=request.form.get("categoria"),
            valor=float(valor),
            data_lancamento=data_lancamento,
            lead_id=lead_id,
            empresa_id=current_user.empresa_id
        )

        db.session.add(lancamento)
        db.session.commit()

        return redirect(url_for("financeiro.index"))

    return render_template(
        "financeiro_form.html",
        leads=leads,
        categorias=CATEGORIAS_FINANCEIRAS
    )