"""
Motor de follow-up automático.
D+2: primeiro follow-up (abordagem diferente)
D+5: segundo follow-up (urgência / prova social)
Máximo 2 follow-ups por prospect.
"""
import time
import logging
from app import database as db
from app.messaging.sender import enviar_whatsapp
from app.design.generator import gerar_mensagem_followup

logger = logging.getLogger("agente.followup")

# Dias após o contato inicial para cada follow-up
FOLLOWUP_1_DIAS = 2
FOLLOWUP_2_DIAS = 5


def executar_followups(callback=None) -> dict:
    """
    Verifica e envia follow-ups pendentes.
    Retorna resumo: {enviados, erros, pulados}
    """
    def log(msg):
        logger.info(msg)
        if callback:
            callback(msg)

    enviados = erros = 0

    for numero, dias in [(1, FOLLOWUP_1_DIAS), (2, FOLLOWUP_2_DIAS)]:
        pendentes = db.prospects_para_followup(dias_apos=dias, numero_followup=numero)
        log(f"[Follow-up {numero}] {len(pendentes)} prospects elegíveis (D+{dias})")

        for lead in pendentes:
            nome     = lead["nome"]
            telefone = lead["telefone"]
            nicho    = lead.get("nicho", "")
            cidade   = lead.get("cidade", "")

            mensagem = gerar_mensagem_followup(nome, nicho, cidade, numero)
            resultado = enviar_whatsapp(telefone, mensagem)

            if resultado["sucesso"]:
                db.registrar_campanha(lead["id"], "whatsapp", "enviado", mensagem, tipo=f"followup_{numero}")
                db.registrar_followup(lead["id"], numero, "enviado")
                log(f"[Follow-up {numero}] Enviado → {nome} ({telefone})")
                enviados += 1
            else:
                db.registrar_followup(lead["id"], numero, "erro")
                log(f"[Follow-up {numero}] Falha → {nome}: {resultado['erro']}")
                erros += 1

            time.sleep(15)  # delay entre follow-ups

    resumo = {"enviados": enviados, "erros": erros}
    log(f"Follow-ups concluídos: {resumo}")
    return resumo
