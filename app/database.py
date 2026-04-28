import sqlite3
import os
from datetime import datetime
from app.config.settings import DB_PATH


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


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
        """)


def lead_ja_contatado(email: str = None, telefone: str = None) -> bool:
    with get_conn() as conn:
        if email:
            r = conn.execute(
                "SELECT id FROM campanhas c JOIN prospects p ON c.prospect_id=p.id WHERE p.email=? AND c.status='enviado'",
                (email,)
            ).fetchone()
            if r:
                return True
        if telefone:
            r = conn.execute(
                "SELECT id FROM campanhas c JOIN prospects p ON c.prospect_id=p.id WHERE p.telefone=? AND c.status='enviado'",
                (telefone,)
            ).fetchone()
            if r:
                return True
    return False


def salvar_prospect(nome, email=None, telefone=None, nicho=None, cidade=None, website=None, fonte=None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO prospects (nome,email,telefone,nicho,cidade,website,fonte) VALUES (?,?,?,?,?,?,?)",
            (nome, email, telefone, nicho, cidade, website, fonte)
        )
        return cur.lastrowid


def registrar_campanha(prospect_id, canal, status, mensagem=None, erro=None):
    enviado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "enviado" else None
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO campanhas (prospect_id,canal,status,mensagem,enviado_em,erro) VALUES (?,?,?,?,?,?)",
            (prospect_id, canal, status, mensagem, enviado_em, erro)
        )


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


def get_stats():
    with get_conn() as conn:
        total_prospects = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
        total_enviados = conn.execute("SELECT COUNT(*) FROM campanhas WHERE status='enviado'").fetchone()[0]
        total_erros = conn.execute("SELECT COUNT(*) FROM campanhas WHERE status='erro'").fetchone()[0]
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
        "total_enviados": total_enviados,
        "total_erros": total_erros,
        "execucoes": execucoes,
        "prospects": prospects,
    }
