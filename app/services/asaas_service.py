import os
import requests
from datetime import date, timedelta


class AsaasService:

    def __init__(self):
        self.base_url = "https://api.asaas.com/v3"

        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "access_token": os.getenv("ASAAS_API_KEY")
        }

    def criar_cliente(
        self,
        nome,
        email,
        telefone=None,
        cpf_cnpj=None
    ):
        url = f"{self.base_url}/customers"

        payload = {
            "name": nome,
            "email": email,
        }

        if telefone:
            payload["mobilePhone"] = telefone

        if cpf_cnpj:
            payload["cpfCnpj"] = cpf_cnpj

        response = requests.post(
            url,
            json=payload,
            headers=self.headers
        )

        return response.json()

    def criar_cobranca(
        self,
        customer_id,
        valor,
        descricao="Assinatura MaVa CRM",
        dias_para_vencer=1
    ):
        url = f"{self.base_url}/payments"

        vencimento = date.today() + timedelta(days=dias_para_vencer)

        payload = {
            "customer": customer_id,
            "billingType": "UNDEFINED",
            "value": valor,
            "description": descricao,
            "dueDate": vencimento.strftime("%Y-%m-%d")
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers
        )

        return response.json()

    def criar_assinatura_mensal(
        self,
        customer_id,
        valor,
        descricao="Assinatura mensal MaVa CRM",
        dias_para_primeira_cobranca=14
    ):
        url = f"{self.base_url}/subscriptions"

        proximo_vencimento = date.today() + timedelta(
            days=dias_para_primeira_cobranca
        )

        payload = {
            "customer": customer_id,
            "billingType": "UNDEFINED",
            "value": valor,
            "nextDueDate": proximo_vencimento.strftime("%Y-%m-%d"),
            "cycle": "MONTHLY",
            "description": descricao
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers
        )

        return response.json()