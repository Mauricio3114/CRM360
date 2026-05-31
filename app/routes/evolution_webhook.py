import os
from datetime import datetime

from flask import Blueprint, request, jsonify

from app import db
from app.models.lead import Lead
from app.models.pipeline import Pipeline
from app.models.mensagem_whatsapp import MensagemWhatsApp
from app.models.lid_mapping import LidMapping

from app.services.whatsapp_qr_cache import salvar_qr


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


@evolution_webhook_bp.route("", methods=["POST"])
@evolution_webhook_bp.route("/", methods=["POST"])
def receber():

    print("WEBHOOK EVOLUTION CHEGOU", flush=True)

    payload = request.get_json(silent=True) or {}

    print("PAYLOAD WEBHOOK:", payload, flush=True)

    # ignora eventos que não são messages.upsert
    evento = payload.get("event", "")
    if evento != "messages.upsert":
        print(f"WEBHOOK IGNORADO: evento={evento}", flush=True)
        return jsonify({"ok": True, "ignorado": f"evento={evento}"})

    dados = payload.get("data") or payload

    # se data vier como lista, ignora
    if isinstance(dados, list):
        print("WEBHOOK IGNORADO: data é lista", flush=True)
        return jsonify({"ok": True, "ignorado": "data lista"})

    print("DADOS RECEBIDOS:", dados, flush=True)

    key = dados.get("key") or {}
    remote_jid = key.get("remoteJid") or dados.get("remoteJid") or ""
    from_me = key.get("fromMe", False)

    message = dados.get("message") or {}
    texto = extrair_texto(message)

    print("REMOTE_JID:", remote_jid, flush=True)
    print("TEXTO EXTRAIDO:", texto, flush=True)
    print("FROM_ME:", from_me, flush=True)

    if not remote_jid or "@g.us" in remote_jid:
        print("WEBHOOK IGNORADO: sem remote_jid ou grupo", flush=True)
        return jsonify({"ok": True, "ignorado": "sem remote_jid ou grupo"})

    empresa_id = obter_empresa_id()

    # ✅ Tratamento de @lid
    if "@lid" in remote_jid:
        if from_me:
            print("WEBHOOK IGNORADO: fromMe=True com @lid", flush=True)
            return jsonify({"ok": True, "ignorado": "fromMe lid"})

        push_name = dados.get("pushName") or ""
        instance_name = payload.get("instance", "")

        print(f"REMOTE_JID é @lid, pushName={push_name}", flush=True)

        # 1. Tenta resolver pelo LidMapping
        mapping = LidMapping.query.filter_by(
            lid_jid=remote_jid,
            instance_name=instance_name
        ).first()

        if mapping:
            telefone = limpar_numero(mapping.numero_real)
            print(f"@lid RESOLVIDO pelo mapping: {telefone}", flush=True)
        else:
            telefone = None

        # 2. Busca lead pelo telefone resolvido ou pelo nome
        lead = None

        if telefone:
            lead = Lead.query.filter_by(
                empresa_id=empresa_id,
                telefone=telefone
            ).first()

        if not lead and push_name:
            lead = Lead.query.filter(
                Lead.empresa_id == empresa_id,
                Lead.nome.ilike(f"%{push_name}%")
            ).first()

            if lead:
                print(f"@lid RESOLVIDO por nome: {lead.telefone}", flush=True)
                # Salva mapping para o futuro
                novo_mapping = LidMapping(
                    lid_jid=remote_jid,
                    numero_real=lead.telefone,
                    instance_name=instance_name
                )
                db.session.add(novo_mapping)
                db.session.commit()
                telefone = lead.telefone

        if not lead:
            # Cria lead novo com @lid como telefone temporário
            telefone_lid = limpar_numero(remote_jid)
            etapa = obter_entrada_whatsapp(empresa_id)
            lead = Lead(
                nome=push_name or telefone_lid,
                telefone=telefone_lid,
                email=None,
                origem="whatsapp_lid",
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
            telefone = telefone_lid
            print("NOVO LEAD @lid CRIADO:", lead.id, flush=True)
        else:
            print("LEAD @lid ENCONTRADO:", lead.id, flush=True)

        if not texto:
            texto = "Mensagem recebida"

        mensagem = MensagemWhatsApp(
            empresa_id=empresa_id,
            lead_id=lead.id,
            usuario_id=None,
            telefone=telefone,
            nome_contato=lead.nome,
            direcao="recebida",
            mensagem=texto,
            tipo_mensagem="texto",
            status="recebida",
            lida=False,
            criado_em=datetime.utcnow()
        )
        db.session.add(mensagem)
        db.session.commit()
        print("MENSAGEM @lid SALVA:", mensagem.id, flush=True)
        return jsonify({"ok": True})

    # ✅ Fluxo normal para @s.whatsapp.net
    telefone = limpar_numero(remote_jid)

    print("TELEFONE:", telefone, flush=True)

    if not telefone:
        print("WEBHOOK IGNORADO: telefone vazio", flush=True)
        return jsonify({"ok": True, "ignorado": "telefone vazio"})

    print("EMPRESA_ID:", empresa_id, flush=True)

    lead = Lead.query.filter_by(
        empresa_id=empresa_id,
        telefone=telefone
    ).first()

    if not lead:
        print("LEAD NÃO ENCONTRADO. CRIANDO NOVO LEAD.", flush=True)

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

        print("NOVO LEAD CRIADO:", lead.id, flush=True)

    else:
        print("LEAD ENCONTRADO:", lead.id, flush=True)

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

    print("MENSAGEM WHATSAPP SALVA:", mensagem.id, flush=True)

    return jsonify({"ok": True})


@evolution_webhook_bp.route("/qrcode-updated", methods=["POST"])
def qrcode_updated():
    payload = request.get_json(silent=True) or {}

    dados = payload.get("data") or {}
    qrcode = dados.get("qrcode") or {}

    instance_name = (
        qrcode.get("instance")
        or payload.get("instance")
        or dados.get("instance")
    )

    qr_base64 = qrcode.get("base64")

    salvar_qr(instance_name, qr_base64)

    print("WEBHOOK QR SALVO:", instance_name, bool(qr_base64), flush=True)

    return jsonify({"ok": True}), 200


@evolution_webhook_bp.route("/connection-update", methods=["POST"])
def connection_update():
    payload = request.get_json(silent=True) or {}

    print("WEBHOOK CONEXAO RECEBIDO:", payload, flush=True)

    return jsonify({"ok": True, "evento": "connection.update"}), 200