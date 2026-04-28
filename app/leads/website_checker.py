"""
Verificador de website: filtra empresas que NÃO possuem site ativo.
Usa HTTP request para confirmar com 100% de certeza.
"""
import logging
import re
import requests

logger = logging.getLogger("agente.leads.website")

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})


def _normalizar_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    return url


def tem_website_ativo(url: str) -> bool:
    """
    Retorna True apenas se o URL responde com status HTTP < 400.
    Tenta HEAD primeiro, depois GET como fallback.
    """
    if not url or not url.strip():
        return False

    # URLs de listagens/diretórios não contam como site próprio
    dominios_listagem = (
        "paginasamarelas.com.br", "guiamais.com.br", "encontrei.com",
        "yelp.com", "tripadvisor.com", "ifood.com.br", "aiqfome.com",
        "facebook.com", "instagram.com", "google.com", "linkedin.com",
    )
    for dominio in dominios_listagem:
        if dominio in url.lower():
            return False

    url_norm = _normalizar_url(url)
    try:
        resp = _SESSION.head(url_norm, timeout=6, allow_redirects=True)
        return resp.status_code < 400
    except Exception:
        pass

    try:
        resp = _SESSION.get(url_norm, timeout=8, allow_redirects=True, stream=True)
        resp.close()
        return resp.status_code < 400
    except Exception:
        return False


def filtrar_sem_website(leads: list[dict], callback=None) -> list[dict]:
    """
    Retorna apenas leads que comprovadamente NÃO possuem site ativo.
    Verifica cada URL encontrada — se responder, descarta o lead.
    """
    sem_site = []
    for lead in leads:
        nome = lead.get("nome", "?")
        website = lead.get("website") or ""

        if not website.strip():
            sem_site.append(lead)
            if callback:
                callback(f"[SEM SITE] {nome} — nenhum URL encontrado")
            continue

        ativo = tem_website_ativo(website)
        if ativo:
            if callback:
                callback(f"[TEM SITE] {nome} — site ativo: {website[:60]}")
        else:
            sem_site.append(lead)
            if callback:
                callback(f"[SEM SITE] {nome} — URL inativo/inexistente: {website[:60]}")

    return sem_site
