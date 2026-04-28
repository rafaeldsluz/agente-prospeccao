"""
Disparador em massa com fluxo anti-ban.
Delays humanizados, lotes com pausas, limite diário e variação de mensagem.
"""
import io
import re
import time
import random
import logging
import threading
import pandas as pd

from app.messaging.sender import enviar_whatsapp

logger = logging.getLogger("agente.bulk")

# ── Leitura de Excel / CSV ─────────────────────────────────────────────────────

_ALIAS_TELEFONE = {"telefone", "phone", "celular", "whatsapp", "tel", "numero", "número", "fone"}
_ALIAS_NOME     = {"nome", "name", "empresa", "company", "cliente", "contato", "razao", "razão"}


def ler_planilha(arquivo_bytes: bytes, nome_arquivo: str) -> tuple[list[dict], list[str]]:
    """
    Lê Excel ou CSV e retorna (contatos, colunas).
    Normaliza a coluna de telefone para 'telefone' e de nome para 'nome'.
    """
    try:
        if nome_arquivo.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(arquivo_bytes), dtype=str)
        else:
            df = pd.read_excel(io.BytesIO(arquivo_bytes), dtype=str)
    except Exception as e:
        raise ValueError(f"Erro ao ler planilha: {e}")

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")

    # Normaliza colunas para chaves padrão
    rename_map = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in _ALIAS_TELEFONE and "telefone" not in rename_map.values():
            rename_map[col] = "telefone"
        elif col_lower in _ALIAS_NOME and "nome" not in rename_map.values():
            rename_map[col] = "nome"
    df = df.rename(columns=rename_map)

    contatos = df.to_dict(orient="records")
    return contatos, list(df.columns)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _limpar_telefone(valor: str) -> str:
    return re.sub(r"[^\d+]", "", str(valor or ""))


def _delay_humano(minimo: float, maximo: float) -> float:
    """Delay com leve variação gaussiana para parecer mais humano."""
    base = random.uniform(minimo, maximo)
    jitter = random.gauss(0, base * 0.08)
    return max(minimo * 0.7, base + jitter)


def _variar_mensagem(texto: str, indice: int) -> str:
    """
    Insere caractere invisível único em cada mensagem para evitar detecção
    de mensagem duplicada pelo WhatsApp.
    """
    marcador = "\u200b" * ((indice % 8) + 1)   # zero-width spaces (1 a 8)
    return texto + marcador


def _personalizar(template: str, dados: dict) -> str:
    """Substitui {nome}, {cidade}, etc. pelos valores do contato."""
    variaveis = {k.lower(): (v or "") for k, v in dados.items() if v and str(v).strip()}
    try:
        return template.format_map({**{"nome": "", "cidade": "", "empresa": ""}, **variaveis})
    except Exception:
        return template


# ── Disparador principal ───────────────────────────────────────────────────────

def disparar_em_massa(
    contatos: list[dict],
    mensagem_template: str,
    delay_min: float = 20,
    delay_max: float = 45,
    tamanho_lote: int = 15,
    pausa_lote_min: float = 240,
    pausa_lote_max: float = 540,
    limite_diario: int = 200,
    stop_event: threading.Event | None = None,
    callback=None,
) -> dict:
    """
    Dispara mensagem para lista de contatos com anti-ban.

    Parâmetros de anti-ban:
    - delay_min/max: segundos entre cada mensagem (padrão 20-45s)
    - tamanho_lote: mensagens por lote antes da pausa longa (padrão 15)
    - pausa_lote_min/max: segundos de pausa entre lotes (padrão 4-9 min)
    - limite_diario: máximo de envios nessa execução (padrão 200)
    """
    def log(msg: str):
        logger.info(msg)
        if callback:
            callback(msg)

    if stop_event is None:
        stop_event = threading.Event()

    enviados = erros = pulados = 0
    alvo = min(len(contatos), limite_diario)

    log(f"Iniciando disparo | {alvo} contatos | Lote={tamanho_lote} | Delay={delay_min}-{delay_max}s")

    for i, contato in enumerate(contatos[:limite_diario]):
        if stop_event.is_set():
            log("Disparo interrompido pelo usuario.")
            break

        telefone_raw = (
            contato.get("telefone") or contato.get("Telefone")
            or contato.get("phone")  or contato.get("celular") or ""
        )
        telefone = _limpar_telefone(telefone_raw)
        if len(telefone) < 10:
            nome_fb = contato.get("nome") or contato.get("Nome") or f"linha {i+1}"
            log(f"[{i+1}/{alvo}] Sem telefone valido — pulando {nome_fb}")
            pulados += 1
            continue

        mensagem = _personalizar(mensagem_template, contato)
        mensagem = _variar_mensagem(mensagem, i)

        resultado = enviar_whatsapp(telefone, mensagem)
        nome_exib = contato.get("nome") or contato.get("Nome") or telefone

        if resultado["sucesso"]:
            log(f"[{i+1}/{alvo}] Enviado → {nome_exib} ({telefone})")
            enviados += 1
        else:
            log(f"[{i+1}/{alvo}] Falha → {nome_exib}: {resultado['erro']}")
            erros += 1

        # Verifica parada antes do delay
        if stop_event.is_set():
            break

        is_ultimo = (i + 1) >= alvo
        is_fim_lote = (i + 1) % tamanho_lote == 0

        if not is_ultimo:
            if is_fim_lote:
                pausa = _delay_humano(pausa_lote_min, pausa_lote_max)
                minutos = pausa / 60
                log(f"--- Pausa entre lotes: {minutos:.1f} min (anti-ban) ---")
                # Dorme em pequenos intervalos para responder ao stop_event
                fim = time.time() + pausa
                while time.time() < fim and not stop_event.is_set():
                    time.sleep(1)
            else:
                delay = _delay_humano(delay_min, delay_max)
                log(f"Aguardando {delay:.1f}s...")
                fim = time.time() + delay
                while time.time() < fim and not stop_event.is_set():
                    time.sleep(0.5)

    resumo = {
        "total": alvo,
        "enviados": enviados,
        "erros": erros,
        "pulados": pulados,
    }
    log(f"Disparo concluido: {resumo}")
    return resumo
