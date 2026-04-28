"""
Motor de busca de leads — Brasil inteiro, sem filtro de cidade.
Fontes: Páginas Amarelas, DuckDuckGo, Google Maps.
"""
import re
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger("agente.leads")
ua = UserAgent()

HEADERS = lambda: {"User-Agent": ua.random, "Accept-Language": "pt-BR,pt;q=0.9"}

# Principais cidades brasileiras para varredura rotativa
NICHOS_GERAIS = [
    "restaurante", "pizzaria", "lanchonete", "padaria", "mercado",
    "academia", "fisioterapia", "nutricionista",
    "salao de beleza", "barbearia", "estetica",
    "clinica medica", "dentista", "psicólogo", "veterinario",
    "advogado", "contabilidade", "imobiliaria",
    "pet shop", "escola", "curso", "oficina mecanica",
    "farmácia", "loja de roupas", "moveis", "eletrodomesticos",
    "construcao civil", "encanador", "eletricista", "jardinagem",
]

CIDADES_BR = [
    "São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador", "Fortaleza",
    "Curitiba", "Manaus", "Recife", "Porto Alegre", "Belém", "Goiânia",
    "Guarulhos", "Campinas", "São Luís", "Maceió", "Natal", "Teresina",
    "Campo Grande", "João Pessoa", "Aracaju", "Cuiabá", "Macapá", "Porto Velho",
    "Rio Branco", "Boa Vista", "Palmas", "Florianópolis", "Vitória", "Brasília",
]


def _limpar_telefone(texto: str) -> str:
    return re.sub(r"[^\d+]", "", texto)


def _cidades_amostra(n: int = 6) -> list[str]:
    """Retorna amostra aleatória de cidades para diversificar a busca."""
    return random.sample(CIDADES_BR, min(n, len(CIDADES_BR)))


def buscar_paginas_amarelas(nicho: str, cidade: str, max_results: int = 15) -> list[dict]:
    """Scraping das Páginas Amarelas Brasil."""
    leads = []
    slug_nicho = nicho.lower().replace(" ", "-")
    slug_cidade = (cidade.lower()
                   .replace(" ", "-")
                   .replace("ã", "a").replace("ç", "c")
                   .replace("é", "e").replace("ê", "e")
                   .replace("ó", "o").replace("ô", "o")
                   .replace("á", "a").replace("â", "a"))
    url = f"https://www.paginasamarelas.com.br/busca/{slug_nicho}/{slug_cidade}"

    try:
        resp = requests.get(url, headers=HEADERS(), timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(".company-info, .listing-item, [class*='company']")
        for card in cards[:max_results]:
            nome_tag = card.select_one("h2, h3, .company-name, [class*='name']")
            tel_tag = card.select_one("[class*='phone'], [class*='tel']")
            site_tag = card.select_one("a[href*='http']:not([href*='paginasamarelas'])")
            nome = nome_tag.get_text(strip=True) if nome_tag else ""
            telefone = tel_tag.get_text(strip=True) if tel_tag else ""
            website = site_tag["href"] if site_tag and site_tag.get("href") else None
            if nome:
                leads.append({
                    "nome": nome[:80],
                    "telefone": _limpar_telefone(telefone) if telefone else None,
                    "email": None,
                    "website": website,
                    "cidade": cidade,
                    "fonte": "paginas_amarelas",
                })
    except Exception as e:
        logger.warning(f"Páginas Amarelas ({cidade}): {e}")

    return leads


def buscar_duckduckgo(nicho: str, cidade: str, max_results: int = 15) -> list[dict]:
    """Busca via DuckDuckGo HTML."""
    leads = []
    query = f"{nicho} {cidade} Brasil telefone whatsapp"
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"

    try:
        resp = requests.get(url, headers=HEADERS(), timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = soup.select(".result__body")
        for result in results[:max_results]:
            title_tag = result.select_one(".result__title a")
            snippet = result.select_one(".result__snippet")
            url_tag = result.select_one(".result__url")
            nome = title_tag.get_text(strip=True) if title_tag else ""
            website = url_tag.get_text(strip=True) if url_tag else ""
            texto = snippet.get_text(" ") if snippet else ""
            telefones = re.findall(r"(?:\+55\s?)?(?:\(?\d{2}\)?\s?)(?:9\s?)?\d{4}[-\s]?\d{4}", texto)
            emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", texto)
            if nome:
                leads.append({
                    "nome": nome[:80],
                    "telefone": _limpar_telefone(telefones[0]) if telefones else None,
                    "email": emails[0] if emails else None,
                    "website": website[:200] if website else None,
                    "cidade": cidade,
                    "fonte": "duckduckgo",
                })
        time.sleep(1)
    except Exception as e:
        logger.warning(f"DuckDuckGo ({cidade}): {e}")

    return leads


def buscar_leads(nicho: str = None, cidade: str = None, max_results: int = 50) -> list[dict]:
    """
    Busca leads no Brasil inteiro rotacionando cidades automaticamente.
    Se nicho for None ou 'geral', rotaciona por vários nichos automaticamente.
    Se cidade for informada, foca nela; caso contrário varre várias cidades.
    """
    todos = []

    # Modo geral: rotaciona por nichos variados
    if not nicho or nicho.strip().lower() == "geral":
        nichos_amostra = random.sample(NICHOS_GERAIS, min(6, len(NICHOS_GERAIS)))
        cidades = [cidade] if cidade else _cidades_amostra(3)
        por_nicho = max(max_results // len(nichos_amostra), 5)
        for nic in nichos_amostra:
            for cid in cidades:
                logger.info(f"[Geral] Buscando '{nic}' em {cid}...")
                todos += buscar_paginas_amarelas(nic, cid, por_nicho)
                todos += buscar_duckduckgo(nic, cid, por_nicho)
                time.sleep(random.uniform(1.0, 2.5))
        # Garante o campo nicho em cada lead
        for lead in todos:
            if not lead.get("nicho"):
                lead["nicho"] = lead.get("_nicho_temp", nicho or "geral")
        vistos = set()
        unicos = []
        for lead in todos:
            chave = lead.get("telefone") or lead.get("email") or lead.get("nome", "")
            if chave and chave not in vistos:
                vistos.add(chave)
                unicos.append(lead)
        random.shuffle(unicos)
        logger.info(f"[Geral] Total único: {len(unicos)}")
        return unicos[:max_results]

    cidades = [cidade] if cidade else _cidades_amostra(6)
    por_cidade = max(max_results // len(cidades), 10)

    for cid in cidades:
        logger.info(f"Buscando '{nicho}' em {cid}...")
        todos += buscar_paginas_amarelas(nicho, cid, por_cidade)
        todos += buscar_duckduckgo(nicho, cid, por_cidade)
        time.sleep(random.uniform(1.5, 3.0))  # delay anti-bloqueio

    # Deduplicar por telefone/email/nome
    vistos = set()
    unicos = []
    for lead in todos:
        chave = lead.get("telefone") or lead.get("email") or lead.get("nome", "")
        if chave and chave not in vistos:
            vistos.add(chave)
            lead["nicho"] = nicho
            unicos.append(lead)

    random.shuffle(unicos)
    logger.info(f"Total de leads únicos encontrados: {len(unicos)}")
    return unicos[:max_results]
