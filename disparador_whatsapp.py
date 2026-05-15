from app import create_app, db
from app.models.tarefa import Tarefa
from app.models.lead import Lead
from app.models.interacao import Interacao
from app.services.whatsapp_qr_service import EvolutionAPIService

from datetime import datetime
from zoneinfo import ZoneInfo
import time


INSTANCE_NAME = "mava_novo"
TZ = ZoneInfo("America/Fortaleza")

app = create_app()


def agora_brasil_naive():
    return datetime.now(TZ).replace(tzinfo=None)


def limpar_numero(numero):
    if not numero:
        return ""

    numero = (
        str(numero)
        .replace("(", "")
        .replace(")", "")
        .replace("-", "")
        .replace(" ", "")
        .replace("+", "")
        .strip()
    )

    numero = "".join(filter(str.isdigit, numero))

    if numero and not numero.startswith("55"):
        numero = f"55{numero}"

    return numero


def registrar_interacao(tarefa, lead, tipo, descricao):
    try:
        interacao = Interacao(
            lead_id=lead.id,
            empresa_id=tarefa.empresa_id,
            usuario_id=tarefa.usuario_id,
            tipo=tipo,
            descricao=descricao
        )

        db.session.add(interacao)

    except Exception as erro:
        print(f"[AVISO] Não conseguiu registrar interação: {erro}")


def processar_tarefas():
    agora = agora_brasil_naive()

    tarefas = Tarefa.query.filter(
        Tarefa.status == "pendente",
        Tarefa.enviar_whatsapp == True,
        Tarefa.data_tarefa <= agora
    ).order_by(Tarefa.data_tarefa.asc()).all()

    if not tarefas:
        print(f"[{agora.strftime('%d/%m/%Y %H:%M:%S')}] Nenhuma tarefa para disparar.")
        return

    service = EvolutionAPIService()

    for tarefa in tarefas:
        print(f"[ANALISANDO] Tarefa {tarefa.id} - {tarefa.titulo}")

        lead = db.session.get(Lead, tarefa.lead_id)

        if not lead:
            print(f"[ERRO] Tarefa {tarefa.id} sem lead vinculado.")
            registrar_interacao(
                tarefa,
                Lead.query.filter_by(empresa_id=tarefa.empresa_id).first(),
                "Follow-up erro",
                f"Tarefa {tarefa.id} sem lead vinculado."
            )
            continue

        if not lead.telefone:
            print(f"[ERRO] Lead {lead.nome} sem telefone.")
            registrar_interacao(
                tarefa,
                lead,
                "Follow-up erro",
                "Não enviou WhatsApp automático: lead sem telefone."
            )
            continue

        numero = limpar_numero(lead.telefone)

        if not numero:
            print(f"[ERRO] Telefone inválido no lead {lead.nome}.")
            registrar_interacao(
                tarefa,
                lead,
                "Follow-up erro",
                "Não enviou WhatsApp automático: telefone inválido."
            )
            continue

        jid = f"{numero}@s.whatsapp.net"

        mensagem = (
            tarefa.mensagem_whatsapp
            or tarefa.descricao
            or f"Olá {lead.nome}, tudo bem? Estou retornando seu atendimento."
        ).strip()

        print(f"[DISPARANDO] Tarefa {tarefa.id} para {jid}")
        print(f"[MENSAGEM] {mensagem}")

        try:
            resultado = service.enviar_mensagem(
                INSTANCE_NAME,
                jid,
                mensagem
            )

        except Exception as erro:
            resultado = {
                "ok": False,
                "erro": str(erro)
            }

        if resultado.get("ok"):
            tarefa.status = "concluida"

            registrar_interacao(
                tarefa,
                lead,
                "Follow-up WhatsApp enviado",
                f"Mensagem automática enviada pelo agendamento: {mensagem}"
            )

            print(f"[OK] Mensagem enviada para {lead.nome}")

        else:
            registrar_interacao(
                tarefa,
                lead,
                "Follow-up WhatsApp erro",
                f"Erro ao enviar mensagem automática. Retorno: {resultado}"
            )

            print(f"[ERRO] Não enviou para {lead.nome}: {resultado}")

    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        print("🚀 Disparador WhatsApp Evolution iniciado...")
        print(f"📱 Instância: {INSTANCE_NAME}")
        print("⏱️ Verificando tarefas a cada 30 segundos...")

        while True:
            processar_tarefas()
            time.sleep(30)