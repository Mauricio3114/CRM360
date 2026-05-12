from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from app.models.pipeline import Pipeline
from app.models.lead import Lead
from app.models.usuario import Usuario
from app.models.historico_etapa_lead import HistoricoEtapaLead

pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/pipeline")


def criar_pipeline_padrao():
    etapas = [
        ("Entrada WhatsApp", 0),
        ("Novo Lead", 1),
        ("Contato Feito", 2),
        ("Proposta", 3),
        ("Negociação", 4),
        ("Fechado", 5),
        ("Perdido", 6),
    ]

    for nome, ordem in etapas:
        existe = Pipeline.query.filter_by(
            nome=nome,
            empresa_id=current_user.empresa_id
        ).first()

        if not existe:
            etapa = Pipeline(
                nome=nome,
                ordem=ordem,
                empresa_id=current_user.empresa_id
            )
            db.session.add(etapa)

    db.session.commit()


@pipeline_bp.route("/")
@login_required
def index():
    criar_pipeline_padrao()

    is_admin = current_user.tipo in ["admin", "master"]

    tag_filtro = request.args.get("tag", "").strip()

    origem_filtro = request.args.get("origem", "").strip()

    if is_admin:

        vendedor_id = request.args.get("vendedor_id")

        if vendedor_id and vendedor_id != "todos":
            vendedor_id = int(vendedor_id)
        else:
            vendedor_id = None

    else:

        vendedor_id = current_user.id

    etapas = Pipeline.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(Pipeline.ordem.asc()).all()

    usuarios = Usuario.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(Usuario.nome.asc()).all()

    for etapa in etapas:
        query = Lead.query.filter_by(
            empresa_id=current_user.empresa_id,
            pipeline_id=etapa.id
        )

        if vendedor_id:
            query = query.filter_by(usuario_id=vendedor_id)

        if tag_filtro:

            query = query.filter(
                Lead.tags.like(f"%{tag_filtro}%")
            )

        if origem_filtro:

            query = query.filter_by(
                origem=origem_filtro
            )

        etapa.leads = query.order_by(
            Lead.etapa_atualizada_em.desc()
        ).all()

    return render_template(
        "pipeline.html",
        etapas=etapas,
        usuarios=usuarios,
        vendedor_id=vendedor_id if vendedor_id else "todos",
        is_admin=is_admin
    )


@pipeline_bp.route("/nova-coluna", methods=["POST"])
@login_required
def nova_coluna():

    nome = request.form.get("nome")

    if not nome:
        flash("Informe o nome da coluna.", "warning")
        return redirect(url_for("pipeline.index"))

    ultima = Pipeline.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(Pipeline.ordem.desc()).first()

    ordem = 1

    if ultima:
        ordem = ultima.ordem + 1

    pipeline = Pipeline(
        nome=nome,
        ordem=ordem,
        empresa_id=current_user.empresa_id
    )

    db.session.add(pipeline)
    db.session.commit()

    flash("Nova coluna criada.", "success")

    return redirect(url_for("pipeline.index"))


@pipeline_bp.route("/renomear/<int:pipeline_id>", methods=["POST"])
@login_required
def renomear_coluna(pipeline_id):

    pipeline = Pipeline.query.filter_by(
        id=pipeline_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    nome = request.form.get("nome")

    if nome:
        pipeline.nome = nome
        db.session.commit()

        flash("Coluna renomeada.", "success")

    return redirect(url_for("pipeline.index"))


@pipeline_bp.route("/subir/<int:pipeline_id>")
@login_required
def subir_coluna(pipeline_id):

    pipeline = Pipeline.query.filter_by(
        id=pipeline_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    anterior = Pipeline.query.filter(
        Pipeline.empresa_id == current_user.empresa_id,
        Pipeline.ordem < pipeline.ordem
    ).order_by(Pipeline.ordem.desc()).first()

    if anterior:
        ordem_atual = pipeline.ordem

        pipeline.ordem = anterior.ordem
        anterior.ordem = ordem_atual

        db.session.commit()

    return redirect(url_for("pipeline.index"))


@pipeline_bp.route("/descer/<int:pipeline_id>")
@login_required
def descer_coluna(pipeline_id):

    pipeline = Pipeline.query.filter_by(
        id=pipeline_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    proxima = Pipeline.query.filter(
        Pipeline.empresa_id == current_user.empresa_id,
        Pipeline.ordem > pipeline.ordem
    ).order_by(Pipeline.ordem.asc()).first()

    if proxima:
        ordem_atual = pipeline.ordem

        pipeline.ordem = proxima.ordem
        proxima.ordem = ordem_atual

        db.session.commit()

    return redirect(url_for("pipeline.index"))


@pipeline_bp.route("/mover/<int:lead_id>/<int:pipeline_id>")
@login_required
def mover(lead_id, pipeline_id):

    lead = Lead.query.filter_by(
        id=lead_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    if current_user.tipo not in ["admin", "master"]:
        if lead.usuario_id != current_user.id:
            return redirect(url_for("pipeline.index"))

    etapa = Pipeline.query.filter_by(
        id=pipeline_id,
        empresa_id=current_user.empresa_id
    ).first_or_404()

    if lead.pipeline_id != etapa.id:

        historico_aberto = HistoricoEtapaLead.query.filter_by(
            lead_id=lead.id,
            saiu_em=None
        ).first()

        if historico_aberto:
            historico_aberto.saiu_em = datetime.utcnow()

            historico_aberto.tempo_segundos = int(
                (
                    historico_aberto.saiu_em
                    - historico_aberto.entrou_em
                ).total_seconds()
            )

        novo_historico = HistoricoEtapaLead(
            lead_id=lead.id,
            pipeline_id=etapa.id,
            entrou_em=datetime.utcnow(),
            empresa_id=current_user.empresa_id
        )

        db.session.add(novo_historico)

        lead.pipeline_id = etapa.id
        lead.etapa_atualizada_em = datetime.utcnow()

        db.session.commit()

    return redirect(url_for("pipeline.index"))


@pipeline_bp.route("/mover-ajax", methods=["POST"])
@login_required
def mover_ajax():

    dados = request.get_json()

    lead_id = dados.get("lead_id")
    pipeline_id = dados.get("pipeline_id")

    lead = Lead.query.filter_by(
        id=lead_id,
        empresa_id=current_user.empresa_id
    ).first()

    if not lead:
        return jsonify({"sucesso": False})

    etapa = Pipeline.query.filter_by(
        id=pipeline_id,
        empresa_id=current_user.empresa_id
    ).first()

    if not etapa:
        return jsonify({"sucesso": False})

    if lead.pipeline_id != etapa.id:

        historico_aberto = HistoricoEtapaLead.query.filter_by(
            lead_id=lead.id,
            saiu_em=None
        ).first()

        if historico_aberto:
            historico_aberto.saiu_em = datetime.utcnow()

            historico_aberto.tempo_segundos = int(
                (
                    historico_aberto.saiu_em
                    - historico_aberto.entrou_em
                ).total_seconds()
            )

        novo_historico = HistoricoEtapaLead(
            lead_id=lead.id,
            pipeline_id=etapa.id,
            entrou_em=datetime.utcnow(),
            empresa_id=current_user.empresa_id
        )

        db.session.add(novo_historico)

        lead.pipeline_id = etapa.id
        lead.etapa_atualizada_em = datetime.utcnow()

        db.session.commit()

    return jsonify({"sucesso": True})