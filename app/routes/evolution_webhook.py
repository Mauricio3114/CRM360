import os
from datetime import datetime

from flask import Blueprint, request, jsonify

from app import db
from app.models.lead import Lead
from app.models.pipeline import Pipeline
from app.models.mensagem_whatsapp import MensagemWhatsApp


evolution_webhook_bp = Blueprint(
    "evolution_webhook",
    __name__,
    url_prefix="/webhook/evolution"
)


def limpar_numero(numero):
    if not numero:
        return ""

    numero = (
        str(numero)
        .replace("@s.whatsapp.net", "")
        .replace("@lid", "")
        .replace("@g.us", "")
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .strip()
    )

    numero = "".join(filter(str.isdigit, numero))

    if numero and not numero.startswith("55"):
        numero = f"55{numero}"

    return numero


def extrair_texto(message):
    if not isinstance(message, dict):
        return ""

    if message.get("conversation"):
        return message.get("conversation")

    if message.get("extendedTextMessage"):
        return message.get("extendedTextMessage", {}).get("text", "")

    if message.get("imageMessage"):
        return message.get("imageMessage", {}).get("caption") or "Imagem recebida"

    if message.get("audioMessage"):
        return "Mensagem de áudio"

    if message.get("videoMessage"):
        return message.get("videoMessage", {}).get("caption") or "Vídeo recebido"

    if message.get("documentMessage"):
        return message.get("documentMessage", {}).get("fileName") or "Documento recebido"

    return ""


def obter_empresa_id():
    return int(os.getenv("WEBHOOK_EMPRESA_ID", "1"))


def obter_entrada_whatsapp(empresa_id):
    etapa = Pipeline.query.filter_by(
        nome="Entrada WhatsApp",
        empresa_id=empresa_id
    ).first()

    if etapa:
        return etapa

    etapa = Pipeline(
        nome="Entrada WhatsApp",
        ordem=0,
        empresa_id=empresa_id
    )

    db.session.add(etapa)
    db.session.commit()

    return etapa


@evolution_webhook_bp.route("/", methods=["POST"])
def receber():
    payload = request.get_json(silent=True) or {}

    dados = payload.get("data") or payload

    key = dados.get("key") or {}
    remote_jid = key.get("remoteJid") or dados.get("remoteJid") or ""
    from_me = key.get("fromMe", False)

    message = dados.get("message") or {}
    texto = extrair_texto(message)

    if not remote_jid or "@g.us" in remote_jid:
        return jsonify({"ok": True, "ignorado": "sem remote_jid ou grupo"})

    telefone = limpar_numero(remote_jid)

    if not telefone:
        return jsonify({"ok": True, "ignorado": "telefone vazio"})

    empresa_id = obter_empresa_id()

    lead = Lead.query.filter_by(
        empresa_id=empresa_id,
        telefone=telefone
    ).first()

    if not lead:
        etapa = obter_entrada_whatsapp(empresa_id)

        lead = Lead(
            nome=dados.get("pushName") or dados.get("name") or telefone,
            telefone=telefone,
            email=None,
            origem="whatsapp",
            produto_interesse="Atendimento WhatsApp",
            plano=None,
            valor=0.0,
            status="aberto",
            pipeline_id=etapa.id,
            empresa_id=empresa_id,
            usuario_id=None,
            criado_em=datetime.utcnow(),
            etapa_atualizada_em=datetime.utcnow()
        )

        db.session.add(lead)
        db.session.commit()

    if not texto:
        texto = "Mensagem recebida"

    mensagem = MensagemWhatsApp(
        empresa_id=empresa_id,
        lead_id=lead.id,
        usuario_id=None,
        telefone=telefone,
        nome_contato=lead.nome,
        direcao="enviada" if from_me else "recebida",
        mensagem=texto,
        tipo_mensagem="texto",
        status="recebida",
        lida=False,
        criado_em=datetime.utcnow()
    )

    db.session.add(mensagem)
    db.session.commit()

    return jsonify({"ok": True})