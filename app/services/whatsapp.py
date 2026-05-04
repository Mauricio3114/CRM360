import requests
import os

# ⚠️ DEPOIS TU PREENCHE ISSO
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN") or "SEU_TOKEN_AQUI"
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID") or "SEU_PHONE_ID_AQUI"


def enviar_whatsapp_real(telefone, mensagem):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {
            "body": mensagem
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            print(f"[WHATSAPP REAL] Enviado para {telefone}")
        else:
            print(f"[ERRO WHATSAPP] {response.text}")

    except Exception as e:
        print(f"[ERRO EXCEPTION] {e}")