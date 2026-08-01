"""Testes de integração do webhook — FastAPI TestClient.

Testa o fluxo de webhook sem banco de dados real.
Usa mocking para simular pool e operações de fila.
"""

from unittest.mock import AsyncMock, patch

import fakeredis
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from whatsapp_langchain import __version__
from whatsapp_langchain.server.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def mock_db():
    """Mock do banco de dados e do Redis para testes sem infra real."""
    mock_pool = AsyncMock()
    fake_redis = fakeredis.FakeAsyncRedis()

    with (
        patch(
            "whatsapp_langchain.server.routes.health.check_db_health",
            return_value=True,
        ),
        patch(
            "whatsapp_langchain.server.routes.webhook.get_pool",
            return_value=mock_pool,
        ),
        patch(
            "whatsapp_langchain.server.routes.admin.get_pool",
            return_value=mock_pool,
        ),
        patch("whatsapp_langchain.shared.db.get_pool", return_value=mock_pool),
        patch("whatsapp_langchain.shared.db.run_migrations"),
        patch("whatsapp_langchain.shared.db.close_pool"),
        patch(
            "whatsapp_langchain.server.dependencies.get_redis",
            return_value=fake_redis,
        ),
    ):
        yield mock_pool


@pytest.fixture
def admin_session(monkeypatch):
    """Configura credenciais de admin e retorna um client autenticado (isolado)."""
    from whatsapp_langchain.shared.config import settings

    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", SecretStr("test-password"))

    authed_client = TestClient(app, raise_server_exceptions=False)
    login_response = authed_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "test-password"},
    )
    assert login_response.status_code == 200
    return authed_client


class TestHealthCheck:
    """Testes do endpoint /health."""

    def test_health_ok(self):
        """Retorna 200 quando o banco está acessível."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "database": "connected",
            "version": __version__,
        }


class TestWebhookSync:
    """Testes do webhook síncrono."""

    def test_sync_requires_agent(self):
        """Deve exigir o query param 'agent'."""
        response = client.post(
            "/webhook/sync",
            json={"phone": "+5511999999999", "message": "Olá"},
        )
        # Sem agent= -> 422 (query param obrigatório)
        assert response.status_code == 422

    def test_sync_nonexistent_agent(self):
        """Deve retornar erro para agente inexistente."""
        response = client.post(
            "/webhook/sync?agent=nao_existe",
            json={"phone": "+5511999999999", "message": "Olá"},
        )
        assert response.status_code == 400


class TestWebhookTwilio:
    """Testes do webhook Twilio."""

    def test_twilio_requires_agent(self):
        """Deve exigir o query param 'agent'."""
        response = client.post(
            "/webhook/twilio",
            data={
                "MessageSid": "SM123",
                "From": "whatsapp:+5511999999999",
                "To": "whatsapp:+14155238886",
                "Body": "Olá",
                "NumMedia": "0",
            },
        )
        # Sem agent= -> 422
        assert response.status_code == 422

    def test_twilio_nonexistent_agent(self):
        """Deve retornar erro para agente inexistente."""
        response = client.post(
            "/webhook/twilio?agent=nao_existe",
            data={
                "MessageSid": "SM123",
                "From": "whatsapp:+5511999999999",
                "To": "whatsapp:+14155238886",
                "Body": "Olá",
                "NumMedia": "0",
            },
        )
        assert response.status_code == 400

    @patch("whatsapp_langchain.server.routes.webhook.enqueue_or_buffer")
    def test_twilio_enqueues_message(self, mock_enqueue):
        """Deve enfileirar mensagem e retornar TwiML vazio."""
        from whatsapp_langchain.shared.models import EnqueueResult

        mock_enqueue.return_value = EnqueueResult(message_id=1, is_buffered=False)

        response = client.post(
            "/webhook/twilio?agent=rhawk_assistant",
            data={
                "MessageSid": "SM123",
                "From": "whatsapp:+5511999999999",
                "To": "whatsapp:+14155238886",
                "Body": "Olá",
                "NumMedia": "0",
            },
        )
        assert response.status_code == 200
        assert "Response" in response.text

    def test_twilio_openapi_exposes_form_fields(self):
        """Swagger deve exibir body form-encoded para teste manual."""
        openapi = client.get("/openapi.json").json()
        post = openapi["paths"]["/webhook/twilio"]["post"]
        assert "requestBody" in post

        form_content = post["requestBody"]["content"][
            "application/x-www-form-urlencoded"
        ]
        schema = form_content["schema"]
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            schema = openapi["components"]["schemas"][ref_name]

        properties = schema["properties"]
        assert "MessageSid" in properties
        assert "From" in properties
        assert "To" in properties
        assert "Body" in properties
        assert "NumMedia" in properties


class TestAdminRoutes:
    """Testes das rotas administrativas."""

    def test_list_agents_requires_auth(self):
        """Sem sessão de admin, deve retornar 401."""
        response = TestClient(app, raise_server_exceptions=False).get("/api/agents")
        assert response.status_code == 401

    def test_list_agents(self, admin_session):
        """Deve listar agentes disponíveis quando autenticado."""
        response = admin_session.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "rhawk_assistant" in data["agents"]
