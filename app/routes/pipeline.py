from flask import Blueprint, render_template, redirect, url_for, request, jsonify
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
        if vendedor_id:
            etapa.leads = Lead.query.filter_by(
                empresa_id=current_user.empresa_id,
                pipeline_id=etapa.id,
                usuario_id=vendedor_id
            ).order_by(Lead.etapa_atualizada_em.asc()).all()
        else:
            etapa.leads = Lead.query.filter_by(
                empresa_id=current_user.empresa_id,
                pipeline_id=etapa.id
            ).order_by(Lead.etapa_atualizada_em.asc()).all()

    return render_template(
        "pipeline.html",
        etapas=etapas,
        usuarios=usuarios,
        vendedor_id=vendedor_id if vendedor_id else "todos",
        is_admin=is_admin
    )


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

        # 🔴 FINALIZA ETAPA ANTIGA
        historico_aberto = HistoricoEtapaLead.query.filter_by(
            lead_id=lead.id,
            saiu_em=None
        ).first()

        if historico_aberto:
            historico_aberto.saiu_em = datetime.utcnow()
            historico_aberto.tempo_segundos = int(
                (historico_aberto.saiu_em - historico_aberto.entrou_em).total_seconds()
            )

        # 🟢 NOVA ETAPA
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

    if current_user.tipo not in ["admin", "master"]:
        if lead.usuario_id != current_user.id:
            return jsonify({"sucesso": False})

    etapa = Pipeline.query.filter_by(
        id=pipeline_id,
        empresa_id=current_user.empresa_id
    ).first()

    if not etapa:
        return jsonify({"sucesso": False})

    if lead.pipeline_id != etapa.id:

        # 🔴 FINALIZA ETAPA ANTIGA
        historico_aberto = HistoricoEtapaLead.query.filter_by(
            lead_id=lead.id,
            saiu_em=None
        ).first()

        if historico_aberto:
            historico_aberto.saiu_em = datetime.utcnow()
            historico_aberto.tempo_segundos = int(
                (historico_aberto.saiu_em - historico_aberto.entrou_em).total_seconds()
            )

        # 🟢 NOVA ETAPA
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