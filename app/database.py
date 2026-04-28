import sqlite3
import os
from datetime import datetime
from app.config.settings import DB_PATH


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS prospects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nome        TEXT NOT NULL,
                email       TEXT,
                telefone    TEXT,
                nicho       TEXT,
                cidade      TEXT,
                website     TEXT,
                fonte       TEXT,
                criado_em   TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS campanhas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_id     INTEGER NOT NULL,
                canal           TEXT NOT NULL,
                status          TEXT DEFAULT 'pendente',
                mensagem        TEXT,
                enviado_em      TEXT,
                erro            TEXT,
                tipo            TEXT DEFAULT 'inicial',
                FOREIGN KEY(prospect_id) REFERENCES prospects(id)
            );

            CREATE TABLE IF NOT EXISTS execucoes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                inicio      TEXT,
                fim         TEXT,
                leads_found INTEGER DEFAULT 0,
                enviados    INTEGER DEFAULT 0,
                erros       INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'em_andamento'
            );

            CREATE TABLE IF NOT EXISTS pipeline (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_id     INTEGER UNIQUE NOT NULL,
                status          TEXT DEFAULT 'contatado',
                observacoes     TEXT,
                valor_estimado  REAL DEFAULT 0,
                criado_em       TEXT DEFAULT (datetime('now','localtime')),
                atualizado_em   TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY(prospect_id) REFERENCES prospects(id)
            );

            CREATE TABLE IF NOT EXISTS followups (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_id     INTEGER NOT NULL,
                numero          INTEGER DEFAULT 1,
                enviado_em      TEXT,
                status          TEXT DEFAULT 'pendente',
                FOREIGN KEY(prospect_id) REFERENCES prospects(id)
            );
        """)
        # Migração: adiciona coluna tipo em campanhas se não existir
        try:
            conn.execute("ALTER TABLE campanhas ADD COLUMN tipo TEXT DEFAULT 'inicial'")
        except Exception:
            pass


# ── Prospects ──────────────────────────────────────────────────────────────────

def _normalizar_tel(telefone: str) -> str:
    import re
    return re.sub(r"\D", "", str(telefone or ""))


def lead_ja_contatado(email: str = None, telefone: str = None) -> bool:
    """Verifica por e-mail ou telefone (normalizado) se o lead já foi contatado."""
    with get_conn() as conn:
        if email and email.strip():
            r = conn.execute(
                "SELECT id FROM campanhas c JOIN prospects p ON c.prospect_id=p.id "
                "WHERE lower(p.email)=lower(?) AND c.status='enviado'", (email.strip(),)
            ).fetchone()
            if r:
                return True
        if telefone:
            tel = _normalizar_tel(telefone)
            if tel:
                # Checa com e sem o prefixo 55 (Brasil)
                variantes = {tel}
                if tel.startswith("55") and len(tel) > 11:
                    variantes.add(tel[2:])
                else:
                    variantes.add("55" + tel)
                for v in variantes:
                    r = conn.execute(
                        "SELECT id FROM campanhas c JOIN prospects p ON c.prospect_id=p.id "
                        "WHERE replace(replace(replace(p.telefone,'+',''),'-',''),' ','')=? "
                        "AND c.status='enviado'", (v,)
                    ).fetchone()
                    if r:
                        return True
    return False


def telefone_ja_na_lista(telefone: str) -> bool:
    """Verifica se o telefone já existe em qualquer prospect (mesmo sem campanha enviada)."""
    tel = _normalizar_tel(telefone)
    if not tel:
        return False
    with get_conn() as conn:
        r = conn.execute(
            "SELECT id FROM prospects WHERE "
            "replace(replace(replace(telefone,'+',''),'-',''),' ','') IN (?,?)",
            (tel, "55" + tel if not tel.startswith("55") else tel[2:])
        ).fetchone()
        return r is not None


def salvar_prospect(nome, email=None, telefone=None, nicho=None, cidade=None, website=None, fonte=None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO prospects (nome,email,telefone,nicho,cidade,website,fonte) VALUES (?,?,?,?,?,?,?)",
            (nome, email, telefone, nicho, cidade, website, fonte)
        )
        pid = cur.lastrowid
        # Cria entrada no pipeline automaticamente
        conn.execute(
            "INSERT OR IGNORE INTO pipeline (prospect_id, status) VALUES (?, 'contatado')",
            (pid,)
        )
        return pid


# ── Campanhas ──────────────────────────────────────────────────────────────────

def registrar_campanha(prospect_id, canal, status, mensagem=None, erro=None, tipo="inicial"):
    enviado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "enviado" else None
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO campanhas (prospect_id,canal,status,mensagem,enviado_em,erro,tipo) "
            "VALUES (?,?,?,?,?,?,?)",
            (prospect_id, canal, status, mensagem, enviado_em, erro, tipo)
        )


# ── Execuções ──────────────────────────────────────────────────────────────────

def iniciar_execucao() -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO execucoes (inicio) VALUES (?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
        )
        return cur.lastrowid


def finalizar_execucao(exec_id, leads_found, enviados, erros, status="concluido"):
    with get_conn() as conn:
        conn.execute(
            "UPDATE execucoes SET fim=?,leads_found=?,enviados=?,erros=?,status=? WHERE id=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), leads_found, enviados, erros, status, exec_id)
        )


# ── Pipeline ───────────────────────────────────────────────────────────────────

PIPELINE_STATUS = ["contatado", "respondeu", "interessado", "negociando", "fechou", "perdeu"]

PIPELINE_CORES = {
    "contatado":  "#4f8ef7",
    "respondeu":  "#a78bfa",
    "interessado":"#fbbf24",
    "negociando": "#f97316",
    "fechou":     "#00d4aa",
    "perdeu":     "#ff4b6e",
}


def atualizar_pipeline(prospect_id: int, status: str, observacoes: str = None, valor: float = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO pipeline (prospect_id, status, observacoes, valor_estimado) VALUES (?,?,?,?) "
            "ON CONFLICT(prospect_id) DO UPDATE SET "
            "status=excluded.status, "
            "observacoes=COALESCE(excluded.observacoes, observacoes), "
            "valor_estimado=COALESCE(excluded.valor_estimado, valor_estimado), "
            "atualizado_em=datetime('now','localtime')",
            (prospect_id, status, observacoes, valor or 0)
        )


def marcar_respondeu_por_telefone(telefone: str):
    """Chamado pelo webhook quando alguém responde no WhatsApp."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM prospects WHERE telefone=?", (telefone,)
        ).fetchone()
        if row:
            pid = row[0]
            conn.execute(
                "UPDATE pipeline SET status='respondeu', atualizado_em=datetime('now','localtime') "
                "WHERE prospect_id=? AND status='contatado'",
                (pid,)
            )


def get_pipeline_completo() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.id, p.nome, p.telefone, p.nicho, p.cidade,
                   pl.status, pl.observacoes, pl.valor_estimado, pl.atualizado_em,
                   c.enviado_em as primeiro_contato,
                   (SELECT COUNT(*) FROM followups f WHERE f.prospect_id=p.id) as followups_enviados
            FROM prospects p
            JOIN pipeline pl ON pl.prospect_id = p.id
            LEFT JOIN campanhas c ON c.prospect_id = p.id AND c.tipo='inicial' AND c.status='enviado'
            ORDER BY pl.atualizado_em DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_pipeline_stats() -> dict:
    with get_conn() as conn:
        contagens = {}
        for s in PIPELINE_STATUS:
            n = conn.execute(
                "SELECT COUNT(*) FROM pipeline WHERE status=?", (s,)
            ).fetchone()[0]
            contagens[s] = n

        receita = conn.execute(
            "SELECT COALESCE(SUM(valor_estimado),0) FROM pipeline WHERE status IN ('negociando','fechou')"
        ).fetchone()[0]

        receita_fechada = conn.execute(
            "SELECT COALESCE(SUM(valor_estimado),0) FROM pipeline WHERE status='fechou'"
        ).fetchone()[0]

    total = contagens.get("contatado", 0) + contagens.get("respondeu", 0)
    taxa_resposta = round(contagens.get("respondeu", 0) / total * 100) if total > 0 else 0

    return {
        "contagens": contagens,
        "receita_pipeline": receita,
        "receita_fechada": receita_fechada,
        "taxa_resposta": taxa_resposta,
    }


# ── Follow-ups ─────────────────────────────────────────────────────────────────

def prospects_para_followup(dias_apos: int, numero_followup: int) -> list[dict]:
    """
    Retorna prospects que foram contatados há X dias,
    ainda estão no status 'contatado' (não responderam)
    e não receberam o follow-up de número N ainda.
    """
    with get_conn() as conn:
        rows = conn.execute(f"""
            SELECT p.id, p.nome, p.telefone, p.nicho, p.cidade
            FROM prospects p
            JOIN pipeline pl ON pl.prospect_id = p.id
            JOIN campanhas c ON c.prospect_id = p.id AND c.tipo='inicial' AND c.status='enviado'
            WHERE pl.status = 'contatado'
              AND datetime(c.enviado_em) <= datetime('now', '-{dias_apos} days', 'localtime')
              AND p.telefone IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM followups f
                  WHERE f.prospect_id = p.id AND f.numero = {numero_followup}
              )
        """).fetchall()
        return [dict(r) for r in rows]


def registrar_followup(prospect_id: int, numero: int, status: str = "enviado"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO followups (prospect_id, numero, enviado_em, status) VALUES (?,?,?,?)",
            (prospect_id, numero, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status)
        )


# ── Stats gerais ───────────────────────────────────────────────────────────────

def get_stats():
    with get_conn() as conn:
        total_prospects = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
        total_enviados  = conn.execute("SELECT COUNT(*) FROM campanhas WHERE status='enviado'").fetchone()[0]
        total_erros     = conn.execute("SELECT COUNT(*) FROM campanhas WHERE status='erro'").fetchone()[0]
        execucoes = conn.execute(
            "SELECT id,inicio,fim,leads_found,enviados,erros,status FROM execucoes ORDER BY id DESC LIMIT 30"
        ).fetchall()
        prospects = conn.execute(
            "SELECT p.nome,p.email,p.telefone,p.nicho,p.cidade,c.status,c.enviado_em "
            "FROM prospects p LEFT JOIN campanhas c ON p.id=c.prospect_id "
            "ORDER BY p.id DESC LIMIT 100"
        ).fetchall()
    return {
        "total_prospects": total_prospects,
        "total_enviados":  total_enviados,
        "total_erros":     total_erros,
        "execucoes":       [tuple(r) for r in execucoes],
        "prospects":       [tuple(r) for r in prospects],
    }
