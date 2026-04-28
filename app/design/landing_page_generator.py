"""
Gerador de mockup visual de landing page usando Pillow.
Cria uma imagem PNG profissional para pitching de criação de site.
"""
import io
import os
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("agente.design.landing")

# ── Paletas por nicho ──────────────────────────────────────────────────────────
_PALETAS = {
    "restaurante": {"pri": (210, 65, 45),  "sec": (245, 155, 45), "dark": (28, 12,  8)},
    "pizzaria":    {"pri": (210, 65, 45),  "sec": (245, 155, 45), "dark": (28, 12,  8)},
    "lanchonete":  {"pri": (210, 65, 45),  "sec": (245, 155, 45), "dark": (28, 12,  8)},
    "academia":    {"pri": (25,  25, 25),  "sec": (240, 190,  0), "dark": ( 8,  8,  8)},
    "fitness":     {"pri": (25,  25, 25),  "sec": (240, 190,  0), "dark": ( 8,  8,  8)},
    "salao":       {"pri": (175, 75, 115), "sec": (240, 155, 185),"dark": (28, 12, 22)},
    "estetica":    {"pri": (175, 75, 115), "sec": (240, 155, 185),"dark": (28, 12, 22)},
    "clinica":     {"pri": ( 0, 115, 195), "sec": ( 0, 175, 215), "dark": ( 5, 18, 38)},
    "dentista":    {"pri": ( 0, 115, 195), "sec": ( 0, 175, 215), "dark": ( 5, 18, 38)},
    "advogado":    {"pri": (40,  50, 80),  "sec": (180, 155, 100),"dark": (12, 15, 25)},
    "contabil":    {"pri": (40,  50, 80),  "sec": (180, 155, 100),"dark": (12, 15, 25)},
    "pet":         {"pri": (60, 150,  90), "sec": (120, 220, 140),"dark": (10, 22, 15)},
    "escola":      {"pri": (90,  60, 190), "sec": (150, 120, 240),"dark": (15, 10, 35)},
    "default":     {"pri": (55,  95, 215), "sec": ( 0, 200, 170), "dark": (10, 14, 30)},
}

_HEADLINES = {
    "restaurante": ("Gastronomia que conquista",    "Reserve sua mesa e viva uma experiência única"),
    "pizzaria":    ("A melhor pizza da cidade",      "Massa artesanal, ingredientes frescos todo dia"),
    "lanchonete":  ("Sabor e rapidez em cada bite", "Atendimento ágil, comida de verdade"),
    "academia":    ("Transforme seu corpo",          "Resultados reais com acompanhamento profissional"),
    "fitness":     ("Seu melhor desempenho",         "Treinos personalizados para todos os objetivos"),
    "salao":       ("Realce sua beleza",             "Atendimento premium para você brilhar"),
    "estetica":    ("Beleza e bem-estar",            "Tratamentos exclusivos para sua autoestima"),
    "clinica":     ("Saude em primeiro lugar",       "Cuidado especializado e atendimento humanizado"),
    "dentista":    ("Sorria com confianca",          "Tratamentos modernos para seu sorriso perfeito"),
    "advogado":    ("Defesa que voce pode confiar",  "Experiencia e dedicacao em cada caso"),
    "contabil":    ("Sua empresa em ordem",          "Contabilidade especializada para seu negocio"),
    "pet":         ("Amor e cuidado para seu pet",   "Servicos completos de saude e bem-estar animal"),
    "escola":      ("Educacao que transforma",       "Metodologia moderna para o futuro dos seus filhos"),
    "default":     ("Bem-vindo ao nosso espaco",     "Qualidade e excelencia em cada detalhe"),
}

_FEATURES = {
    "restaurante": [("Cardapio Digital",  "Acesse o menu completo"), ("Reservas Online", "Reserve sua mesa"), ("Delivery",        "Pedidos pelo site")],
    "academia":    [("Planos Exclusivos", "Para todos objetivos"),   ("Instrutores",     "Equipe qualificada"),("Horarios",        "Flexiveis para voce")],
    "salao":       [("Cortes & Color.",   "Ultimas tendencias"),     ("Tratamentos",     "Realce sua beleza"), ("Agendamento",     "Rapido e facil")],
    "clinica":     [("Consultas",         "Profissionais expert."), ("Exames",          "Tecnologia atual"),  ("Agendamento",     "Online e rapido")],
    "dentista":    [("Limpeza",           "Profilaxia completa"),    ("Ortodontia",      "Alinhamento dental"),("Clareamento",     "Sorriso perfeito")],
    "advogado":    [("Consultoria",       "Analise do seu caso"),    ("Defesa Civel",    "Seus direitos"),     ("Trabalhista",     "Protecao total")],
    "pet":         [("Veterinario",       "Saude do seu pet"),       ("Banho & Tosa",    "Bem-estar animal"),  ("Hotel Pet",       "Cuidado 24h")],
    "default":     [("Qualidade",         "Servicos premium"),       ("Atendimento",     "Equipe dedicada"),   ("Contato",         "Sempre disponivel")],
}


def _paleta(nicho: str) -> dict:
    n = nicho.lower()
    for key, val in _PALETAS.items():
        if key in n:
            return val
    return _PALETAS["default"]


def _headline(nicho: str) -> tuple:
    n = nicho.lower()
    for key, val in _HEADLINES.items():
        if key in n:
            return val
    return _HEADLINES["default"]


def _features(nicho: str) -> list:
    n = nicho.lower()
    for key, val in _FEATURES.items():
        if key in n:
            return val
    return _FEATURES["default"]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates = [
            "C:/Windows/Fonts/calibrib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/trebucbd.ttf",
            "C:/Windows/Fonts/verdanab.ttf",
        ]
    else:
        candidates = [
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/trebuc.ttf",
            "C:/Windows/Fonts/verdana.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


def gerar_mockup_landing_page(nome: str, nicho: str, cidade: str = "") -> bytes:
    """
    Gera PNG de mockup de landing page profissional.
    Retorna bytes da imagem PNG.
    """
    W, H = 1280, 780
    pri   = _paleta(nicho)["pri"]
    sec   = _paleta(nicho)["sec"]
    dark  = _paleta(nicho)["dark"]
    h1, h2 = _headline(nicho)
    feats   = _features(nicho)
    nome_s  = nome[:28]

    img  = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # ── Browser chrome ──────────────────────────────────────────
    draw.rectangle([(0, 0), (W, 44)], fill=(238, 238, 238))
    draw.rectangle([(0, 44), (W, 45)], fill=(200, 200, 200))
    # Tabs
    _draw_rounded_rect(draw, [10, 7, 14, 38], 3, (220, 220, 220))   # tab left strip
    _draw_rounded_rect(draw, [16, 7, 220, 38], 6, (255, 255, 255))
    draw.text((32, 17), nome_s[:18], fill=(70, 70, 70), font=_font(13))
    draw.text((190, 17), "x", fill=(160, 160, 160), font=_font(13))
    _draw_rounded_rect(draw, [224, 7, 244, 38], 6, (238, 238, 238))
    draw.text((230, 16), "+", fill=(120, 120, 120), font=_font(16))
    # URL bar
    _draw_rounded_rect(draw, [360, 10, 880, 34], 12, (225, 225, 225))
    url_text = f"www.{nome.lower().replace(' ', '').replace('.', '')[:18]}.com.br"
    draw.text((378, 17), url_text, fill=(90, 90, 90), font=_font(12))
    # Nav icons (back/fwd)
    draw.text((255, 16), "<  >", fill=(140, 140, 140), font=_font(13))

    # ── Navbar ─────────────────────────────────────────────────
    NAV_Y0, NAV_Y1 = 45, 100
    draw.rectangle([(0, NAV_Y0), (W, NAV_Y1)], fill=dark)
    # Logo text
    draw.text((40, 62), nome_s.upper(), fill=sec, font=_font(24, bold=True))
    # Nav links
    for i, item in enumerate(["Inicio", "Servicos", "Sobre nos", "Contato"]):
        draw.text((680 + i * 140, 68), item, fill=(210, 215, 225), font=_font(14))

    # ── Hero gradient ───────────────────────────────────────────
    HERO_Y0, HERO_Y1 = NAV_Y1, NAV_Y1 + 360
    for y in range(HERO_Y0, HERO_Y1):
        t = (y - HERO_Y0) / (HERO_Y1 - HERO_Y0)
        r = int(dark[0] * (1 - t * 0.5) + pri[0] * t * 0.5)
        g = int(dark[1] * (1 - t * 0.5) + pri[1] * t * 0.5)
        b = int(dark[2] * (1 - t * 0.5) + pri[2] * t * 0.5)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Hero image placeholder (right)
    IMG_X0, IMG_Y0, IMG_X1, IMG_Y1 = 700, HERO_Y0 + 30, 1200, HERO_Y1 - 30
    ph_r = max(0, min(255, pri[0] + 40))
    ph_g = max(0, min(255, pri[1] + 40))
    ph_b = max(0, min(255, pri[2] + 40))
    _draw_rounded_rect(draw, [IMG_X0, IMG_Y0, IMG_X1, IMG_Y1], 16, (ph_r, ph_g, ph_b))
    # Decorative grid lines on placeholder
    for xi in range(0, 500, 35):
        x = IMG_X0 + xi
        if x < IMG_X1:
            draw.line([(x, IMG_Y0), (x, IMG_Y1)], fill=(max(0, ph_r-20), max(0, ph_g-20), max(0, ph_b-20)), width=1)
    for yi in range(0, 300, 35):
        y = IMG_Y0 + yi
        if y < IMG_Y1:
            draw.line([(IMG_X0, y), (IMG_X1, y)], fill=(max(0, ph_r-20), max(0, ph_g-20), max(0, ph_b-20)), width=1)
    # Camera icon placeholder text
    ph_cx = (IMG_X0 + IMG_X1) // 2
    ph_cy = (IMG_Y0 + IMG_Y1) // 2
    draw.text((ph_cx - 60, ph_cy - 20), "[ FOTO DA EMPRESA ]", fill=(255, 255, 255), font=_font(16))

    # Headline texts
    draw.text((55, HERO_Y0 + 30), nome_s, fill=(255, 255, 255), font=_font(44, bold=True))
    draw.text((55, HERO_Y0 + 90), h1, fill=sec, font=_font(26, bold=True))
    draw.text((55, HERO_Y0 + 135), h2, fill=(200, 210, 225), font=_font(17))
    if cidade:
        draw.text((55, HERO_Y0 + 170), f"Localizado em {cidade}", fill=(170, 185, 210), font=_font(14))

    # CTA Button
    BTN_X0, BTN_Y0, BTN_X1, BTN_Y1 = 55, HERO_Y0 + 210, 270, HERO_Y0 + 258
    _draw_rounded_rect(draw, [BTN_X0, BTN_Y0, BTN_X1, BTN_Y1], 24, sec)
    draw.text((BTN_X0 + 38, BTN_Y0 + 11), "Entre em Contato", fill=dark, font=_font(17, bold=True))

    # Second CTA (outline style)
    BTN2_X0 = 290
    draw.rounded_rectangle([BTN2_X0, BTN_Y0, BTN2_X0 + 190, BTN_Y1], radius=24, outline=(220, 225, 235), width=2)
    draw.text((BTN2_X0 + 30, BTN_Y0 + 11), "Ver Servicos", fill=(220, 225, 235), font=_font(17))

    # ── Features section ───────────────────────────────────────
    FEAT_Y0 = HERO_Y1
    FEAT_Y1 = FEAT_Y0 + 210
    draw.rectangle([(0, FEAT_Y0), (W, FEAT_Y1)], fill=(248, 249, 252))

    # Section title
    draw.text((W // 2 - 100, FEAT_Y0 + 18), "Nossos Diferenciais", fill=(40, 45, 60), font=_font(20, bold=True))
    draw.line([(W // 2 - 60, FEAT_Y0 + 50), (W // 2 + 60, FEAT_Y0 + 50)], fill=pri, width=3)

    for i, (title, desc) in enumerate(feats[:3]):
        fx = 120 + i * 380
        fy = FEAT_Y0 + 70
        # Icon circle
        draw.ellipse([(fx, fy), (fx + 56, fy + 56)], fill=pri)
        draw.text((fx + 16, fy + 14), str(i + 1), fill=(255, 255, 255), font=_font(22, bold=True))
        # Text
        draw.text((fx + 72, fy + 5),  title, fill=(35, 40, 55),  font=_font(17, bold=True))
        draw.text((fx + 72, fy + 32), desc,  fill=(100, 108, 125), font=_font(14))

    # ── Footer ─────────────────────────────────────────────────
    FOOT_Y0 = FEAT_Y1
    draw.rectangle([(0, FOOT_Y0), (W, H)], fill=dark)
    draw.text((55, FOOT_Y0 + 20), nome_s.upper(), fill=sec, font=_font(18, bold=True))
    draw.text((55, FOOT_Y0 + 52), f"{cidade or 'Brasil'}  |  WhatsApp  |  Instagram", fill=(145, 160, 185), font=_font(13))
    draw.text((55, FOOT_Y0 + 75), f"(c) {nome_s}. Todos os direitos reservados.", fill=(90, 100, 120), font=_font(12))

    # Watermark
    draw.text((W - 390, H - 22), "Pre-visualizacao de site — Proposta exclusiva", fill=(75, 82, 98), font=_font(12))

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()
