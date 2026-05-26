import os
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime

from app.services.whatsapp_qr_service import EvolutionAPIService
from app.models.lid_mapping import LidMapping
from app.models.pipeline import Pipeline
from app.models.lead import Lead
from app.models.mensagem_whatsapp import MensagemWhatsApp
from app import db, socketio

whatsapp_qr_bp = Blueprint("whatsapp_qr", __name__, url_prefix="/whatsapp-qr")


def obter_instance_name():
    empresa_id = getattr(current_user, "empresa_id", None)
    user_id = getattr(current_user, "id", None)

    if empresa_id:
        return f"mava_empresa_{empresa_id}"

    return f"mava_user_{user_id or 'local'}"


def formatar_jid(jid):
    if not jid:
        return "Contato"

    numero = (
        jid.replace("@s.whatsapp.net", "")
        .replace("@g.us", "")
        .replace("@lid", "")
    )

    if numero.startswith("55") and len(numero) >= 12:
        ddd = numero[2:4]
        telefone = numero[4:]

        if len(telefone) == 9:
            return f"({ddd}) {telefone[:5]}-{telefone[5:]}"
        elif len(telefone) == 8:
            return f"({ddd}) {telefone[:4]}-{telefone[4:]}"

    return numero


def limpar_numero(numero):
    if not numero:
        return ""

    numero = (
        numero.replace("(", "")
        .replace(")", "")
        .replace("-", "")
        .replace(" ", "")
        .replace("+", "")
    )

    if not numero.startswith("55"):
        numero = f"55{numero}"

    return numero


def buscar_mapping_lid(lid_jid, instance_name):
    if not lid_jid:
        return None

    return LidMapping.query.filter_by(
        lid_jid=lid_jid,
        instance_name=instance_name
    ).first()


def resolver_jid_para_busca(jid, instance_name):
    if "@lid" not in jid:
        return jid

    mapping = buscar_mapping_lid(jid, instance_name)

    if mapping:
        numero = mapping.numero_real

        if "@s.whatsapp.net" not in numero:
            numero = f"{numero}@s.whatsapp.net"

        return numero

    return jid


def resolver_jid_para_envio(jid, instance_name):
    if "@lid" not in jid:
        return jid

    mapping = buscar_mapping_lid(jid, instance_name)

    if mapping:
        return mapping.numero_real

    return jid


def timestamp_para_datetime(timestamp):
    try:
        timestamp = int(timestamp)

        if timestamp > 9999999999:
            timestamp = timestamp / 1000

        return datetime.fromtimestamp(timestamp)
    except Exception:
        return datetime.utcnow()


def obter_ou_criar_entrada_whatsapp():
    etapa = Pipeline.query.filter_by(
        nome="Entrada WhatsApp",
        empresa_id=current_user.empresa_id
    ).first()

    if etapa:
        return etapa

    etapa = Pipeline(
        nome="Entrada WhatsApp",
        ordem=0,
        empresa_id=current_user.empresa_id
    )

    db.session.add(etapa)
    db.session.commit()

    return etapa


def extrair_telefone_para_lead(remote_jid, instance_name):
    if not remote_jid:
        return None

    if "@g.us" in remote_jid:
        return None

    if "@lid" in remote_jid:
        mapping = buscar_mapping_lid(remote_jid, instance_name)

        if mapping:
            return limpar_numero(mapping.numero_real)

        numero_lid = remote_jid.replace("@lid", "")
        return numero_lid[:20]

    telefone = (
        remote_jid.replace("@s.whatsapp.net", "")
        .replace("@lid", "")
        .replace("@g.us", "")
    )

    telefone = limpar_numero(telefone)

    return telefone[:20]


def sincronizar_conversa_com_lead(conversa, instance_name):
    if not current_user.is_authenticated:
        return None

    if not current_user.empresa_id:
        return None

    remote_jid = conversa.get("remoteJid")

    if not remote_jid:
        return None

    if "@g.us" in remote_jid:
        return None

    telefone = extrair_telefone_para_lead(remote_jid, instance_name)

    if not telefone:
        return None

    nome = (
        conversa.get("nome_formatado")
        or conversa.get("name")
        or conversa.get("pushName")
        or conversa.get("notify")
        or conversa.get("contactName")
        or conversa.get("profileName")
        or formatar_jid(remote_jid)
    )

    timestamp = conversa.get("timestamp") or 0
    data_ultima = timestamp_para_datetime(timestamp)

    entrada_whatsapp = obter_ou_criar_entrada_whatsapp()

    lead = Lead.query.filter_by(
        empresa_id=current_user.empresa_id,
        telefone=telefone,
        origem="whatsapp"
    ).first()

    if not lead:
        lead = Lead(
            nome=nome or "Contato WhatsApp",
            telefone=telefone,
            email=None,
            origem="whatsapp",
            produto_interesse="Atendimento WhatsApp",
            plano=None,
            valor=0.0,
            status="aberto",
            pipeline_id=entrada_whatsapp.id,
            empresa_id=current_user.empresa_id,
            usuario_id=None,
            criado_em=datetime.utcnow(),
            etapa_atualizada_em=data_ultima or datetime.utcnow()
        )

        db.session.add(lead)
        db.session.commit()

    else:
        mudou = False

        if nome and lead.nome != nome:
            lead.nome = nome
            mudou = True

        if not lead.pipeline_id:
            lead.pipeline_id = entrada_whatsapp.id
            mudou = True

        if data_ultima:
            if not lead.etapa_atualizada_em or data_ultima > lead.etapa_atualizada_em:
                lead.etapa_atualizada_em = data_ultima
                mudou = True

        if mudou:
            db.session.commit()

    conversa["lead_id"] = lead.id
    conversa["lead_nome"] = lead.nome
    conversa["lead_telefone"] = lead.telefone
    conversa["lead_pipeline"] = lead.pipeline.nome if lead.pipeline else "Sem etapa"
    conversa["lead_tags"] = lead.lista_tags if hasattr(lead, "lista_tags") else []
    conversa["lead_vendedor"] = lead.usuario.nome if lead.usuario else "Sem vendedor"

    return lead


@whatsapp_qr_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    service = EvolutionAPIService()

    instance_name = obter_instance_name()

    qr_base64 = None
    qr_code = None
    pairing_code = None
    status = None

    try:
        status_result = service.status_instancia(instance_name)
        status = status_result.get("estado")
    except Exception:
        status = None

    if request.method == "POST":
        acao = request.form.get("acao")

        try:
            if acao == "gerar_qr":
                instance_name = f"{obter_instance_name()}_{int(datetime.utcnow().timestamp())}"

                resultado = service.conectar_qr(instance_name)

                qr_base64 = (
                    resultado.get("qr_base64")
                    or resultado.get("qr_code")
                    or resultado.get("data", {}).get("qrcode", {}).get("base64")
                    or resultado.get("data", {}).get("base64")
                    or resultado.get("data", {}).get("qr")
                    or resultado.get("data", {}).get("qrCode")
                )

                pairing_code = resultado.get("pairing_code")

                if qr_base64:
                    return render_template(
                        "whatsapp_qr.html",
                        instance_name=instance_name,
                        qr_base64=qr_base64,
                        qr_code=qr_base64,
                        pairing_code=pairing_code,
                        status="connecting",
                    )

                flash("Não foi possível gerar o QR Code. Tente novamente.", "warning")

            elif acao == "status":
                resultado = service.status_instancia(instance_name)
                status = resultado.get("estado")

                if status:
                    flash(f"Status do WhatsApp: {status}", "info")
                else:
                    flash("Não foi possível consultar o status.", "warning")

            elif acao == "logout":
                resultado = service.logout_instancia(instance_name)

                flash(
                    "WhatsApp desconectado com sucesso."
                    if resultado["ok"]
                    else "Não foi possível desconectar o WhatsApp.",
                    "success" if resultado["ok"] else "warning"
                )

                status = None

        except Exception as e:
            flash(f"Erro ao processar WhatsApp: {e}", "danger")

    return render_template(
        "whatsapp_qr.html",
        instance_name=instance_name,
        qr_base64=qr_base64,
        qr_code=qr_code,
        pairing_code=pairing_code,
        status=status,
    )


@whatsapp_qr_bp.route("/conversas")
@login_required
def conversas():
    service = EvolutionAPIService()

    instance_name = obter_instance_name()
    jid_ativo = request.args.get("jid")
    numero_param = request.args.get("numero", "").strip()

    if numero_param:
        numero_limpo = limpar_numero(numero_param)
        jid_ativo = f"{numero_limpo}@s.whatsapp.net"

    resultado = service.buscar_conversas(instance_name)

    conversas = []

    if resultado["ok"]:
        vistos = set()

        for conversa in resultado["data"]:
            remote_jid = conversa.get("remoteJid")

            if not remote_jid:
                continue

            if remote_jid in vistos:
                continue

            vistos.add(remote_jid)

            mapping = None

            if "@lid" in remote_jid:
                mapping = buscar_mapping_lid(remote_jid, instance_name)

            nome = (
                conversa.get("nome_formatado")
                or conversa.get("name")
                or conversa.get("pushName")
                or conversa.get("notify")
                or conversa.get("contactName")
                or conversa.get("profileName")
                or formatar_jid(remote_jid)
            )

            numero_formatado = formatar_jid(remote_jid)

            if mapping:
                numero_formatado = formatar_jid(mapping.numero_real)

            ultima_mensagem = (
                conversa.get("ultima_mensagem")
                or conversa.get("lastMessage")
                or conversa.get("conversation")
                or "Clique para abrir conversa"
            )

            timestamp = (
                conversa.get("timestamp")
                or conversa.get("updatedAt")
                or conversa.get("conversationTimestamp")
                or conversa.get("messageTimestamp")
                or 0
            )

            unread_count = (
                conversa.get("unread_count")
                or conversa.get("unreadCount")
                or 0
            )

            conversa["nome_formatado"] = nome
            conversa["numero_formatado"] = numero_formatado
            conversa["ultima_mensagem"] = ultima_mensagem
            conversa["timestamp"] = timestamp
            conversa["unread_count"] = unread_count

            sincronizar_conversa_com_lead(conversa, instance_name)

            conversas.append(conversa)

        conversas = sorted(
            conversas,
            key=lambda x: x.get("timestamp", 0),
            reverse=True
        )

    mensagens = []
    nome_contato = None

    if jid_ativo:
        jid_busca = resolver_jid_para_busca(jid_ativo, instance_name)

        resultado_chat = service.buscar_mensagens(instance_name, jid_busca)

        if resultado_chat["ok"]:
            mensagens = resultado_chat["data"]

            mensagens_unicas = []
            ids_vistos = set()

            for msg in mensagens:
                key = msg.get("key", {})
                msg_id = key.get("id") or msg.get("id")

                if not msg_id:
                    continue

                if msg_id in ids_vistos:
                    continue

                ids_vistos.add(msg_id)
                mensagens_unicas.append(msg)

            mensagens = sorted(
                mensagens_unicas,
                key=lambda msg: msg.get("messageTimestamp", 0)
            )

        for conversa in conversas:
            if conversa.get("remoteJid") == jid_ativo:
                nome_contato = conversa.get("nome_formatado")
                break

        if not nome_contato:
            nome_contato = formatar_jid(jid_ativo)

    return render_template(
        "whatsapp_conversas.html",
        conversas=conversas,
        mensagens=mensagens,
        jid_ativo=jid_ativo,
        nome_contato=nome_contato,
        instance_name=instance_name
    )


@whatsapp_qr_bp.route("/chat/<path:jid>")
@login_required
def abrir_chat(jid):
    instance_name = obter_instance_name()

    return redirect(
        url_for(
            "whatsapp_qr.conversas",
            jid=jid,
            instance_name=instance_name
        )
    )


@whatsapp_qr_bp.route("/chat/<path:jid>/enviar", methods=["POST"])
@login_required
def enviar_chat(jid):
    service = EvolutionAPIService()

    instance_name = obter_instance_name()
    mensagem = request.form.get("mensagem")

    if mensagem:
        jid_envio = resolver_jid_para_envio(jid, instance_name)

        resultado = service.enviar_mensagem(instance_name, jid_envio, mensagem)

        if resultado["ok"]:
            socketio.emit(
                "nova_mensagem_whatsapp",
                {
                    "jid": jid,
                    "mensagem": mensagem,
                    "hora": datetime.now().strftime("%H:%M"),
                    "from_me": True
                },
                room=jid
            )

            flash("Mensagem enviada com sucesso.", "success")
        else:
            erro = resultado.get("erro") or resultado.get("data") or "Erro ao enviar mensagem."

            if "@lid" in jid and jid_envio == jid:
                erro = (
                    "Esse contato veio como @lid. "
                    "Corrija o número real antes de enviar."
                )

            flash(erro, "danger")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"ok": True}

    return redirect(
        url_for(
            "whatsapp_qr.conversas",
            jid=jid,
            instance_name=instance_name
        )
    )


@whatsapp_qr_bp.route("/chat/<path:jid>/enviar-arquivo", methods=["POST"])
@login_required
def enviar_arquivo_chat(jid):
    service = EvolutionAPIService()

    instance_name = obter_instance_name()
    legenda = request.form.get("legenda", "").strip()
    arquivo = request.files.get("arquivo")

    if not arquivo or arquivo.filename == "":
        return {"ok": False, "erro": "Nenhum arquivo enviado."}, 400

    pasta_upload = os.path.join(
        "app",
        "static",
        "uploads",
        "whatsapp"
    )

    os.makedirs(pasta_upload, exist_ok=True)

    nome_seguro = secure_filename(arquivo.filename)

    caminho_arquivo = os.path.join(
        pasta_upload,
        nome_seguro
    )

    arquivo.save(caminho_arquivo)

    jid_envio = resolver_jid_para_envio(jid, instance_name)

    resultado = service.enviar_arquivo(
        instance_name,
        jid_envio,
        caminho_arquivo,
        legenda
    )

    if resultado["ok"]:
        socketio.emit(
            "nova_mensagem_whatsapp",
            {
                "jid": jid,
                "mensagem": legenda or nome_seguro,
                "hora": datetime.now().strftime("%H:%M"),
                "from_me": True,
                "tipo": "arquivo"
            },
            room=jid
        )

        return {"ok": True}

    return {
        "ok": False,
        "erro": resultado.get("data")
    }, 400


@whatsapp_qr_bp.route("/chat_ajax/<path:jid>")
@login_required
def chat_ajax(jid):
    instance_name = obter_instance_name()

    nome_contato = formatar_jid(jid)

    telefone = (
        jid.replace("@s.whatsapp.net", "")
        .replace("@lid", "")
        .replace("@g.us", "")
    )

    if telefone and not telefone.startswith("55"):
        telefone = f"55{telefone}"

    mensagens_banco = MensagemWhatsApp.query.filter_by(
        telefone=telefone
    ).order_by(
        MensagemWhatsApp.criado_em.asc()
    ).all()

    mensagens = []

    for item in mensagens_banco:
        mensagens.append({
            "key": {
                "id": f"local-{item.id}",
                "fromMe": True if item.direcao == "enviada" else False
            },
            "messageTimestamp": int(item.criado_em.timestamp()),
            "hora_formatada": item.criado_em.strftime("%H:%M"),
            "message": {
                "conversation": item.mensagem or ""
            }
        })

    return render_template(
        "partials/chat_content.html",
        mensagens=mensagens,
        jid_ativo=jid,
        nome_contato=nome_contato,
        instance_name=instance_name
    )


@whatsapp_qr_bp.route("/salvar_lid", methods=["POST"])
@login_required
def salvar_lid():
    lid_jid = request.form.get("lid_jid")
    numero_real = request.form.get("numero_real")
    instance_name = obter_instance_name()

    if not lid_jid or not numero_real:
        flash("Informe o número corretamente.", "danger")

        return redirect(
            url_for(
                "whatsapp_qr.conversas",
                jid=lid_jid,
                instance_name=instance_name
            )
        )

    numero_real = limpar_numero(numero_real)

    mapping = LidMapping.query.filter_by(
        lid_jid=lid_jid,
        instance_name=instance_name
    ).first()

    if not mapping:
        mapping = LidMapping(
            lid_jid=lid_jid,
            numero_real=numero_real,
            instance_name=instance_name
        )

        db.session.add(mapping)
    else:
        mapping.numero_real = numero_real

    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"ok": True, "numero_real": numero_real}

    flash("Número corrigido com sucesso.", "success")

    return redirect(
        url_for(
            "whatsapp_qr.conversas",
            jid=lid_jid,
            instance_name=instance_name
        )
    )


@socketio.on("entrar_chat")
def entrar_chat(data):
    from flask_socketio import join_room

    jid = data.get("jid")

    if jid:
        join_room(jid)