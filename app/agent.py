"""
Núcleo do agente: orquestra busca → geração de mensagem → envio → persistência.
"""
import logging
import time
from app import database as db
from app.leads.scraper import buscar_leads, empresa_vale_landing_page
from app.leads.website_checker import filtrar_sem_website
from app.leads.logo_finder import buscar_logo
from app.design.generator import gerar_mensagem_whatsapp, gerar_mensagem_oferta_site
from app.design.landing_page_generator import gerar_mockup_landing_page
from app.messaging.sender import enviar_whatsapp, enviar_imagem_whatsapp
from app.config.settings import NICHO_BUSCA, CIDADE_BUSCA, MAX_LEADS_POR_DIA, CANAL_ENVIO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("agente.core")


def executar_ciclo(nicho=None, cidade=None, max_leads=None, canal="whatsapp", callback=None) -> dict:
    """
    Executa um ciclo completo de prospecção.
    callback(msg): função opcional para log em tempo real na UI.
    """
    nicho = nicho or NICHO_BUSCA
    cidade = cidade or CIDADE_BUSCA
    max_leads = max_leads or MAX_LEADS_POR_DIA
    canal = canal or CANAL_ENVIO

    def log(msg):
        logger.info(msg)
        if callback:
            callback(msg)

    db.init_db()
    exec_id = db.iniciar_execucao()
    enviados = erros = 0

    log(f"🚀 Iniciando ciclo | Nicho: {nicho} | Cidade: {cidade} | Max: {max_leads}")

    leads = buscar_leads(nicho, cidade, max_leads)
    log(f"📋 {len(leads)} leads encontrados")

    novos = []
    for lead in leads:
        chave_email = lead.get("email")
        chave_tel = lead.get("telefone")
        if db.lead_ja_contatado(email=chave_email, telefone=chave_tel):
            log(f"⏭️  Pulando (já contatado): {lead['nome']}")
            continue
        novos.append(lead)

    log(f"✅ {len(novos)} leads novos para contatar")

    for lead in novos:
        nome = lead["nome"]
        telefone = lead.get("telefone")

        if not telefone:
            log(f"⚠️  Sem telefone para {nome}, pulando")
            continue

        prospect_id = db.salvar_prospect(
            nome=nome,
            email=lead.get("email"),
            telefone=telefone,
            nicho=lead.get("nicho", nicho),
            cidade=lead.get("cidade", cidade),
            website=lead.get("website"),
            fonte=lead.get("fonte"),
        )

        mensagem = gerar_mensagem_whatsapp(nome, nicho, cidade)
        log(f"✍️  Mensagem gerada para {nome}")

        resultado = enviar_whatsapp(telefone, mensagem)
        if resultado["sucesso"]:
            db.registrar_campanha(prospect_id, "whatsapp", "enviado", mensagem)
            log(f"📤 WhatsApp enviado → {nome} ({telefone})")
            enviados += 1
        else:
            db.registrar_campanha(prospect_id, "whatsapp", "erro", mensagem, resultado["erro"])
            log(f"❌ Falha → {nome}: {resultado['erro']}")
            erros += 1

        time.sleep(3)  # Delay anti-spam entre envios

    db.finalizar_execucao(exec_id, len(leads), enviados, erros)
    resumo = {
        "leads_encontrados": len(leads),
        "novos": len(novos),
        "enviados": enviados,
        "erros": erros,
    }
    log(f"🏁 Ciclo finalizado: {resumo}")
    return resumo


def executar_ciclo_sites(nicho=None, cidade=None, max_leads=None, callback=None, mensagem_custom=None) -> dict:
    """
    Ciclo de prospecção de sites:
    1. Busca leads
    2. Filtra apenas quem NÃO tem site ativo
    3. Gera mockup de landing page personalizado
    4. Envia imagem + mensagem de oferta via WhatsApp
    """
    nicho     = nicho     or NICHO_BUSCA
    cidade    = cidade    or CIDADE_BUSCA
    max_leads = max_leads or MAX_LEADS_POR_DIA

    def log(msg):
        logger.info(msg)
        if callback:
            callback(msg)

    db.init_db()
    exec_id = db.iniciar_execucao()
    enviados = erros = 0

    log(f"🌐 Modo Prospecção de Sites | Nicho: {nicho} | Cidade: {cidade} | Max: {max_leads}")

    leads = buscar_leads(nicho, cidade, max_leads * 3)
    log(f"📋 {len(leads)} leads encontrados — verificando quais não têm site...")

    sem_site = filtrar_sem_website(leads, callback=log)
    log(f"🚫 {len(sem_site)} empresas confirmadas SEM site ativo")

    novos = []
    for lead in sem_site:
        nome_lead  = lead.get("nome", "")
        nicho_lead = lead.get("nicho", nicho)
        if not empresa_vale_landing_page(nome_lead, nicho_lead):
            log(f"⏭️  Pulando (não se beneficia de landing page): {nome_lead}")
            continue
        if not db.lead_ja_contatado(email=lead.get("email"), telefone=lead.get("telefone")):
            novos.append(lead)

    log(f"✅ {len(novos)} leads qualificados para contatar")

    for lead in novos[:max_leads]:
        nome     = lead["nome"]
        telefone = lead.get("telefone")
        cid      = lead.get("cidade", cidade)

        if not telefone:
            log(f"⚠️  Sem telefone para {nome}, pulando")
            continue

        prospect_id = db.salvar_prospect(
            nome=nome,
            email=lead.get("email"),
            telefone=telefone,
            nicho=lead.get("nicho", nicho),
            cidade=cid,
            website=None,
            fonte=lead.get("fonte"),
        )

        log(f"🔍 Buscando logo de {nome}...")
        logo = buscar_logo(nome, nicho, cid)
        if logo:
            log(f"🖼️  Logo encontrada para {nome}")
        else:
            log(f"📝 Logo nao encontrada — usando nome no mockup")

        log(f"🎨 Gerando mockup de landing page para {nome}...")
        try:
            imagem_bytes = gerar_mockup_landing_page(nome, nicho, cid, logo_bytes=logo)
        except Exception as e:
            log(f"❌ Erro ao gerar mockup para {nome}: {e}")
            erros += 1
            db.registrar_campanha(prospect_id, "whatsapp", "erro", "", str(e))
            continue

        if mensagem_custom and mensagem_custom.strip():
            try:
                mensagem = mensagem_custom.format(nome=nome)
            except Exception:
                mensagem = mensagem_custom
        else:
            mensagem = gerar_mensagem_oferta_site(nome, nicho, cid)
        log(f"✍️  Mensagem gerada para {nome}")

        resultado = enviar_imagem_whatsapp(telefone, imagem_bytes, mensagem)
        if resultado["sucesso"]:
            db.registrar_campanha(prospect_id, "whatsapp", "enviado", mensagem)
            log(f"📤 Imagem + oferta enviada → {nome} ({telefone})")
            enviados += 1
        else:
            db.registrar_campanha(prospect_id, "whatsapp", "erro", mensagem, resultado["erro"])
            log(f"❌ Falha ao enviar → {nome}: {resultado['erro']}")
            erros += 1

        time.sleep(4)

    db.finalizar_execucao(exec_id, len(leads), enviados, erros)
    resumo = {
        "leads_encontrados": len(leads),
        "sem_site": len(sem_site),
        "novos": len(novos),
        "enviados": enviados,
        "erros": erros,
    }
    log(f"🏁 Ciclo de sites finalizado: {resumo}")
    return resumo
