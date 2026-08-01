"""FastAPI dependencies para validação e rate limiting.

Dependencies são injetadas automaticamente nas rotas via Depends().
Centralizar aqui mantém as rotas limpas e focadas na lógica de negócio.

Uso:
    from whatsapp_langchain.server.dependencies import check_rate_limit

    @router.post("/webhook/twilio")
    async def webhook(rate_limit: None = Depends(check_rate_limit)):
        ...
"""

import time
import uuid

import structlog
from fastapi import HTTPException, Request
from twilio.request_validator import RequestValidator  # type: ignore[import-untyped]

from whatsapp_langchain.shared.config import settings
from whatsapp_langchain.shared.redis_client import get_redis

logger = structlog.get_logger()


def build_validation_url(request: Request) -> str:
    """Reconstrói a URL pública que o Twilio usou para chamar o webhook.

    Atrás de proxy/túnel (cloudflared), request.url mostra localhost.
    TWILIO_WEBHOOK_URL resolve isso definindo a URL pública base.
    Se não configurada, usa a URL do request diretamente.

    Args:
        request: Request HTTP do FastAPI.

    Returns:
        URL completa para validação de assinatura.
    """
    if settings.twilio_webhook_url:
        base = settings.twilio_webhook_url.rstrip("/")
        url = f"{base}{request.url.path}"
        if request.url.query:
            url = f"{url}?{request.url.query}"
        return url
    return str(request.url)


async def validate_twilio_signature(request: Request) -> None:
    """Valida a assinatura X-Twilio-Signature com HMAC-SHA1 (SDK oficial).

    Usa o RequestValidator do SDK do Twilio para validação criptográfica.
    Quando habilitada (VALIDATE_TWILIO_SIGNATURE=true), rejeita com 403
    qualquer request sem assinatura válida.

    A URL usada na validação é reconstruída via TWILIO_WEBHOOK_URL
    (necessário atrás de proxy/túnel como cloudflared) ou do request.

    Raises:
        HTTPException 403: Se a assinatura é inválida ou ausente.
        HTTPException 500: Se TWILIO_AUTH_TOKEN não está configurado.
    """
    if not settings.validate_twilio_signature:
        return

    signature = request.headers.get("X-Twilio-Signature")
    if not signature:
        logger.warning("twilio_signature_missing")
        raise HTTPException(status_code=403, detail="Missing Twilio signature")

    if not settings.twilio_auth_token:
        logger.error("twilio_auth_token_not_configured")
        raise HTTPException(
            status_code=500,
            detail="Twilio auth token not configured",
        )

    url = build_validation_url(request)

    # Parâmetros POST para validação (Twilio assina URL + params ordenados)
    form_data = await request.form()
    params = {key: str(value) for key, value in form_data.items()}

    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(url, params, signature):
        logger.warning(
            "twilio_signature_invalid",
            url=url,
            params_keys=sorted(params.keys()),
        )
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    logger.debug("twilio_signature_valid")


async def check_rate_limit(phone_number: str) -> None:
    """Verifica rate limit por número de telefone.

    Usa sliding window de 1 hora em Redis (sorted set), compartilhado entre
    todas as réplicas da API. Remove entradas antigas e compara a
    quantidade de requisições com o limite configurado.

    Args:
        phone_number: Número de telefone do remetente.

    Raises:
        HTTPException 429: Se o limite foi atingido.
    """
    redis = await get_redis()
    key = f"ratelimit:{phone_number}"
    now = time.time()
    one_hour_ago = now - 3600

    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, one_hour_ago)
        pipe.zcard(key)
        results = await pipe.execute()
    count = results[1]

    if count >= settings.rate_limit_per_hour:
        logger.warning(
            "rate_limit_exceeded",
            phone=phone_number,
            count=count,
            limit=settings.rate_limit_per_hour,
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
        )

    async with redis.pipeline(transaction=True) as pipe:
        pipe.zadd(key, {str(uuid.uuid4()): now})
        pipe.expire(key, 3600)
        await pipe.execute()


async def require_admin_session(request: Request) -> str:
    """Exige sessão de admin autenticada via cookie assinado.

    Usado como dependency das rotas administrativas (`/api/*`).

    Args:
        request: Request HTTP do FastAPI.

    Returns:
        Username do admin autenticado.

    Raises:
        HTTPException 401: Se não há sessão válida.
    """
    admin_username = request.session.get("admin_username")
    if not admin_username:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return admin_username
