from app import create_app, db
from app.models.tarefa import Tarefa
from app.models.lead import Lead
from datetime import datetime
import time

# 👇 NOVO IMPORT
from app.services.whatsapp import enviar_whatsapp_real

app = create_app()


def enviar_whatsapp_fake(telefone, mensagem):
    print(f"[ENVIO WHATSAPP FAKE] Para: {telefone}")
    print(f"Mensagem: {mensagem}")
    print("-" * 40)


def processar_tarefas():
    agora = datetime.now()

    tarefas = Tarefa.query.filter(
        Tarefa.status == "pendente",
        Tarefa.enviar_whatsapp == True,
        Tarefa.data_tarefa <= agora
    ).all()

    for tarefa in tarefas:
        lead = db.session.get(Lead, tarefa.lead_id)

        if not lead or not lead.telefone:
            continue

        mensagem = tarefa.mensagem_whatsapp or f"Olá {lead.nome}, estou retornando seu atendimento."

        # 🔥 AQUI ESTÁ O PODER
        if "SEU_TOKEN_AQUI" in enviar_whatsapp_real.__code__.co_consts:
            enviar_whatsapp_fake(lead.telefone, mensagem)
        else:
            enviar_whatsapp_real(lead.telefone, mensagem)

        tarefa.status = "concluida"

    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        print("🚀 Disparador iniciado...")

        while True:
            processar_tarefas()
            time.sleep(30)