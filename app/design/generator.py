"""
Gerador de mensagens personalizadas via Claude AI.
Cria textos persuasivos e únicos para cada prospect.
"""
import logging
import anthropic
from app.config.settings import ANTHROPIC_API_KEY

logger = logging.getLogger("agente.design")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


PROMPT_SISTEMA = """Você é um especialista em copywriting e vendas consultivas para pequenas e médias empresas brasileiras.
Sua tarefa é criar mensagens de prospecção via WhatsApp que:
- Sejam curtas (máximo 3 parágrafos)
- Comecem com o nome do negócio para personalização
- Apresentem um problema real do nicho e ofereçam solução
- Tenham um CTA claro e natural
- Soem humanizadas, nunca robóticas
- Usem linguagem informal mas profissional
- Nunca mencionem que é uma IA gerando o texto
"""


def gerar_mensagem_whatsapp(nome: str, nicho: str, cidade: str, servico_ofertado: str = None) -> str:
    """Gera mensagem personalizada para WhatsApp via Claude."""
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "sua_chave_aqui":
        return _mensagem_template(nome, nicho, cidade, servico_ofertado)

    servico = servico_ofertado or "presença digital e captação de clientes online"

    prompt = f"""
Crie uma mensagem de prospecção para WhatsApp para o seguinte negócio:
- Nome do negócio: {nome}
- Nicho/Segmento: {nicho}
- Cidade: {cidade}
- Serviço que vou oferecer: {servico}

A mensagem deve ser natural, como se eu tivesse digitando no WhatsApp agora.
Retorne APENAS o texto da mensagem, sem explicações adicionais.
"""

    try:
        client = _get_client()
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=PROMPT_SISTEMA,
            messages=[{"role": "user", "content": prompt}],
        )
        mensagem = resp.content[0].text.strip()
        logger.info(f"Mensagem gerada via Claude para: {nome}")
        return mensagem
    except Exception as e:
        logger.warning(f"Claude indisponível ({e}), usando template padrão")
        return _mensagem_template(nome, nicho, cidade, servico_ofertado)


def gerar_mensagem_oferta_site(nome: str, nicho: str, cidade: str) -> str:
    """Gera mensagem de oferta de criação de site para empresa sem website."""
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "sua_chave_aqui":
        return _mensagem_template_site(nome, nicho, cidade)

    prompt = f"""
Crie uma mensagem de prospecção para WhatsApp. A empresa NÃO POSSUI SITE e você está
oferecendo criar um site profissional para eles. Você está enviando junto uma imagem de
pré-visualização de como o site deles ficaria.

- Nome do negócio: {nome}
- Nicho/Segmento: {nicho}
- Cidade: {cidade}

A mensagem deve:
- Mencionar que você notou que eles ainda não têm um site
- Dizer que criou uma pré-visualização exclusiva de como o site deles ficaria (a imagem em anexo)
- Destacar os benefícios: mais clientes, aparecer no Google, credibilidade
- Ter um CTA natural (responder para saber mais, sem pressão)
- Ser curta (máximo 4 linhas), informal mas profissional
- Soar humana, nunca robótica

Retorne APENAS o texto da mensagem, sem explicações.
"""

    try:
        client = _get_client()
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=350,
            system=PROMPT_SISTEMA,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning(f"Claude indisponível ({e}), usando template de site")
        return _mensagem_template_site(nome, nicho, cidade)


def _mensagem_template_site(nome: str, nicho: str, cidade: str) -> str:
    templates = [
        f"Olá, *{nome}*! Vi que vocês ainda não têm um site próprio. "
        f"Criei uma pré-visualização de como ficaria o site de vocês — dá uma olhada na imagem! "
        f"Ajudo negócios de {nicho} em {cidade} a atrair mais clientes pelo Google. Posso te contar mais? 😊",

        f"Oi! Pesquisei as melhores empresas de {nicho} em {cidade} e vi que o *{nome}* ainda não tem site. "
        f"Preparei uma pré-visualização exclusiva para vocês (imagem em anexo). "
        f"Site profissional aumenta muito a credibilidade e atrai clientes novos — quer saber como funciona?",

        f"Olá, *{nome}*! Sei que um site pode parecer complicado, mas preparei uma pré-visualização "
        f"personalizada de como ficaria o site de vocês. Empresas de {nicho} que têm site próprio "
        f"ganham muito mais visibilidade. Posso mandar mais detalhes sem compromisso? 🚀",
    ]
    import hashlib
    idx = int(hashlib.md5(nome.encode()).hexdigest(), 16) % len(templates)
    return templates[idx]


def _mensagem_template(nome: str, nicho: str, cidade: str, servico: str = None) -> str:
    """Fallback com templates rotativos quando Claude não está disponível."""
    servico = servico or "sua presença digital"
    templates = [
        f"Olá! Vi que vocês do *{nome}* são referência em {nicho} aqui em {cidade}. "
        f"Trabalho ajudando negócios como o de vocês a atrair mais clientes pelo digital. "
        f"Posso mostrar como em 10 minutos? 🙂",

        f"Boa tarde! Sou especialista em marketing para {nicho} e encontrei o *{nome}* enquanto pesquisava "
        f"as melhores opções de {cidade}. Tenho uma estratégia que pode aumentar o movimento de vocês — "
        f"posso apresentar rapidinho?",

        f"Oi! Tudo bem? Vi o trabalho do *{nome}* e fiquei impressionado. "
        f"Ajudo negócios de {nicho} em {cidade} a crescerem online. "
        f"Tem interesse em saber como? Posso mandar mais detalhes sem compromisso 😊",
    ]
    import hashlib
    idx = int(hashlib.md5(nome.encode()).hexdigest(), 16) % len(templates)
    return templates[idx]
