"""
Servidor webhook para receber eventos da Evolution API.
Quando um lead responde no WhatsApp, move para 'respondeu' no pipeline.
Roda em thread separada na porta 8082.
"""
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from app import database as db

logger = logging.getLogger("agente.webhook")

_servidor: HTTPServer | None = None


class _Handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)
            self._processar(data)
        except Exception as e:
            logger.debug(f"Webhook erro ao processar: {e}")
        finally:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

    def _processar(self, data: dict):
        """
        Trata eventos da Evolution API.
        Detecta mensagens recebidas e atualiza o pipeline.
        """
        evento = data.get("event", "")

        # Evento de mensagem recebida
        if evento in ("messages.upsert", "MESSAGES_UPSERT"):
            msgs = data.get("data", {})
            if isinstance(msgs, list):
                msgs = msgs[0] if msgs else {}

            # Ignora mensagens enviadas por nós
            if msgs.get("key", {}).get("fromMe"):
                return

            # Extrai o número que respondeu
            remote = msgs.get("key", {}).get("remoteJid", "")
            telefone = remote.replace("@s.whatsapp.net", "").replace("@g.us", "")
            if not telefone:
                return

            # Atualiza pipeline para 'respondeu'
            db.marcar_respondeu_por_telefone(telefone)
            logger.info(f"Webhook: resposta recebida de {telefone} — pipeline atualizado")

    def log_message(self, *args):
        pass  # silencia logs HTTP padrão


def iniciar_webhook(porta: int = 8082):
    global _servidor
    if _servidor:
        return

    try:
        _servidor = HTTPServer(("0.0.0.0", porta), _Handler)
        t = threading.Thread(target=_servidor.serve_forever, daemon=True)
        t.start()
        logger.info(f"Webhook rodando em http://localhost:{porta}")
    except Exception as e:
        logger.warning(f"Não foi possível iniciar webhook: {e}")


def parar_webhook():
    global _servidor
    if _servidor:
        _servidor.shutdown()
        _servidor = None
