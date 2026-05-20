import os
import requests
from datetime import datetime


class EvolutionAPIService:

    def __init__(self):

        self.base_url = os.getenv(
            "EVOLUTION_API_URL",
            "http://localhost:8080"
        ).rstrip("/")

        self.api_key = os.getenv(
            "EVOLUTION_API_KEY",
            "mava123"
        )

        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    def formatar_numero(self, jid):

        if not jid:
            return "Contato"

        numero = (
            jid.replace("@s.whatsapp.net", "")
            .replace("@lid", "")
            .replace("@g.us", "")
        )

        if numero.startswith("55") and len(numero) >= 12:

            ddd = numero[2:4]
            telefone = numero[4:]

            if len(telefone) == 9:
                return f"({ddd}) {telefone[:5]}-{telefone[5:]}"

            elif len(telefone) == 8:
                return f"({ddd}) {telefone[:4]}-{telefone[4:]}"

        return numero

    def formatar_timestamp(self, timestamp):

        try:

            timestamp = int(timestamp)

            if timestamp > 9999999999:
                timestamp = timestamp / 1000

            data = datetime.fromtimestamp(timestamp)

            return data.strftime("%H:%M")

        except Exception:
            return "agora"

    def extrair_nome_conversa(self, conversa):

        nome = (
            conversa.get("name")
            or conversa.get("pushName")
            or conversa.get("notify")
            or conversa.get("contactName")
            or conversa.get("profileName")
        )

        remote_jid = conversa.get("remoteJid", "")

        if not nome:
            nome = self.formatar_numero(remote_jid)

        return nome

    def extrair_texto_mensagem(self, msg):

        if not isinstance(msg, dict):
            return ""

        message = msg.get("message") or msg.get("lastMessage") or {}

        if isinstance(message, str):
            return message

        if not isinstance(message, dict):
            return ""

        texto = (
            message.get("conversation")
            or message.get("text")
            or message.get("caption")
        )

        if texto:
            return texto

        if message.get("extendedTextMessage"):
            return message.get("extendedTextMessage", {}).get("text", "")

        if message.get("imageMessage"):
            return message.get("imageMessage", {}).get("caption") or "Imagem recebida/enviada"

        if message.get("audioMessage"):
            return "Mensagem de áudio"

        if message.get("videoMessage"):
            return message.get("videoMessage", {}).get("caption") or "Vídeo recebido/enviado"

        if message.get("documentMessage"):
            return message.get("documentMessage", {}).get("fileName") or "Documento"

        return ""

    def criar_instancia(self, instance_name="mava_crm"):

        url = f"{self.base_url}/instance/create"

        payload = {
            "instanceName": instance_name,
            "integration": "WHATSAPP-BAILEYS",
            "qrcode": True
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            timeout=30
        )

        try:
            data = response.json()

        except Exception:
            data = {"erro": response.text}

        return {
            "ok": response.status_code in [200, 201],
            "status_code": response.status_code,
            "data": data
        }

    def conectar_qr(self, instance_name):

        try:

            url = f"{self.base_url}/instance/connect/{instance_name}"

            response = requests.get(
                url,
                headers=self.headers,
                timeout=60
            )

            print("STATUS CONNECT:", response.status_code, flush=True)
            print("TEXT CONNECT:", response.text, flush=True)

            try:
                data = response.json()

            except Exception:
                data = {
                    "raw": response.text
                }

            qr_code = (
                data.get("base64")
                or data.get("qrcode")
                or data.get("qr")
                or data.get("code")
                or data.get("data", {}).get("base64")
                or data.get("data", {}).get("qrcode")
                or data.get("data", {}).get("qr")
            )

            return {
                "ok": response.status_code in [200, 201],
                "status_code": response.status_code,
                "data": data,
                "qr_base64": qr_code,
                "qr_code": qr_code,
                "pairing_code": data.get("pairingCode")
            }

        except Exception as e:

            print("ERRO CONNECT QR:", str(e), flush=True)

            return {
                "ok": False,
                "erro": str(e)
            }

        def deletar_instancia(self, instance_name="mava_crm"):

            url = f"{self.base_url}/instance/delete/{instance_name}"

            response = requests.delete(
                url,
                headers=self.headers,
                timeout=30
            )

        try:
            data = response.json()

        except Exception:
            data = {"retorno": response.text}

        return {
            "ok": response.status_code in [200, 201],
            "status_code": response.status_code,
            "data": data
        }

    def buscar_conversas(self, instance_name="mava_novo"):

        url = f"{self.base_url}/chat/findChats/{instance_name}"

        response = requests.post(
            url,
            headers=self.headers,
            json={},
            timeout=60
        )

        try:
            data = response.json()

        except Exception:
            data = []

        conversas = []

        if isinstance(data, list):

            for conversa in data:

                remote_jid = conversa.get("remoteJid")

                if not remote_jid:
                    continue

                nome = self.extrair_nome_conversa(conversa)

                ultima_mensagem = (
                    conversa.get("lastMessage")
                    or conversa.get("lastMessageText")
                    or conversa.get("conversation")
                    or conversa.get("message")
                    or ""
                )

                if isinstance(ultima_mensagem, dict):
                    ultima_mensagem = (
                        ultima_mensagem.get("conversation")
                        or ultima_mensagem.get("text")
                        or ultima_mensagem.get("caption")
                        or "Nova mensagem"
                    )

                if not ultima_mensagem:
                    ultima_mensagem = "Clique para abrir conversa"

                timestamp = (
                    conversa.get("updatedAt")
                    or conversa.get("conversationTimestamp")
                    or conversa.get("messageTimestamp")
                    or conversa.get("lastMessageTimestamp")
                    or 0
                )

                unread_count = (
                    conversa.get("unreadCount")
                    or conversa.get("unread_count")
                    or conversa.get("unreadMessages")
                    or 0
                )

                try:
                    unread_count = int(unread_count)
                except Exception:
                    unread_count = 0

                conversa["nome_formatado"] = nome

                conversa["numero_formatado"] = (
                    self.formatar_numero(remote_jid)
                )

                conversa["hora_formatada"] = (
                    self.formatar_timestamp(timestamp)
                )

                conversa["ultima_mensagem"] = ultima_mensagem

                conversa["timestamp"] = timestamp

                conversa["unread_count"] = unread_count

                conversas.append(conversa)

            conversas = sorted(
                conversas,
                key=lambda x: x.get("timestamp", 0),
                reverse=True
            )

            conversas = conversas[:30]

        return {
            "ok": response.status_code in [200, 201],
            "status_code": response.status_code,
            "data": conversas
        }

    def buscar_mensagens(self, instance_name, remote_jid):

        url = f"{self.base_url}/chat/findMessages/{instance_name}"

        numero_base = (
            remote_jid
            .replace("@s.whatsapp.net", "")
            .replace("@lid", "")
            .replace("@g.us", "")
        )

        variacoes = [
            f"{numero_base}@s.whatsapp.net",
            numero_base
        ]

        if numero_base.startswith("55"):
            sem_55 = numero_base[2:]
            variacoes.append(f"{sem_55}@s.whatsapp.net")
            variacoes.append(sem_55)

        mensagens_unicas = []
        ids_vistos = set()

        for jid_teste in variacoes:

            payload = {
                "where": {
                    "key": {
                        "remoteJid": jid_teste
                    }
                },
                "limit": 100
            }

            try:

                response = requests.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )

                try:
                    data = response.json()
                except Exception:
                    data = {}

                print("STATUS FIND MESSAGES:", response.status_code, flush=True)
                print("BUSCANDO JID:", jid_teste, flush=True)
                print("RETORNO FIND MESSAGES:", data, flush=True)

                mensagens = []

                if isinstance(data, dict):

                    if isinstance(data.get("messages"), dict):
                        mensagens = (
                            data.get("messages", {}).get("records")
                            or data.get("messages", {}).get("rows")
                            or []
                        )

                    elif isinstance(data.get("messages"), list):
                        mensagens = data.get("messages")

                    elif isinstance(data.get("records"), list):
                        mensagens = data.get("records")

                    elif isinstance(data.get("data"), list):
                        mensagens = data.get("data")

                    elif isinstance(data.get("data"), dict):
                        mensagens = (
                            data.get("data", {}).get("records")
                            or data.get("data", {}).get("messages")
                            or []
                        )

                elif isinstance(data, list):
                    mensagens = data

                for msg in mensagens:

                    if not isinstance(msg, dict):
                        continue

                    key = msg.get("key", {})
                    msg_id = key.get("id") or msg.get("id")

                    if not msg_id:
                        msg_id = str(msg)

                    if msg_id in ids_vistos:
                        continue

                    ids_vistos.add(msg_id)

                    timestamp = (
                        msg.get("messageTimestamp")
                        or msg.get("timestamp")
                        or msg.get("createdAt")
                        or 0
                    )

                    msg["hora_formatada"] = self.formatar_timestamp(timestamp)

                    mensagens_unicas.append(msg)

            except Exception as erro:
                print("ERRO BUSCA MENSAGENS:", erro, flush=True)

        if not mensagens_unicas:
            mensagens_unicas = self.buscar_ultima_mensagem_por_chats(
                instance_name,
                remote_jid
            )

        mensagens_unicas = sorted(
            mensagens_unicas,
            key=lambda x: (
                x.get("messageTimestamp")
                or x.get("timestamp")
                or 0
            )
        )

        return {
            "ok": True,
            "status_code": 200,
            "data": mensagens_unicas
        }


    def buscar_ultima_mensagem_por_chats(self, instance_name, remote_jid):

        url = f"{self.base_url}/chat/findChats/{instance_name}"

        response = requests.post(
            url,
            headers=self.headers,
            json={},
            timeout=60
        )

        try:
            data = response.json()
        except Exception:
            data = []

        print("FALLBACK FIND CHATS STATUS:", response.status_code, flush=True)
        print("FALLBACK FIND CHATS RETORNO:", data, flush=True)

        mensagens = []

        if not isinstance(data, list):
            return mensagens

        numero_busca = (
            remote_jid
            .replace("@s.whatsapp.net", "")
            .replace("@lid", "")
            .replace("@g.us", "")
        )

        if numero_busca.startswith("55"):
            numero_busca_sem55 = numero_busca[2:]
        else:
            numero_busca_sem55 = numero_busca

        for conversa in data:

            if not isinstance(conversa, dict):
                continue

            conversa_jid = conversa.get("remoteJid") or ""

            numero_conversa = (
                conversa_jid
                .replace("@s.whatsapp.net", "")
                .replace("@lid", "")
                .replace("@g.us", "")
            )

            match = (
                numero_conversa == numero_busca
                or numero_conversa == numero_busca_sem55
                or numero_busca in numero_conversa
                or numero_busca_sem55 in numero_conversa
            )

            if not match:
                continue

            ultima_msg = (
                conversa.get("lastMessage")
                or conversa.get("lastMessageText")
                or conversa.get("conversation")
                or conversa.get("message")
                or ""
            )

            if isinstance(ultima_msg, dict):
                ultima_msg = (
                    ultima_msg.get("conversation")
                    or ultima_msg.get("text")
                    or ultima_msg.get("caption")
                    or ""
                )

            timestamp = (
                conversa.get("updatedAt")
                or conversa.get("conversationTimestamp")
                or conversa.get("messageTimestamp")
                or conversa.get("lastMessageTimestamp")
                or 0
            )

            if ultima_msg:

                mensagens.append({
                    "key": {
                        "id": f"fallback-{conversa_jid}-{timestamp}",
                        "remoteJid": remote_jid,
                        "fromMe": False
                    },
                    "messageTimestamp": timestamp,
                    "hora_formatada": self.formatar_timestamp(timestamp),
                    "message": {
                        "conversation": ultima_msg
                    }
                })

        return mensagens

    def enviar_mensagem(self, instance_name, remote_jid, mensagem):

        url = f"{self.base_url}/message/sendText/{instance_name}"

        numero = remote_jid or ""

        if "@s.whatsapp.net" in numero:
            numero = numero.replace("@s.whatsapp.net", "")

        if "@lid" in numero:

            return {
                "ok": False,
                "status_code": 400,
                "data": {
                    "erro": (
                        "Este contato veio como @lid. "
                        "Precisamos mapear o número real."
                    )
                }
            }

        payload = {
            "number": numero,
            "text": mensagem
        }

        response = requests.post(
            url,
            headers=self.headers,
            json=payload,
            timeout=60
        )

        try:
            data = response.json()

        except Exception:
            data = {"retorno": response.text}

        return {
            "ok": response.status_code in [200, 201],
            "status_code": response.status_code,
            "data": data
        }

    def enviar_arquivo(
        self,
        instance_name,
        remote_jid,
        arquivo_path,
        legenda=None
    ):

        url = f"{self.base_url}/message/sendMedia/{instance_name}"

        numero = remote_jid or ""

        if "@s.whatsapp.net" in numero:
            numero = numero.replace("@s.whatsapp.net", "")

        with open(arquivo_path, "rb") as arquivo:

            files = {
                "medias": arquivo
            }

            data = {
                "number": numero,
                "caption": legenda or ""
            }

            headers = {
                "apikey": self.api_key
            }

            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=120
            )

        try:
            retorno = response.json()

        except Exception:
            retorno = {
                "retorno": response.text
            }

        return {
            "ok": response.status_code in [200, 201],
            "status_code": response.status_code,
            "data": retorno
        }