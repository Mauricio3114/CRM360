from app import create_app, db
from app.models.tarefa import Tarefa
from app.models.lead import Lead
from app.services.whatsapp_qr_service import EvolutionAPIService

from datetime import datetime
from zoneinfo import ZoneInfo
import time


INSTANCE_NAME = "mava_novo"
TZ = ZoneInfo("America/Fortaleza")

app = create_app()


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


def processar_tarefas():
    agora = datetime.now(TZ).replace(tzinfo=None)

    tarefas = Tarefa.query.filter(
        Tarefa.status == "pendente",
        Tarefa.enviar_whatsapp == True,
        Tarefa.data_tarefa <= agora
    ).all()

    if not tarefas:
        print(f"[{agora}] Nenhuma tarefa para disparar.")
        return

    service = EvolutionAPIService()

    for tarefa in tarefas:
        lead = db.session.get(Lead, tarefa.lead_id)

        if not lead or not lead.telefone:
            print(f"[ERRO] Tarefa {tarefa.id} sem lead ou telefone.")
            continue

        numero = limpar_numero(lead.telefone)
        jid = f"{numero}@s.whatsapp.net"

        mensagem = (
            tarefa.mensagem_whatsapp
            or f"Olá {lead.nome}, tudo bem? Estou retornando seu atendimento."
        )

        print(f"[DISPARANDO] Tarefa {tarefa.id} para {jid}")

        resultado = service.enviar_mensagem(
            INSTANCE_NAME,
            jid,
            mensagem
        )

        if resultado.get("ok"):
            tarefa.status = "concluida"
            print(f"[OK] Mensagem enviada para {lead.nome}")
        else:
            print(f"[ERRO] Não enviou para {lead.nome}: {resultado}")

    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        print("🚀 Disparador WhatsApp Evolution iniciado...")

        while True:
            processar_tarefas()
            time.sleep(30)