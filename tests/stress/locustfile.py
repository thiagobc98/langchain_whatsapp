"""Stress test do webhook Twilio via Locust.

Simula múltiplos usuários enviando mensagens simultâneas para
/webhook/twilio, exercitando o pipeline completo: rate limit (Redis),
debounce/fila (PostgreSQL) e worker.

IMPORTANTE: só rode contra a stack local (`make up`), com
VALIDATE_TWILIO_SIGNATURE=false. O Locust não consegue gerar uma
assinatura HMAC-SHA1 válida do Twilio, então com validação habilitada
todas as requisições seriam rejeitadas com 403. Nunca aponte isto para
produção.

Uso:
    make stress            # modo UI (http://localhost:8089)
    make stress-headless    # modo headless, ex: 50 usuários

Direto com uv:
    uv run --extra stress locust -f tests/stress/locustfile.py --host http://localhost:8000
"""

import os
import uuid

from locust import HttpUser, between, task

AGENT_ID = os.getenv("LOCUST_AGENT_ID", "rhawk_assistant")

# Pool fixo de números de telefone — reutilizados entre requisições para
# exercitar debounce (mensagens agrupadas) e rate limit (por telefone) de
# forma realista, em vez de cada requisição ser um usuário "novo".
PHONE_POOL = [f"+5511900{n:06d}" for n in range(50)]

SAMPLE_MESSAGES = [
    "Olá, quero saber mais sobre o produto.",
    "Qual o horário de atendimento?",
    "Preciso de ajuda com meu pedido.",
    "Vocês têm desconto para pagamento à vista?",
    "Como faço para cancelar minha assinatura?",
]


class TwilioWebhookUser(HttpUser):
    """Simula um cliente WhatsApp enviando mensagens via webhook Twilio."""

    wait_time = between(1, 3)

    @task
    def send_message(self) -> None:
        phone = PHONE_POOL[uuid.uuid4().int % len(PHONE_POOL)]
        message = SAMPLE_MESSAGES[uuid.uuid4().int % len(SAMPLE_MESSAGES)]

        self.client.post(
            f"/webhook/twilio?agent={AGENT_ID}",
            data={
                "MessageSid": f"SM{uuid.uuid4().hex[:24]}",
                "From": f"whatsapp:{phone}",
                "To": "whatsapp:+14155238886",
                "Body": message,
                "NumMedia": "0",
            },
            name="/webhook/twilio",
        )
