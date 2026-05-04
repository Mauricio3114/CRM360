from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from urllib.parse import quote
import os
import uuid
import requests

from app import db
from app.models.mensagem_whatsapp import MensagemWhatsApp
from app.models.lead import Lead
from app.models.interacao import Interacao
from app.models.empresa import Empresa
from app.services.ia_sdr import responder_lead

whatsapp_inbox_bp = Blueprint("whatsapp_inbox", __name__, url_prefix="/whatsapp")


def limpar_telefone(telefone):
    return ''.join(filter(str.isdigit, telefone or ""))


def buscar_lead_por_telefone(telefone, empresa_id):
    telefone_limpo = limpar_telefone(telefone)

    leads = Lead.query.filter_by(empresa_id=empresa_id).all()

    for lead in leads:
        if limpar_telefone(lead.telefone) == telefone_limpo:
            return lead

    return None


def buscar_empresa_webhook(phone_number_id=None):
    if phone_number_id:
        empresa = Empresa.query.filter_by(
            whatsapp_phone_number_id=str(phone_number_id)
        ).first()

        if empresa:
            return empresa

    return Empresa.query.filter_by(whatsapp_ativo=True).first()


def tentar_enviar_api(empresa, telefone, mensagem):
    if not empresa or not empresa.whatsapp_ativo:
        return False, "API desativada"

    if not empresa.whatsapp_token or not empresa.whatsapp_phone_number_id:
        return False, "Token ou Phone Number ID não configurado"

    url = f"https://graph.facebook.com/v18.0/{empresa.whatsapp_phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {empresa.whatsapp_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": f"55{telefone}",
        "type": "text",
        "text": {
            "body": mensagem
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)

        if response.status_code in [200, 201]:
            return True, "Enviado pela API"

        return False, f"Erro API {response.status_code}: {response.text}"

    except requests.exceptions.RequestException as erro:
        return False, f"Falha de conexão: {erro}"


def extensao_por_mime(mime_type):
    if not mime_type:
        return ".bin"

    mapa = {
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "video/mp4": ".mp4",
        "application/pdf": ".pdf",
    }

    return mapa.get(mime_type, ".bin")


def baixar_midia_meta(empresa, media_id):
    if not empresa or not empresa.whatsapp_token or not media_id:
        return None, None, None, None

    headers = {
        "Authorization": f"Bearer {empresa.whatsapp_token}"
    }

    try:
        url_info = f"https://graph.facebook.com/v18.0/{media_id}"
        info_response = requests.get(url_info, headers=headers, timeout=20)

        if info_response.status_code != 200:
            print("Erro ao buscar URL da mídia:", info_response.text)
            return None, None, None, None

        info = info_response.json()

        media_url_meta = info.get("url")
        mime_type = info.get("mime_type")
        filename = info.get("filename")

        if not media_url_meta:
            return None, media_id, mime_type, filename

        arquivo_response = requests.get(media_url_meta, headers=headers, timeout=30)

        if arquivo_response.status_code != 200:
            print("Erro ao baixar mídia:", arquivo_response.text)
            return None, media_id, mime_type, filename

        pasta_upload = os.path.join(current_app.static_folder, "uploads", "whatsapp")
        os.makedirs(pasta_upload, exist_ok=True)

        extensao = extensao_por_mime(mime_type)
        nome_arquivo = filename or f"{uuid.uuid4().hex}{extensao}"

        caminho_arquivo = os.path.join(pasta_upload, nome_arquivo)

        with open(caminho_arquivo, "wb") as arquivo:
            arquivo.write(arquivo_response.content)

        media_url_local = url_for(
            "static",
            filename=f"uploads/whatsapp/{nome_arquivo}"
        )

        return media_url_local, media_id, mime_type, nome_arquivo

    except Exception as erro:
        print("Erro geral ao baixar mídia Meta:", erro)
        return None, media_id, None, None


def gerar_resposta_ia_whatsapp(empresa, lead, telefone, mensagem_cliente):
    if not lead:
        return

    try:
        resposta_ia = responder_lead(lead, mensagem_cliente)

        enviado_api, retorno_api = tentar_enviar_api(
            empresa,
            telefone,
            resposta_ia
        )

        if enviado_api:
            status = "ia_enviada_api"
        else:
            status = "ia_gerada_manual"

        msg_ia = MensagemWhatsApp(
            empresa_id=empresa.id,
            lead_id=lead.id,
            usuario_id=None,
            telefone=telefone,
            nome_contato=lead.nome,
            direcao="enviada",
            mensagem=resposta_ia,
            tipo_mensagem="texto",
            status=status,
            criado_em=datetime.utcnow()
        )

        db.session.add(msg_ia)

        interacao_ia = Interacao(
            lead_id=lead.id,
            empresa_id=empresa.id,
            usuario_id=None,
            tipo="IA SDR WhatsApp",
            descricao=f"{resposta_ia} | Status: {retorno_api}"
        )

        db.session.add(interacao_ia)
        db.session.commit()

    except Exception as erro:
        print("Erro IA WhatsApp:", erro)


@whatsapp_inbox_bp.route("/inbox")
@login_required
def inbox():
    telefone_selecionado = request.args.get("telefone")

    mensagens = MensagemWhatsApp.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(MensagemWhatsApp.criado_em.desc()).all()

    contatos_dict = {}

    for msg in mensagens:
        telefone = msg.telefone

        texto_preview = msg.mensagem or "Mídia recebida"

        if msg.tipo_mensagem == "audio":
            texto_preview = "🎤 Áudio"
        elif msg.tipo_mensagem == "image":
            texto_preview = "🖼️ Imagem"
        elif msg.tipo_mensagem == "video":
            texto_preview = "🎥 Vídeo"
        elif msg.tipo_mensagem == "document":
            texto_preview = "📄 Documento"

        if telefone not in contatos_dict:
            contatos_dict[telefone] = {
                "telefone": telefone,
                "nome": msg.nome_contato or "Contato",
                "lead": msg.lead,
                "ultima_mensagem": texto_preview,
                "ultimo_horario": msg.criado_em,
                "total": 1
            }
        else:
            contatos_dict[telefone]["total"] += 1

    contatos = list(contatos_dict.values())
    contatos = sorted(contatos, key=lambda c: c["ultimo_horario"], reverse=True)

    conversa = []
    contato_atual = None

    if telefone_selecionado:
        conversa = MensagemWhatsApp.query.filter_by(
            empresa_id=current_user.empresa_id,
            telefone=telefone_selecionado
        ).order_by(MensagemWhatsApp.criado_em.asc()).all()

        mensagens_nao_lidas = MensagemWhatsApp.query.filter_by(
            empresa_id=current_user.empresa_id,
            telefone=telefone_selecionado,
            direcao="recebida",
            lida=False
        ).all()

        for msg in mensagens_nao_lidas:
            msg.lida = True

        db.session.commit()

        if conversa:
            contato_atual = {
                "telefone": telefone_selecionado,
                "nome": conversa[-1].nome_contato or "Contato",
                "lead": conversa[-1].lead
            }

    leads = Lead.query.filter_by(
        empresa_id=current_user.empresa_id
    ).order_by(Lead.nome.asc()).all()

    return render_template(
        "whatsapp_inbox.html",
        mensagens=mensagens,
        contatos=contatos,
        conversa=conversa,
        contato_atual=contato_atual,
        telefone_selecionado=telefone_selecionado,
        leads=leads
    )


@whatsapp_inbox_bp.route("/nova-manual", methods=["POST"])
@login_required
def nova_manual():
    telefone = request.form.get("telefone", "").strip()
    nome_contato = request.form.get("nome_contato", "").strip()
    mensagem = request.form.get("mensagem", "").strip()
    lead_id = request.form.get("lead_id") or None

    if not telefone or not mensagem:
        return redirect(url_for("whatsapp_inbox.inbox"))

    telefone = limpar_telefone(telefone)

    lead = None

    if lead_id:
        lead = Lead.query.filter_by(
            id=lead_id,
            empresa_id=current_user.empresa_id
        ).first()
    else:
        lead = buscar_lead_por_telefone(telefone, current_user.empresa_id)

    msg = MensagemWhatsApp(
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        lead_id=lead.id if lead else None,
        telefone=telefone,
        nome_contato=nome_contato or (lead.nome if lead else "Contato"),
        direcao="recebida",
        mensagem=mensagem,
        tipo_mensagem="texto",
        status="recebida",
        lida=False,
        criado_em=datetime.utcnow()
    )

    db.session.add(msg)

    if lead:
        interacao = Interacao(
            lead_id=lead.id,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            tipo="WhatsApp recebido",
            descricao=mensagem
        )
        db.session.add(interacao)

    db.session.commit()

    return redirect(url_for("whatsapp_inbox.inbox", telefone=telefone))


@whatsapp_inbox_bp.route("/responder", methods=["POST"])
@login_required
def responder():
    telefone = request.form.get("telefone", "").strip()
    mensagem = request.form.get("mensagem", "").strip()

    telefone = limpar_telefone(telefone)

    if not telefone or not mensagem:
        return redirect(url_for("whatsapp_inbox.inbox"))

    lead = buscar_lead_por_telefone(telefone, current_user.empresa_id)
    empresa = Empresa.query.get(current_user.empresa_id)

    enviado_api, retorno_api = tentar_enviar_api(empresa, telefone, mensagem)

    status = "enviada_api" if enviado_api else "enviada_manual"

    msg = MensagemWhatsApp(
        empresa_id=current_user.empresa_id,
        usuario_id=current_user.id,
        lead_id=lead.id if lead else None,
        telefone=telefone,
        nome_contato=lead.nome if lead else "Contato",
        direcao="enviada",
        mensagem=mensagem,
        tipo_mensagem="texto",
        status=status,
        criado_em=datetime.utcnow()
    )

    db.session.add(msg)

    if lead:
        interacao = Interacao(
            lead_id=lead.id,
            empresa_id=current_user.empresa_id,
            usuario_id=current_user.id,
            tipo="WhatsApp enviado",
            descricao=f"{mensagem} | Status: {retorno_api}"
        )
        db.session.add(interacao)

    db.session.commit()

    if enviado_api:
        return redirect(url_for("whatsapp_inbox.inbox", telefone=telefone))

    link = f"https://wa.me/55{telefone}?text={quote(mensagem)}"
    return redirect(link)


@whatsapp_inbox_bp.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        verify_token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if verify_token == "crm360_webhook_token":
            return challenge or ""

        return "Token inválido", 403

    dados = request.get_json(silent=True) or {}

    try:
        entries = dados.get("entry", [])

        for entry in entries:
            changes = entry.get("changes", [])

            for change in changes:
                value = change.get("value", {})

                metadata = value.get("metadata", {})
                phone_number_id = metadata.get("phone_number_id")

                empresa = buscar_empresa_webhook(phone_number_id)

                if not empresa:
                    print("Webhook recebido, mas nenhuma empresa encontrada.")
                    continue

                contatos = value.get("contacts", [])
                nome_contato = "WhatsApp"

                if contatos:
                    profile = contatos[0].get("profile", {})
                    nome_contato = profile.get("name") or "WhatsApp"

                mensagens = value.get("messages", [])

                for mensagem_meta in mensagens:
                    telefone = limpar_telefone(mensagem_meta.get("from"))
                    tipo = mensagem_meta.get("type")

                    texto = ""
                    media_id = None
                    media_url = None
                    media_mime_type = None
                    media_filename = None

                    if tipo == "text":
                        texto = mensagem_meta.get("text", {}).get("body", "")

                    elif tipo in ["audio", "image", "video", "document"]:
                        bloco_midia = mensagem_meta.get(tipo, {})
                        media_id = bloco_midia.get("id")
                        media_mime_type = bloco_midia.get("mime_type")
                        media_filename = bloco_midia.get("filename")

                        media_url, media_id, media_mime_type_baixado, media_filename_baixado = baixar_midia_meta(
                            empresa,
                            media_id
                        )

                        if media_mime_type_baixado:
                            media_mime_type = media_mime_type_baixado

                        if media_filename_baixado:
                            media_filename = media_filename_baixado

                        if tipo == "audio":
                            texto = "Áudio recebido"
                        elif tipo == "image":
                            texto = "Imagem recebida"
                        elif tipo == "video":
                            texto = "Vídeo recebido"
                        elif tipo == "document":
                            texto = "Documento recebido"

                    else:
                        texto = f"Mensagem recebida do tipo: {tipo}"

                    lead = buscar_lead_por_telefone(telefone, empresa.id)

                    msg = MensagemWhatsApp(
                        empresa_id=empresa.id,
                        lead_id=lead.id if lead else None,
                        usuario_id=None,
                        telefone=telefone,
                        nome_contato=nome_contato or (lead.nome if lead else "WhatsApp"),
                        direcao="recebida",
                        mensagem=texto,
                        tipo_mensagem=tipo or "texto",
                        media_id=media_id,
                        media_url=media_url,
                        media_mime_type=media_mime_type,
                        media_filename=media_filename,
                        status="recebida",
                        lida=False,
                        criado_em=datetime.utcnow()
                    )

                    db.session.add(msg)

                    if lead:
                        interacao = Interacao(
                            lead_id=lead.id,
                            empresa_id=empresa.id,
                            usuario_id=None,
                            tipo="WhatsApp recebido",
                            descricao=texto
                        )
                        db.session.add(interacao)

                    db.session.commit()

                    if tipo == "text" and texto and lead:
                        gerar_resposta_ia_whatsapp(
                            empresa,
                            lead,
                            telefone,
                            texto
                        )

    except Exception as erro:
        print("Erro ao processar webhook WhatsApp:", erro)

    return jsonify({"status": "ok"}), 200