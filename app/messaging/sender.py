"""
Módulo de envio de mensagens WhatsApp via Evolution API (self-hosted).
Evolution API: https://doc.evolution-api.com
"""
import logging
import requests
from app.config.settings import (
    EVOLUTION_API_URL,
    EVOLUTION_API_KEY,
    EVOLUTION_INSTANCE,
)

logger = logging.getLogger("agente.messaging")


def _headers():
    return {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }


def _formatar_numero(telefone: str) -> str:
    """Garante formato: 5511999999999 (DDI + DDD + número, sem símbolos)."""
    import re
    digits = re.sub(r"\D", "", telefone)
    if not digits.startswith("55"):
        digits = "55" + digits
    return digits


def enviar_whatsapp(telefone: str, mensagem: str) -> dict:
    """
    Envia mensagem de texto via Evolution API.
    Retorna: {"sucesso": bool, "erro": str|None, "response": dict}
    """
    if not EVOLUTION_API_URL or not EVOLUTION_API_KEY or not EVOLUTION_INSTANCE:
        logger.error("Evolution API não configurada no .env")
        return {"sucesso": False, "erro": "Evolution API não configurada", "response": {}}

    numero = _formatar_numero(telefone)
    url = f"{EVOLUTION_API_URL.rstrip('/')}/message/sendText/{EVOLUTION_INSTANCE}"
    payload = {
        "number": numero,
        "text": mensagem,
        "delay": 1200,  # delay humanizado em ms
    }

    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=20)
        data = resp.json() if resp.content else {}

        if resp.status_code in (200, 201):
            logger.info(f"WhatsApp enviado para {numero}")
            return {"sucesso": True, "erro": None, "response": data}
        else:
            erro = data.get("message", resp.text[:200])
            logger.warning(f"Falha ao enviar para {numero}: {erro}")
            return {"sucesso": False, "erro": erro, "response": data}

    except requests.exceptions.Timeout:
        logger.error(f"Timeout ao enviar para {numero}")
        return {"sucesso": False, "erro": "Timeout na requisição", "response": {}}
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar para {numero}: {e}")
        return {"sucesso": False, "erro": str(e), "response": {}}


def enviar_imagem_whatsapp(telefone: str, imagem_bytes: bytes, legenda: str = "") -> dict:
    """
    Envia imagem via Evolution API (sendMedia).
    imagem_bytes: conteúdo PNG/JPG em bytes.
    Retorna: {"sucesso": bool, "erro": str|None, "response": dict}
    """
    if not EVOLUTION_API_URL or not EVOLUTION_API_KEY or not EVOLUTION_INSTANCE:
        return {"sucesso": False, "erro": "Evolution API não configurada", "response": {}}

    import base64
    numero = _formatar_numero(telefone)
    url = f"{EVOLUTION_API_URL.rstrip('/')}/message/sendMedia/{EVOLUTION_INSTANCE}"
    payload = {
        "number": numero,
        "mediatype": "image",
        "mimetype": "image/png",
        "caption": legenda,
        "media": base64.b64encode(imagem_bytes).decode("utf-8"),
        "fileName": "preview_site.png",
        "delay": 1500,
    }

    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=30)
        data = resp.json() if resp.content else {}
        if resp.status_code in (200, 201):
            logger.info(f"Imagem enviada para {numero}")
            return {"sucesso": True, "erro": None, "response": data}
        else:
            erro = data.get("message", resp.text[:200])
            logger.warning(f"Falha ao enviar imagem para {numero}: {erro}")
            return {"sucesso": False, "erro": erro, "response": data}
    except requests.exceptions.Timeout:
        return {"sucesso": False, "erro": "Timeout ao enviar imagem", "response": {}}
    except Exception as e:
        logger.error(f"Erro ao enviar imagem para {numero}: {e}")
        return {"sucesso": False, "erro": str(e), "response": {}}


def verificar_conexao() -> dict:
    """Verifica se a instância do WhatsApp está conectada."""
    if not EVOLUTION_API_URL or not EVOLUTION_INSTANCE:
        return {"conectado": False, "estado": "não configurado"}
    try:
        url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/connectionState/{EVOLUTION_INSTANCE}"
        resp = requests.get(url, headers=_headers(), timeout=5)
        data = resp.json() if resp.content else {}
        estado = data.get("instance", {}).get("state", "desconhecido")
        return {"conectado": estado == "open", "estado": estado, "data": data}
    except requests.exceptions.ConnectionError:
        return {"conectado": False, "estado": "offline", "detalhe": "Evolution API não está rodando"}
    except requests.exceptions.Timeout:
        return {"conectado": False, "estado": "timeout", "detalhe": "Evolution API sem resposta"}
    except Exception as e:
        logger.debug(f"Erro ao verificar conexão: {e}")
        return {"conectado": False, "estado": "erro", "detalhe": str(e)}


def obter_qrcode() -> str | None:
    """Obtém QR Code para conectar o WhatsApp (base64)."""
    try:
        url = f"{EVOLUTION_API_URL.rstrip('/')}/instance/connect/{EVOLUTION_INSTANCE}"
        resp = requests.get(url, headers=_headers(), timeout=15)
        data = resp.json() if resp.content else {}
        return data.get("base64") or data.get("qrcode", {}).get("base64")
    except Exception as e:
        logger.error(f"Erro ao obter QR Code: {e}")
        return None
