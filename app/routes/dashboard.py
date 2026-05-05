from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import datetime, date
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Fortaleza")

from app.models.lead import Lead
from app.models.pipeline import Pipeline
from app.models.tarefa import Tarefa
from app.models.interacao import Interacao
from app.models.lancamento_financeiro import LancamentoFinanceiro
from app.models.meta import Meta
from app.models.usuario import Usuario
from app.models.mensagem_whatsapp import MensagemWhatsApp

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def home():

    usuario_id = current_user.id

    is_admin = current_user.tipo in ["admin", "master"]

    # ===== LEADS =====
    if is_admin:
        total_leads = Lead.query.filter_by(
            empresa_id=current_user.empresa_id
        ).count()
    else:
        total_leads = Lead.query.filter(
            Lead.empresa_id == current_user.empresa_id,
            (Lead.usuario_id == usuario_id) | (Lead.usuario_id == None)
        ).count()

    leads_novos = 0
    em_negociacao = 0
    conversoes = 0

    etapas = Pipeline.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(Pipeline.ordem.asc()).all()

    etapa_fechado = None
    resumo_pipeline = []

    for etapa in etapas:

        if is_admin:
            quantidade = Lead.query.filter_by(
                empresa_id=current_user.empresa_id,
                pipeline_id=etapa.id
            ).count()
        else:
            quantidade = Lead.query.filter(
                Lead.empresa_id == current_user.empresa_id,
                Lead.pipeline_id == etapa.id,
                (Lead.usuario_id == usuario_id) | (Lead.usuario_id == None)
            ).count()

        resumo_pipeline.append({
            "nome": etapa.nome,
            "quantidade": quantidade
        })

        if etapa.nome == "Novo Lead":
            leads_novos = quantidade

        if etapa.nome == "Negociação":
            em_negociacao = quantidade

        if etapa.nome == "Fechado":
            conversoes = quantidade
            etapa_fechado = etapa

    # ===== LEADS BASE =====
    if is_admin:
        leads = Lead.query.filter_by(
            empresa_id=current_user.empresa_id
        ).all()
    else:
        leads = Lead.query.filter(
            Lead.empresa_id == current_user.empresa_id,
            (Lead.usuario_id == usuario_id) | (Lead.usuario_id == None)
        ).all()

    # ===== ORIGEM / PRODUTO =====
    origem_resultado = {}
    produto_resultado = {}

    for lead in leads:
        origem = lead.origem or "Não informado"
        origem_resultado[origem] = origem_resultado.get(origem, 0) + 1

        produto = lead.produto_interesse or "Não informado"
        produto_resultado[produto] = produto_resultado.get(produto, 0) + 1

    # ===== TAREFAS =====
    agora = datetime.now(TZ)

    if is_admin:
        tarefas_base = Tarefa.query.filter_by(
            empresa_id=current_user.empresa_id
        ).order_by(Tarefa.data_tarefa.asc()).all()
    else:
        tarefas_base = Tarefa.query.filter(
            Tarefa.empresa_id == current_user.empresa_id,
            (Tarefa.usuario_id == usuario_id) | (Tarefa.usuario_id == None)
        ).order_by(Tarefa.data_tarefa.asc()).all()

    tarefas_pendentes = len([t for t in tarefas_base if t.status == "pendente"])
    tarefas_atrasadas = len([t for t in tarefas_base if t.status == "pendente" and t.data_tarefa < agora])
    tarefas_hoje = len([t for t in tarefas_base if t.status == "pendente" and t.data_tarefa.date() == agora.date()])

    proximas_tarefas = tarefas_base[:8]

    # ===== FINANCEIRO =====
    lancamentos = LancamentoFinanceiro.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(LancamentoFinanceiro.data_lancamento.desc()).all()

    total_entradas = 0
    total_saidas = 0
    ultimos_lancamentos = []

    for l in lancamentos:
        pode_contar = is_admin or (not l.lead or l.lead.usuario_id in [usuario_id, None])

        if pode_contar:
            if l.tipo == "entrada":
                total_entradas += l.valor
            elif l.tipo == "saida":
                total_saidas += l.valor

            if len(ultimos_lancamentos) < 5:
                ultimos_lancamentos.append(l)

    lucro = total_entradas - total_saidas

    # ===== METAS =====
    metas_lista = Meta.query.filter_by(
        empresa_id=current_user.empresa_id
    ).all()

    metas_calculadas = []

    for meta in metas_lista:
        progresso = (total_entradas / meta.valor_meta * 100) if meta.valor_meta > 0 else 0

        metas_calculadas.append({
            "meta": meta,
            "realizado": total_entradas,
            "progresso": progresso
        })

    # ===== RANKING =====
    usuarios = Usuario.query.filter_by(
        empresa_id=current_user.empresa_id
    ).all()

    ranking_vendedores = []

    for usuario in usuarios:

        total_leads_usuario = Lead.query.filter_by(
            empresa_id=current_user.empresa_id,
            usuario_id=usuario.id
        ).count()

        vendas_fechadas = 0
        if etapa_fechado:
            vendas_fechadas = Lead.query.filter_by(
                empresa_id=current_user.empresa_id,
                usuario_id=usuario.id,
                pipeline_id=etapa_fechado.id
            ).count()

        ligacoes = Interacao.query.filter_by(
            empresa_id=current_user.empresa_id,
            usuario_id=usuario.id,
            tipo="Ligação"
        ).count()

        followups = Tarefa.query.filter_by(
            empresa_id=current_user.empresa_id,
            usuario_id=usuario.id,
            tipo="Follow-up"
        ).count()

        receita = sum([
            l.valor for l in lancamentos
            if l.tipo == "entrada" and l.lead and l.lead.usuario_id == usuario.id
        ])

        comissao = (receita * (usuario.percentual_comissao or 0)) / 100

        ranking_vendedores.append({
            "usuario": usuario,
            "total_leads": total_leads_usuario,
            "vendas_fechadas": vendas_fechadas,
            "ligacoes": ligacoes,
            "followups": followups,
            "receita": receita,
            "comissao": comissao
        })

    ranking_vendedores = sorted(
        ranking_vendedores,
        key=lambda item: (item["vendas_fechadas"], item["receita"], item["total_leads"]),
        reverse=True
    )

    # =========================
    # 🔥 WHATSAPP DASHBOARD
    # =========================

    mensagens_recebidas = MensagemWhatsApp.query.filter_by(
        empresa_id=current_user.empresa_id,
        direcao="recebida"
    ).count()

    mensagens_enviadas = MensagemWhatsApp.query.filter_by(
        empresa_id=current_user.empresa_id,
        direcao="enviada"
    ).count()

    mensagens_nao_lidas = MensagemWhatsApp.query.filter_by(
        empresa_id=current_user.empresa_id,
        direcao="recebida",
        lida=False
    ).count()

    # ===== LIGAÇÕES HOJE =====
    hoje = datetime.now(TZ).date()

    ligacoes_hoje_query = Interacao.query.filter(
        Interacao.empresa_id == current_user.empresa_id,
        Interacao.tipo == "Ligação"
    ).all()

    ligacoes_hoje = []
    total_ligacoes_hoje = 0

    for l in ligacoes_hoje_query:
        if l.criado_em and l.criado_em.astimezone(TZ).date() == hoje:
            total_ligacoes_hoje += 1
            ligacoes_hoje.append(l)

    # ===== TEMPO DE RESPOSTA DO VENDEDOR =====
    tempos_resposta = []
    leads_sem_resposta = []

    for lead in leads:
        primeira_interacao = Interacao.query.filter_by(
            empresa_id=current_user.empresa_id,
            lead_id=lead.id
        ).order_by(Interacao.criado_em.asc()).first()

        if primeira_interacao and lead.criado_em:
            segundos = int((primeira_interacao.criado_em - lead.criado_em).total_seconds())

            if segundos >= 0:
                tempos_resposta.append(segundos)
        else:
            leads_sem_resposta.append(lead)

    tempo_medio_resposta = "Sem dados"

    if tempos_resposta:
        media_segundos = sum(tempos_resposta) // len(tempos_resposta)
        media_minutos = media_segundos // 60
        media_horas = media_minutos // 60

        if media_horas > 0:
            tempo_medio_resposta = f"{media_horas}h {media_minutos % 60}min"
        else:
            tempo_medio_resposta = f"{media_minutos}min"

    total_leads_sem_resposta = len(leads_sem_resposta)
    leads_sem_resposta_lista = leads_sem_resposta[:5]

    return render_template(
    "dashboard.html",
    total_leads=total_leads,
    leads_novos=leads_novos,
    em_negociacao=em_negociacao,
    conversoes=conversoes,
    resumo_pipeline=resumo_pipeline,
    origem_resultado=origem_resultado,
    produto_resultado=produto_resultado,
    tarefas_pendentes=tarefas_pendentes,
    tarefas_atrasadas=tarefas_atrasadas,
    tarefas_hoje=tarefas_hoje,
    proximas_tarefas=proximas_tarefas,
    total_entradas=total_entradas,
    total_saidas=total_saidas,
    lucro=lucro,
    ultimos_lancamentos=ultimos_lancamentos,
    metas=metas_calculadas,
    ranking_vendedores=ranking_vendedores,
    mensagens_recebidas=mensagens_recebidas,
    mensagens_enviadas=mensagens_enviadas,
    mensagens_nao_lidas=mensagens_nao_lidas,  # 👈 ESSA VÍRGULA AQUI
        total_ligacoes_hoje=total_ligacoes_hoje,
    ligacoes_hoje=ligacoes_hoje,
    tempo_medio_resposta=tempo_medio_resposta,
    total_leads_sem_resposta=total_leads_sem_resposta,
    leads_sem_resposta_lista=leads_sem_resposta_lista,
)