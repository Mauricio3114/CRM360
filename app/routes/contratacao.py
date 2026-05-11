import secrets
import string

from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_mail import Message
from werkzeug.security import generate_password_hash

from app import db, mail
from app.models.assinatura import Assinatura
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.services.asaas_service import AsaasService


contratacao_bp = Blueprint("contratacao", __name__, url_prefix="")


def gerar_senha_temporaria(tamanho=10):
    caracteres = string.ascii_letters + string.digits
    return "".join(
        secrets.choice(caracteres)
        for _ in range(tamanho)
    )


@contratacao_bp.route("/contratar", methods=["GET", "POST"])
def contratar():
    if request.method == "POST":
        nome = request.form.get("nome")
        empresa_nome = request.form.get("empresa")
        email = request.form.get("email")
        telefone = request.form.get("telefone")
        plano = request.form.get("plano")

        if not nome or not empresa_nome or not email or not plano:
            flash("Preencha todos os campos obrigatórios.", "danger")
            return redirect(url_for("contratacao.contratar"))

        usuario_existente = Usuario.query.filter_by(email=email).first()

        if usuario_existente:
            flash("Já existe um usuário cadastrado com esse e-mail.", "warning")
            return redirect(url_for("contratacao.contratar"))

        valores = {
            "basico": 97.00,
            "pro": 197.00,
            "premium": 297.00
        }

        valor = valores.get(plano, 97.00)

        trial_ate = datetime.utcnow() + timedelta(days=14)

        try:
            asaas_customer_id = None
            asaas_payment_id = None

            asaas = AsaasService()

            cliente_asaas = asaas.criar_cliente(
                nome=nome,
                email=email,
                telefone=telefone
            )

            if cliente_asaas and cliente_asaas.get("id"):
                asaas_customer_id = cliente_asaas.get("id")

                assinatura_asaas = asaas.criar_assinatura_mensal(
                    customer_id=asaas_customer_id,
                    valor=valor,
                    descricao=f"Assinatura MaVa CRM - Plano {plano.upper()}",
                    dias_para_primeira_cobranca=14
                )

                if assinatura_asaas:
                    asaas_payment_id = (
                        assinatura_asaas.get("id")
                        or assinatura_asaas.get("payment")
                    )

            empresa = Empresa(
                nome=empresa_nome,
                plano=plano
            )

            db.session.add(empresa)
            db.session.flush()

            senha_temporaria = gerar_senha_temporaria()

            usuario = Usuario(
                nome=nome,
                email=email,
                senha=generate_password_hash(senha_temporaria),
                tipo="admin",
                empresa_id=empresa.id
            )

            db.session.add(usuario)
            db.session.flush()

            assinatura = Assinatura(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                nome_cliente=nome,
                nome_empresa=empresa_nome,
                email=email,
                telefone=telefone,
                plano=plano,
                valor=valor,
                asaas_customer_id=asaas_customer_id,
                asaas_payment_id=asaas_payment_id,
                status="trial",
                status_trial="ativo",
                trial_ate=trial_ate,
                data_vencimento=trial_ate,
                origem="contratacao_online"
            )

            db.session.add(assinatura)
            db.session.commit()

            try:
                msg = Message(
                    subject="Seu acesso ao MaVa CRM",
                    recipients=[email]
                )

                msg.body = f"""
Olá, {nome}!

Seu teste grátis do MaVa CRM foi ativado com sucesso 🚀

Você tem 14 dias gratuitos para testar a plataforma.

Dados de acesso:

Link:
https://www.mavacrm.com.br/login

E-mail:
{email}

Senha temporária:
{senha_temporaria}

Plano escolhido:
{plano.upper()}

Seu teste grátis vai até:
{trial_ate.strftime("%d/%m/%Y")}

Após o período gratuito, sua assinatura mensal será cobrada conforme o plano escolhido.

Recomendamos alterar sua senha após o primeiro acesso.

Bem-vindo ao MaVa CRM.
"""

                mail.send(msg)

            except Exception as e:
                print("ERRO AO ENVIAR EMAIL DE CONTRATAÇÃO:", e)

            flash(
                "Conta criada com sucesso! Enviamos o acesso para seu e-mail.",
                "success"
            )

            return redirect(url_for("auth.login"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar sua conta: {e}", "danger")

    return render_template("contratar.html")