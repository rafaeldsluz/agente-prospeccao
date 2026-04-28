"""
Busca a logo de uma empresa online.
Estratégias: Bing Images → og:image de redes sociais → favicon Google.
Retorna bytes PNG ou None.
"""
import io
import re
import logging
import requests
from PIL import Image

logger = logging.getLogger("agente.leads.logo")

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "Chrome/124.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
})


# ── Helpers ────────────────────────────────────────────────────────────────────

def _baixar(url: str, timeout: int = 8) -> bytes | None:
    try:
        r = _SESSION.get(url, timeout=timeout, stream=True)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


def _validar_imagem(data: bytes, min_px: int = 50) -> bool:
    try:
        img = Image.open(io.BytesIO(data))
        return img.width >= min_px and img.height >= min_px
    except Exception:
        return False


def _normalizar(data: bytes, tamanho: tuple = (200, 100)) -> bytes:
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    img.thumbnail(tamanho, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ── Estratégia 1: Bing Image Search ───────────────────────────────────────────

def _bing_images(query: str) -> list[str]:
    """Extrai URLs de imagens do Bing Search."""
    try:
        url = f"https://www.bing.com/images/search?q={requests.utils.quote(query)}&form=HDRSC2"
        r = _SESSION.get(url, timeout=10)
        # Bing coloca as URLs das imagens em atributos murl= dentro de elementos <a>
        urls = re.findall(r'murl&quot;:&quot;([^&]+)&quot;', r.text)
        if not urls:
            urls = re.findall(r'"murl":"([^"]+)"', r.text)
        return [u for u in urls if u.startswith("http")][:8]
    except Exception as e:
        logger.debug(f"Bing images erro: {e}")
        return []


# ── Estratégia 2: og:image de página social ───────────────────────────────────

def _og_image_de_url(url: str) -> str | None:
    """Extrai og:image de uma página (Facebook, Instagram, site)."""
    try:
        r = _SESSION.get(url, timeout=8, allow_redirects=True)
        m = re.search(r'<meta[^>]+(?:property="og:image"|name="og:image")[^>]+content="([^"]+)"', r.text)
        if not m:
            m = re.search(r'content="([^"]+)"[^>]+property="og:image"', r.text)
        return m.group(1) if m else None
    except Exception:
        return None


def _buscar_pagina_social(nome: str, cidade: str) -> str | None:
    """Busca página do Facebook ou Instagram da empresa via DuckDuckGo."""
    try:
        query = f"{nome} {cidade} site:facebook.com OR site:instagram.com"
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        r = _SESSION.get(url, timeout=10)
        links = re.findall(r'href="(https?://(?:www\.)?(?:facebook|instagram)\.com/[^"&?]+)"', r.text)
        return links[0] if links else None
    except Exception:
        return None


# ── Estratégia 3: Favicon via Google S2 ───────────────────────────────────────

def _favicon_google(dominio: str) -> bytes | None:
    """Pega favicon de alta resolução via serviço do Google."""
    url = f"https://www.google.com/s2/favicons?domain={dominio}&sz=256"
    data = _baixar(url)
    if data and _validar_imagem(data, min_px=32):
        return data
    return None


def _extrair_dominio(nome: str) -> str:
    """Gera um domínio provável a partir do nome da empresa."""
    slug = re.sub(r"[^a-z0-9]", "", nome.lower().replace(" ", ""))
    return f"{slug}.com.br"


# ── Função principal ───────────────────────────────────────────────────────────

def buscar_logo(nome: str, nicho: str = "", cidade: str = "") -> bytes | None:
    """
    Busca logo da empresa usando 3 estratégias em cascata:
    1. Bing Image Search por "{nome} logo"
    2. og:image da página do Facebook/Instagram da empresa
    3. Favicon via Google S2

    Retorna bytes PNG normalizados ou None.
    """
    # 1. Bing Images
    for query in [f"{nome} logo", f"{nome} {nicho} logo"]:
        logger.info(f"[Logo] Bing: '{query}'")
        for url in _bing_images(query):
            data = _baixar(url)
            if data and _validar_imagem(data):
                try:
                    logo = _normalizar(data)
                    logger.info(f"[Logo] Encontrada via Bing para '{nome}'")
                    return logo
                except Exception:
                    continue

    # 2. og:image de rede social
    logger.info(f"[Logo] Buscando pagina social de '{nome}'")
    pagina = _buscar_pagina_social(nome, cidade)
    if pagina:
        img_url = _og_image_de_url(pagina)
        if img_url:
            data = _baixar(img_url)
            if data and _validar_imagem(data):
                try:
                    logo = _normalizar(data)
                    logger.info(f"[Logo] Encontrada via og:image para '{nome}'")
                    return logo
                except Exception:
                    pass

    # 3. Favicon
    dominio = _extrair_dominio(nome)
    logger.info(f"[Logo] Tentando favicon: {dominio}")
    data = _favicon_google(dominio)
    if data:
        try:
            logo = _normalizar(data, tamanho=(80, 80))
            logger.info(f"[Logo] Favicon encontrado para '{nome}'")
            return logo
        except Exception:
            pass

    logger.info(f"[Logo] Nao encontrada para '{nome}' — mockup usara texto")
    return None
