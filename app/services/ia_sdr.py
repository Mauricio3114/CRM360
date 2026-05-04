from app import db
from app.models.interacao import Interacao
from app.models.pipeline import Pipeline
from app.models.tarefa import Tarefa
from datetime import datetime, timedelta


def buscar_contexto_historico(lead):
    interacoes = Interacao.query.filter_by(
        lead_id=lead.id,
        empresa_id=lead.empresa_id
    ).order_by(Interacao.criado_em.desc()).limit(8).all()

    textos = []
    ja_falou_preco = False
    ja_pediu_pensar = False
    ja_pediu_ligacao = False
    ja_quer_fechar = False

    for item in interacoes:
        texto = (item.descricao or "").lower()

        textos.append(f"{item.tipo}: {item.descricao}")

        if any(p in texto for p in ["valor", "preço", "quanto", "custa", "plano"]):
            ja_falou_preco = True

        if any(p in texto for p in ["vou pensar", "depois", "caro", "negociar"]):
            ja_pediu_pensar = True

        if any(p in texto for p in ["me liga", "ligar", "chamada", "telefone"]):
            ja_pediu_ligacao = True

        if any(p in texto for p in ["quero fechar", "vamos fechar", "aceito", "contratar"]):
            ja_quer_fechar = True

    return {
        "textos": textos,
        "ja_falou_preco": ja_falou_preco,
        "ja_pediu_pensar": ja_pediu_pensar,
        "ja_pediu_ligacao": ja_pediu_ligacao,
        "ja_quer_fechar": ja_quer_fechar,
    }


def detectar_etapa_pipeline(mensagem_cliente):
    mensagem = mensagem_cliente.lower().strip()

    if any(palavra in mensagem for palavra in ["fechar", "fechado", "quero fechar", "vamos fechar", "pode fazer", "aceito", "contratar"]):
        return "Fechado"

    if any(palavra in mensagem for palavra in ["proposta", "orçamento", "manda", "me envia", "envia", "valor", "preço", "quanto", "custa", "plano"]):
        return "Proposta"

    if any(palavra in mensagem for palavra in ["vou pensar", "depois", "caro", "negociar", "desconto", "condição"]):
        return "Negociação"

    if any(palavra in mensagem for palavra in ["não quero", "sem interesse", "não tenho interesse", "desisti"]):
        return "Perdido"

    if any(palavra in mensagem for palavra in ["interesse", "tenho interesse", "quero", "preciso", "funciona", "como funciona", "explica", "detalhes"]):
        return "Contato Feito"

    return None


def mover_lead_por_ia(lead, mensagem_cliente):
    nome_etapa = detectar_etapa_pipeline(mensagem_cliente)

    if not nome_etapa:
        return None

    etapa = Pipeline.query.filter_by(
        nome=nome_etapa,
        empresa_id=lead.empresa_id
    ).first()

    if not etapa:
        return None

    lead.pipeline_id = etapa.id
    return nome_etapa


def criar_tarefa_por_ia(lead, mensagem_cliente):
    mensagem = mensagem_cliente.lower().strip()

    titulo = None
    descricao = None
    data_tarefa = None
    tipo = "Follow-up"

    # 🔥 NOVO: tarefa para proposta / preço
    if any(palavra in mensagem for palavra in ["valor", "preço", "quanto", "custa", "plano", "proposta"]):
        titulo = f"Enviar proposta para {lead.nome}"
        descricao = "IA criou esta tarefa porque o lead pediu informações de preço/proposta."
        data_tarefa = datetime.now() + timedelta(minutes=30)
        tipo = "Proposta"

    if any(palavra in mensagem for palavra in ["vou pensar", "depois", "caro", "negociar", "desconto", "condição"]):
        titulo = f"Retornar para {lead.nome}"
        descricao = "IA criou este follow-up porque o lead demonstrou dúvida ou pediu tempo para pensar."
        data_tarefa = datetime.now() + timedelta(days=1)
        tipo = "Follow-up"

    elif any(palavra in mensagem for palavra in ["me liga amanhã", "ligar amanhã", "amanhã", "amanha"]):
        titulo = f"Ligar para {lead.nome}"
        descricao = "IA criou esta tarefa porque o lead pediu contato amanhã."
        data_tarefa = datetime.now() + timedelta(days=1)
        tipo = "Ligação"

    elif any(palavra in mensagem for palavra in ["me liga", "liga pra mim", "ligar", "chamada"]):
        titulo = f"Ligar para {lead.nome}"
        descricao = "IA criou esta tarefa porque o lead pediu ligação."
        data_tarefa = datetime.now() + timedelta(hours=2)
        tipo = "Ligação"

    elif any(palavra in mensagem for palavra in ["reunião", "reuniao", "agenda", "marcar"]):
        titulo = f"Agendar reunião com {lead.nome}"
        descricao = "IA criou esta tarefa porque o lead demonstrou interesse em reunião/agendamento."
        data_tarefa = datetime.now() + timedelta(hours=3)
        tipo = "Reunião"

    elif any(palavra in mensagem for palavra in ["fechar", "fechado", "quero fechar", "vamos fechar", "pode fazer", "aceito", "contratar"]):
        titulo = f"Finalizar venda com {lead.nome}"
        descricao = "IA criou esta tarefa porque o lead demonstrou intenção de fechamento."
        data_tarefa = datetime.now() + timedelta(hours=1)
        tipo = "Tarefa"

    if not titulo:
        return None

    tarefa = Tarefa(
        titulo=titulo,
        descricao=descricao,
        data_tarefa=data_tarefa,
        status="pendente",
        tipo=tipo,
        lead_id=lead.id,
        empresa_id=lead.empresa_id,
        enviar_whatsapp=False,
        mensagem_whatsapp=None
    )

    db.session.add(tarefa)

    return titulo


def responder_lead(lead, mensagem_cliente):
    mensagem = mensagem_cliente.lower().strip()

    nome = lead.nome.split()[0] if lead.nome else "tudo bem"
    produto = lead.produto_interesse or "nossa solução"
    contexto = buscar_contexto_historico(lead)

    # =========================
    # 🔥 1 - REGRAS DO BANCO (CENTRAL IA SDR)
    # =========================
    try:
        from app.models.regra_ia_sdr import RegraIASDR

        regras = RegraIASDR.query.filter_by(
            empresa_id=lead.empresa_id,
            ativo=True
        ).all()

        for regra in regras:
            palavras = [p.strip().lower() for p in regra.palavras_chave.split(",") if p.strip()]

            if any(p in mensagem for p in palavras):
                resposta = regra.resposta

                resposta = resposta.replace("{nome}", nome)
                resposta = resposta.replace("{produto}", produto)

                if contexto["ja_falou_preco"]:
                    resposta += "\n\nVi que já falamos sobre valores antes, então posso seguir para uma proposta mais objetiva se você quiser."

                if contexto["ja_pediu_pensar"]:
                    resposta += "\n\nComo você já tinha comentado que iria pensar, posso te ajudar tirando a principal dúvida agora."

                if regra.etapa_pipeline:
                    etapa = Pipeline.query.filter_by(
                        nome=regra.etapa_pipeline,
                        empresa_id=lead.empresa_id
                    ).first()

                    if etapa:
                        lead.pipeline_id = etapa.id

                if regra.criar_tarefa:
                    titulo = (regra.titulo_tarefa or "Follow-up").replace("{nome}", lead.nome)

                    tarefa = Tarefa(
                        titulo=titulo,
                        descricao="Criada automaticamente pela IA SDR usando regra da Central IA.",
                        data_tarefa=datetime.now() + timedelta(hours=regra.horas_para_tarefa or 24),
                        status="pendente",
                        tipo=regra.tipo_tarefa or "Follow-up",
                        lead_id=lead.id,
                        empresa_id=lead.empresa_id,
                        enviar_whatsapp=False,
                        mensagem_whatsapp=None
                    )

                    db.session.add(tarefa)

                return resposta.strip()

    except Exception:
        pass

    # =========================
    # 🔥 2 - IA ORIGINAL + HISTÓRICO
    # =========================

    if contexto["ja_falou_preco"] and any(palavra in mensagem for palavra in ["valor", "preço", "quanto", "custa", "plano"]):
        resposta = f"""
{nome}, como a gente já falou um pouco sobre valores, vou ser mais direto.

Pra eu te passar uma proposta certa, me confirma só:
é para uso próprio, para empresa ou para revenda?

Com isso eu já consigo te direcionar sem ficar repetindo informação.
"""

    elif contexto["ja_pediu_pensar"] and any(palavra in mensagem for palavra in ["vou pensar", "depois", "caro", "não sei"]):
        resposta = f"""
Entendi, {nome}.

Como você já comentou que queria pensar, me diz só o que ainda está travando:
é o valor, a forma de pagamento ou dúvida se a solução resolve mesmo?

Assim eu te ajudo sem pressão.
"""

    elif contexto["ja_pediu_ligacao"] and any(palavra in mensagem for palavra in ["me liga", "ligar", "chamada"]):
        resposta = f"""
Perfeito, {nome}.

Vi que já falamos sobre ligação antes. Me confirma o melhor horário hoje para eu deixar esse retorno organizado.
"""

    elif any(palavra in mensagem for palavra in ["fechar", "fechado", "quero fechar", "vamos fechar", "pode fazer", "aceito", "contratar"]):
        resposta = f"""
Perfeito, {nome}! Excelente decisão.

Vou te direcionar para a finalização agora. O próximo passo é confirmar os dados e alinhar pagamento/implantação.

Me confirma, por favor:
o melhor contato para continuar é esse mesmo?
"""

    elif any(palavra in mensagem for palavra in ["valor", "preço", "quanto", "custa", "plano"]):
        resposta = f"""
Olá {nome}, perfeito!

Sobre valores, eu consigo te orientar melhor rapidinho.

Antes de te passar uma proposta, me diz uma coisa:
você busca {produto} para uso próprio, para sua empresa ou para revender?

Assim eu te indico o melhor plano e evito te passar algo que não encaixe no que você precisa.
"""

    elif any(palavra in mensagem for palavra in ["funciona", "como funciona", "explica", "detalhes"]):
        resposta = f"""
Claro, {nome}!

Funciona de forma simples: primeiro entendemos sua necessidade, depois mostramos a melhor solução e acompanhamos todo o processo até ficar tudo certo.

Me diz uma coisa:
qual é hoje a maior dificuldade que você quer resolver com {produto}?
"""

    elif any(palavra in mensagem for palavra in ["interesse", "tenho interesse", "quero", "preciso"]):
        resposta = f"""
Show, {nome}! Que bom saber do seu interesse.

Para eu te ajudar melhor, me responde rapidinho:
você quer começar o quanto antes ou ainda está pesquisando opções?

Com isso eu já consigo te direcionar para o melhor atendimento.
"""

    elif any(palavra in mensagem for palavra in ["reunião", "reuniao", "agenda", "marcar", "ligar", "chamada"]):
        resposta = f"""
Perfeito, {nome}!

Podemos organizar sim.

Qual melhor horário para falarmos?
Pode ser hoje ainda ou prefere amanhã?
"""

    elif any(palavra in mensagem for palavra in ["não quero", "sem interesse", "não tenho interesse", "desisti"]):
        resposta = f"""
Tudo bem, {nome}. Obrigado por avisar.

Vou deixar registrado aqui. Caso mude de ideia no futuro, seguimos à disposição para te ajudar.
"""

    elif any(palavra in mensagem for palavra in ["não", "caro", "vou pensar", "depois"]):
        resposta = f"""
Entendo, {nome}. Sem problema.

Só para eu te ajudar melhor: sua dúvida maior é sobre valor, forma de pagamento ou se a solução realmente resolve o que você precisa?

Assim eu consigo te orientar com mais clareza.
"""

    else:
        resposta = f"""
Olá {nome}, tudo bem?

Recebi sua mensagem: "{mensagem_cliente}"

Vou te ajudar com isso. Me diz só uma coisa:
você está buscando {produto} para resolver qual necessidade principal hoje?
"""

    return resposta.strip()


def registrar_interacao_ia(lead, mensagem_cliente, resposta_ia):
    etapa_movida = mover_lead_por_ia(lead, mensagem_cliente)
    tarefa_criada = criar_tarefa_por_ia(lead, mensagem_cliente)

    interacao_cliente = Interacao(
        lead_id=lead.id,
        empresa_id=lead.empresa_id,
        tipo="Cliente",
        descricao=mensagem_cliente
    )

    interacao_ia = Interacao(
        lead_id=lead.id,
        empresa_id=lead.empresa_id,
        tipo="IA SDR",
        descricao=resposta_ia
    )

    db.session.add(interacao_cliente)
    db.session.add(interacao_ia)

    if etapa_movida:
        interacao_sistema = Interacao(
            lead_id=lead.id,
            empresa_id=lead.empresa_id,
            tipo="Sistema",
            descricao=f"IA SDR moveu o lead automaticamente para a etapa: {etapa_movida}"
        )
        db.session.add(interacao_sistema)

    if tarefa_criada:
        interacao_tarefa = Interacao(
            lead_id=lead.id,
            empresa_id=lead.empresa_id,
            tipo="Sistema",
            descricao=f"IA SDR criou uma tarefa automática na agenda: {tarefa_criada}"
        )
        db.session.add(interacao_tarefa)

    db.session.commit()