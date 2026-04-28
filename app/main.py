"""
Interface Web — Streamlit
Dashboard de monitoramento e controle do Agente de Prospecção.
"""
import base64
import threading
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

import threading
from app import database as db
from app.agent import executar_ciclo, executar_ciclo_sites
from app.messaging.bulk_sender import disparar_em_massa, ler_planilha
from app.scheduler import (
    iniciar_scheduler,
    parar_scheduler,
    get_proxima_execucao,
)
from app.messaging.sender import verificar_conexao, obter_qrcode
from app.config import settings

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Agente de Prospecção IA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS customizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Base */
    .main { background-color: #0a0c12; }
    section[data-testid="stSidebar"] { background-color: #0f1218; border-right: 1px solid #1e2433; }
    section[data-testid="stSidebar"] .stButton button { width: 100%; }

    /* Typography */
    h1, h2, h3 { font-family: 'Inter', sans-serif; letter-spacing: -0.02em; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #13172a, #1a1f35);
        border: 1px solid #252d45;
        border-radius: 14px;
        padding: 18px 20px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(79,142,247,0.15);
    }
    div[data-testid="metric-container"] label {
        color: #8892a4 !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #e8eaf0 !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }

    /* Status badges */
    .badge {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 5px 12px; border-radius: 20px;
        font-size: 0.82rem; font-weight: 600; letter-spacing: 0.02em;
    }
    .badge-online  { background: rgba(0,212,170,0.12); color: #00d4aa; border: 1px solid rgba(0,212,170,0.3); }
    .badge-offline { background: rgba(255,75,110,0.12); color: #ff4b6e; border: 1px solid rgba(255,75,110,0.3); }
    .badge-active  { background: rgba(79,142,247,0.12); color: #4f8ef7; border: 1px solid rgba(79,142,247,0.3); }
    .badge-idle    { background: rgba(136,146,164,0.12); color: #8892a4; border: 1px solid rgba(136,146,164,0.3); }

    /* Log box */
    .log-box {
        background: #080b10;
        border-radius: 10px;
        padding: 14px 16px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 12.5px;
        line-height: 1.7;
        max-height: 340px;
        overflow-y: auto;
        border: 1px solid #1e2433;
    }
    .log-box::-webkit-scrollbar { width: 5px; }
    .log-box::-webkit-scrollbar-track { background: transparent; }
    .log-box::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 3px; }

    /* Log line colors */
    .log-error { color: #ff6b7a; }
    .log-success { color: #00d4aa; }
    .log-info { color: #7dd3fc; }
    .log-warn { color: #fbbf24; }
    .log-default { color: #94a3b8; }
    .log-ts { color: #4a5568; margin-right: 4px; }

    /* Section divider */
    .section-header {
        display: flex; align-items: center; gap: 10px;
        margin: 24px 0 14px;
    }
    .section-header h3 { margin: 0; color: #c8cfe0; font-size: 1.05rem; font-weight: 600; }
    .section-line { flex: 1; height: 1px; background: linear-gradient(90deg, #1e2433, transparent); }

    /* Info banner */
    .info-banner {
        background: linear-gradient(135deg, #0f1a2e, #131f36);
        border: 1px solid #1e3a5f;
        border-left: 3px solid #4f8ef7;
        border-radius: 8px;
        padding: 12px 16px;
        color: #90b8f8;
        font-size: 0.88rem;
    }

    /* Empty state */
    .empty-state {
        text-align: center; padding: 48px 24px;
        color: #4a5568; font-size: 0.95rem;
    }
    .empty-state .icon { font-size: 2.5rem; margin-bottom: 12px; }

    /* Scrollbar global */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 3px; }

    /* Dataframe */
    .stDataFrame { border-radius: 10px; overflow: hidden; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: transparent;
        border-bottom: 1px solid #1e2433;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        color: #6b7280;
        padding: 8px 18px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: #13172a !important;
        color: #e8eaf0 !important;
        border-bottom: 2px solid #4f8ef7;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────
def add_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{ts}] {msg}")
    st.session_state.logs = st.session_state.logs[:200]


def _render_log_line(line: str) -> str:
    low = line.lower()
    ts_part = ""
    msg_part = line

    if line.startswith("[") and "]" in line:
        bracket_end = line.index("]") + 1
        ts_part = f'<span class="log-ts">{line[:bracket_end]}</span>'
        msg_part = line[bracket_end:]

    if any(w in low for w in ["erro", "error", "falha", "fail", "❌"]):
        cls = "log-error"
    elif any(w in low for w in ["sucesso", "success", "concluído", "enviado", "✅", "✓"]):
        cls = "log-success"
    elif any(w in low for w in ["aviso", "warn", "⚠"]):
        cls = "log-warn"
    elif any(w in low for w in ["info", "iniciando", "buscando", "🔍", "📤"]):
        cls = "log-info"
    else:
        cls = "log-default"

    return f'<div><span class="log-ts">{ts_part}</span><span class="{cls}">{msg_part}</span></div>'


def render_logs(lines: list[str]) -> str:
    if not lines:
        return '<div class="empty-state"><div class="icon">📭</div>Nenhum log ainda.</div>'
    html = "".join(_render_log_line(l) for l in lines)
    return f'<div class="log-box">{html}</div>'


# ── Inicialização ────────────────────────────────────────────────────────────
db.init_db()

for key, default in [
    ("scheduler_ativo", False),
    ("logs", []),
    ("rodando", False),
    ("refresh_count", 0),
    ("bulk_rodando", False),
    ("bulk_logs", []),
    ("bulk_resultado", None),
    ("bulk_stop", None),
    ("bulk_contatos", []),
    ("bulk_colunas", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;padding:8px 0 4px;">
        <span style="font-size:2rem;">🤖</span>
        <div>
            <div style="font-size:1.1rem;font-weight:700;color:#e8eaf0;line-height:1.2">Agente IA</div>
            <div style="font-size:0.72rem;color:#6b7280;letter-spacing:0.05em;text-transform:uppercase">Prospecção WhatsApp</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Status WhatsApp
    st.markdown("**📱 WhatsApp**")
    conn_status = verificar_conexao()
    if conn_status["conectado"]:
        st.markdown('<span class="badge badge-online">● Conectado</span>', unsafe_allow_html=True)
        if st.button("🔗 Gerar QR Code", use_container_width=True):
            qr = obter_qrcode()
            if qr:
                try:
                    img_bytes = base64.b64decode(qr.split(",")[-1])
                    st.image(img_bytes, caption="Escaneie com o WhatsApp")
                except Exception:
                    st.code(qr[:200])
            else:
                st.error("Erro ao obter QR Code")
    elif conn_status["estado"] == "offline":
        st.markdown('<span class="badge badge-offline">● API Offline</span>', unsafe_allow_html=True)
        st.caption("Evolution API nao esta rodando.\nConfigure no .env e inicie o servidor.")
    elif conn_status["estado"] == "não configurado":
        st.markdown('<span class="badge badge-idle">● Nao configurado</span>', unsafe_allow_html=True)
        st.caption("Preencha EVOLUTION_API_URL e EVOLUTION_INSTANCE no arquivo .env")
    else:
        estado = conn_status.get("estado", "desconectado").title()
        st.markdown(f'<span class="badge badge-offline">● {estado}</span>', unsafe_allow_html=True)
        if st.button("🔗 Gerar QR Code", use_container_width=True):
            qr = obter_qrcode()
            if qr:
                try:
                    img_bytes = base64.b64decode(qr.split(",")[-1])
                    st.image(img_bytes, caption="Escaneie com o WhatsApp")
                except Exception:
                    st.code(qr[:200])
            else:
                st.warning("Configure a Evolution API no .env")

    st.divider()

    # Configurações de campanha
    st.markdown("**⚙️ Campanha**")

    modo_nicho = st.radio(
        "Nicho",
        ["Geral", "Específico"],
        horizontal=True,
        help="Geral varre restaurantes, academias, salões, clínicas e muito mais automaticamente",
    )
    if modo_nicho == "Específico":
        nicho = st.text_input("Qual nicho?", value=settings.NICHO_BUSCA, placeholder="ex: restaurante")
    else:
        nicho = "geral"
        st.caption("Varredura automatica em 30+ nichos")

    cidade    = st.text_input("Cidade", value=settings.CIDADE_BUSCA, placeholder="ex: São Paulo (vazio = Brasil todo)")
    max_leads = st.slider("Leads por execução", 1, 100, settings.MAX_LEADS_POR_DIA)

    st.divider()

    # Agendador
    st.markdown("**⏰ Agendador**")
    proxima = get_proxima_execucao()
    st.caption(f"Próxima: **{proxima}**")

    sched_status = "badge-active" if st.session_state.scheduler_ativo else "badge-idle"
    sched_label  = "● Ativo" if st.session_state.scheduler_ativo else "● Inativo"
    st.markdown(f'<span class="badge {sched_status}">{sched_label}</span>', unsafe_allow_html=True)
    st.write("")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Iniciar", use_container_width=True, type="primary",
                     disabled=st.session_state.scheduler_ativo):
            iniciar_scheduler()
            st.session_state.scheduler_ativo = True
            add_log("Scheduler iniciado — turnos 08:00-17:00")
            st.rerun()
    with col2:
        if st.button("⏹ Parar", use_container_width=True,
                     disabled=not st.session_state.scheduler_ativo):
            parar_scheduler()
            st.session_state.scheduler_ativo = False
            add_log("Scheduler parado pelo usuário")
            st.rerun()

    st.divider()

    # Modo de prospecção
    st.markdown("**🌐 Modo de Prospecção**")
    modo_sites = st.toggle(
        "Prospecção de Sites",
        value=st.session_state.get("modo_sites", False),
        help="Busca apenas empresas sem site e envia mockup de landing page como pitch",
    )
    st.session_state["modo_sites"] = modo_sites
    if modo_sites:
        st.markdown(
            '<div style="background:rgba(0,212,170,0.08);border:1px solid rgba(0,212,170,0.3);'
            'border-radius:8px;padding:8px 12px;color:#00d4aa;font-size:0.82rem;">'
            '🌐 Envia mockup de site personalizado para empresas sem website</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")


# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.markdown("""
    <h1 style="margin:0;font-size:1.7rem;font-weight:800;
               background:linear-gradient(90deg,#4f8ef7,#00d4aa);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent">
        Agente de Prospecção IA
    </h1>
    """, unsafe_allow_html=True)
with col_refresh:
    if st.button("↻ Atualizar", use_container_width=True):
        st.rerun()

st.write("")

# ── Métricas ─────────────────────────────────────────────────────────────────
stats = db.get_stats()
c1, c2, c3, c4 = st.columns(4)

total_p   = stats["total_prospects"]
total_e   = stats["total_enviados"]
total_err = stats["total_erros"]
taxa_ok   = f"{round(total_e / total_p * 100)}%" if total_p > 0 else "—"

c1.metric("🎯 Prospects", total_p)
c2.metric("📤 Enviados", total_e)
c3.metric("⚡ Taxa de Envio", taxa_ok)
c4.metric("❌ Erros", total_err)

st.write("")

# ── Execução Manual ───────────────────────────────────────────────────────────
st.markdown("""
<div class="section-header">
    <h3>▶ Execução Manual</h3>
    <div class="section-line"></div>
</div>
""", unsafe_allow_html=True)

_modo_sites_ativo = st.session_state.get("modo_sites", False)

col_btn, col_info = st.columns([1, 3])
with col_btn:
    _btn_label = "🌐 Prospectar Sites" if _modo_sites_ativo else "🚀 Executar Agora"
    executar = st.button(
        _btn_label,
        use_container_width=True,
        type="primary",
        disabled=st.session_state.rodando,
    )
with col_info:
    if _modo_sites_ativo:
        st.markdown(
            f'<div class="info-banner" style="border-left-color:#00d4aa;">'
            f'Buscará empresas de <strong>{nicho or "..."}</strong> em <strong>{cidade or "..."}</strong> '
            f'<strong>sem site</strong>, gerará um mockup de landing page personalizado e enviará via WhatsApp.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="info-banner">Buscará até <strong>{max_leads}</strong> leads de '
            f'<strong>{nicho or "..."}</strong> em <strong>{cidade or "..."}</strong> '
            f'e enviará mensagens via WhatsApp.</div>',
            unsafe_allow_html=True,
        )

if executar and not st.session_state.rodando:
    st.session_state.rodando = True
    log_container    = st.empty()
    result_container = st.empty()
    logs_locais: list[str] = []

    def _callback(msg: str):
        logs_locais.append(msg)
        add_log(msg)
        log_container.markdown(render_logs(logs_locais[-30:]), unsafe_allow_html=True)

    with st.spinner("Agente em execução…"):
        try:
            if _modo_sites_ativo:
                resultado = executar_ciclo_sites(
                    nicho=nicho, cidade=cidade, max_leads=max_leads,
                    callback=_callback,
                )
                result_container.success(
                    f"✅ Concluído! "
                    f"Leads encontrados: **{resultado['leads_encontrados']}** | "
                    f"Sem site: **{resultado['sem_site']}** | "
                    f"Enviados: **{resultado['enviados']}** | "
                    f"Erros: **{resultado['erros']}**"
                )
            else:
                resultado = executar_ciclo(
                    nicho=nicho, cidade=cidade, max_leads=max_leads,
                    canal="whatsapp", callback=_callback,
                )
                result_container.success(
                    f"✅ Concluído! "
                    f"Leads: **{resultado['leads_encontrados']}** | "
                    f"Novos: **{resultado['novos']}** | "
                    f"Enviados: **{resultado['enviados']}** | "
                    f"Erros: **{resultado['erros']}**"
                )
        except Exception as e:
            result_container.error(f"❌ Erro na execução: {e}")
            add_log(f"ERRO: {e}")
        finally:
            st.session_state.rodando = False

st.write("")

# ── Tabs de dados ─────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋  Prospects", "📊  Execuções", "📨  Disparos em Massa", "📝  Logs"])

with tab1:
    if stats["prospects"]:
        df = pd.DataFrame(
            stats["prospects"],
            columns=["Nome", "E-mail", "Telefone", "Nicho", "Cidade", "Status", "Enviado em"],
        )
        status_icons = {"enviado": "🟢", "erro": "🔴", "pendente": "🟡"}
        df["Status"] = df["Status"].apply(
            lambda x: f"{status_icons.get(x, '⚪')} {x or 'N/A'}"
        )
        st.dataframe(df, use_container_width=True, height=420)

        col_dl, col_total = st.columns([1, 3])
        with col_dl:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇ Exportar CSV", csv, "prospects.csv", "text/csv",
                               use_container_width=True)
        with col_total:
            enviados_n = (df["Status"].str.startswith("🟢")).sum()
            erros_n    = (df["Status"].str.startswith("🔴")).sum()
            st.caption(f"{enviados_n} enviados · {erros_n} com erro · {len(df) - enviados_n - erros_n} pendentes")
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">🎯</div>
            <div>Nenhum prospect ainda.<br>Execute o agente para começar.</div>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    if stats["execucoes"]:
        df_exec = pd.DataFrame(
            stats["execucoes"],
            columns=["ID", "Início", "Fim", "Leads", "Enviados", "Erros", "Status"],
        )
        st.dataframe(df_exec, use_container_width=True, height=280)

        if len(df_exec) >= 2:
            df_chart = df_exec.tail(14).copy()
            fig = go.Figure()
            fig.add_bar(
                name="Enviados", x=df_chart["Início"], y=df_chart["Enviados"],
                marker_color="#00d4aa", marker_line_width=0,
            )
            fig.add_bar(
                name="Erros", x=df_chart["Início"], y=df_chart["Erros"],
                marker_color="#ff4b6e", marker_line_width=0,
            )
            fig.update_layout(
                title=dict(text="Desempenho das últimas execuções", font_color="#c8cfe0", font_size=15),
                barmode="group",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(13,17,27,0.6)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=48, b=0),
                height=320,
                xaxis=dict(gridcolor="#1e2433"),
                yaxis=dict(gridcolor="#1e2433"),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📊</div>
            <div>Nenhuma execução registrada ainda.</div>
        </div>
        """, unsafe_allow_html=True)

with tab3:
    # ── Disparos em Massa ─────────────────────────────────────────────────────
    st.markdown("""
    <div class="section-header">
        <h3>📨 Disparo em Massa com Anti-Ban</h3>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    # Upload da planilha
    col_up, col_info_up = st.columns([2, 3])
    with col_up:
        arquivo = st.file_uploader(
            "Lista de contatos (Excel ou CSV)",
            type=["xlsx", "xls", "csv"],
            help="Planilha com colunas: Telefone (obrigatório), Nome (opcional), e outros campos para personalização",
        )
    with col_info_up:
        st.markdown("""
        <div class="info-banner" style="margin-top:28px">
        Formato esperado: coluna <strong>Telefone</strong> (obrigatória) + <strong>Nome</strong> (opcional).<br>
        Outros campos podem ser usados na mensagem como <code>{campo}</code>.
        </div>
        """, unsafe_allow_html=True)

    if arquivo:
        try:
            contatos, colunas = ler_planilha(arquivo.read(), arquivo.name)
            st.session_state.bulk_contatos = contatos
            st.session_state.bulk_colunas  = colunas
        except Exception as e:
            st.error(f"Erro ao ler planilha: {e}")

    if st.session_state.bulk_contatos:
        contatos_bulk = st.session_state.bulk_contatos
        colunas_bulk  = st.session_state.bulk_colunas

        st.caption(f"{len(contatos_bulk)} contatos carregados | Colunas: {', '.join(colunas_bulk)}")

        # Preview dos primeiros contatos
        with st.expander("Pré-visualização da planilha", expanded=False):
            import pandas as _pd
            st.dataframe(_pd.DataFrame(contatos_bulk[:10]), use_container_width=True, height=220)

        st.divider()

        # Mensagem template
        st.markdown("**Mensagem padrão**")
        _variaveis_hint = "  ".join([f"`{{{c.lower()}}}`" for c in colunas_bulk])
        st.caption(f"Variáveis disponíveis: {_variaveis_hint}")

        bulk_mensagem = st.text_area(
            "Mensagem",
            value=st.session_state.get("bulk_mensagem_salva", "Olá, {nome}! Tudo bem?\n\nVi que você pode se interessar por..."),
            height=140,
            placeholder="Use {nome}, {cidade}, etc. para personalizar",
            label_visibility="collapsed",
        )
        st.session_state["bulk_mensagem_salva"] = bulk_mensagem

        # Preview da mensagem com primeiro contato
        if contatos_bulk and bulk_mensagem.strip():
            primeiro = contatos_bulk[0]
            variaveis_preview = {k.lower(): (v or "") for k, v in primeiro.items() if v}
            try:
                preview_txt = bulk_mensagem.format_map(
                    {**{"nome": "", "cidade": "", "empresa": ""}, **variaveis_preview}
                )
            except Exception:
                preview_txt = bulk_mensagem
            with st.expander("Pré-visualização da mensagem (1° contato)", expanded=True):
                st.markdown(
                    f'<div style="background:#080b10;border:1px solid #1e2433;border-radius:10px;'
                    f'padding:14px 18px;font-family:monospace;color:#c8cfe0;white-space:pre-wrap;">'
                    f'{preview_txt}</div>',
                    unsafe_allow_html=True,
                )

        st.divider()

        # Configurações anti-ban (defaults sempre definidos antes do expander)
        delay_min      = 20
        delay_max      = 45
        tamanho_lote   = 15
        pausa_lote_min = 240
        pausa_lote_max = 540
        limite_diario  = 200

        with st.expander("Configuracoes Anti-Ban", expanded=False):
            ab_col1, ab_col2 = st.columns(2)
            with ab_col1:
                delay_min    = st.slider("Delay minimo entre msgs (s)", 5, 120, 20)
                delay_max    = st.slider("Delay maximo entre msgs (s)", delay_min, 180, max(delay_min + 5, 45))
                tamanho_lote = st.slider("Msgs por lote", 5, 50, 15,
                                         help="Apos esse numero, faz pausa longa")
            with ab_col2:
                pausa_lote_min = st.slider("Pausa entre lotes - min (min)", 1, 30, 4) * 60
                pausa_lote_max = st.slider("Pausa entre lotes - max (min)", 1, 60, 9) * 60
                limite_diario  = st.slider("Limite de envios nessa sessao", 10, 500, 200)

            st.markdown("""
            <div class="info-banner" style="margin-top:8px">
            <strong>Como funciona o anti-ban:</strong>
            delay aleatorio humanizado entre msgs + pausa longa entre lotes +
            variacao invisivel em cada mensagem (evita deteccao de msg duplicada).
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # Botões de controle
        bcol1, bcol2, bcol3 = st.columns([1, 1, 3])
        with bcol1:
            iniciar_bulk = st.button(
                "Disparar",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.bulk_rodando or not bulk_mensagem.strip(),
            )
        with bcol2:
            parar_bulk = st.button(
                "Parar",
                use_container_width=True,
                disabled=not st.session_state.bulk_rodando,
            )
        with bcol3:
            if st.session_state.bulk_resultado:
                r = st.session_state.bulk_resultado
                st.markdown(
                    f'<div class="info-banner" style="border-left-color:#00d4aa;">'
                    f'Ultimo disparo: <strong>{r["enviados"]}</strong> enviados | '
                    f'<strong>{r["erros"]}</strong> erros | '
                    f'<strong>{r["pulados"]}</strong> pulados</div>',
                    unsafe_allow_html=True,
                )

        # Iniciar disparo em thread separada
        if iniciar_bulk and not st.session_state.bulk_rodando:
            stop_ev = threading.Event()
            st.session_state.bulk_stop      = stop_ev
            st.session_state.bulk_rodando   = True
            st.session_state.bulk_resultado = None
            st.session_state.bulk_logs      = []

            def _bulk_callback(msg: str):
                ts = datetime.now().strftime("%H:%M:%S")
                entrada = f"[{ts}] {msg}"
                st.session_state.bulk_logs.insert(0, entrada)
                st.session_state.bulk_logs = st.session_state.bulk_logs[:500]
                add_log(msg)

            def _run_bulk():
                try:
                    res = disparar_em_massa(
                        contatos=contatos_bulk,
                        mensagem_template=bulk_mensagem,
                        delay_min=delay_min,
                        delay_max=delay_max,
                        tamanho_lote=tamanho_lote,
                        pausa_lote_min=pausa_lote_min,
                        pausa_lote_max=pausa_lote_max,
                        limite_diario=limite_diario,
                        stop_event=stop_ev,
                        callback=_bulk_callback,
                    )
                    st.session_state.bulk_resultado = res
                finally:
                    st.session_state.bulk_rodando = False

            t = threading.Thread(target=_run_bulk, daemon=True)
            t.start()
            st.rerun()

        # Parar disparo
        if parar_bulk and st.session_state.bulk_stop:
            st.session_state.bulk_stop.set()
            st.info("Sinal de parada enviado — aguardando a mensagem atual finalizar...")

        # Status e log em tempo real
        if st.session_state.bulk_rodando:
            st.markdown(
                '<div class="badge badge-active" style="margin:8px 0;">● Disparo em andamento...</div>',
                unsafe_allow_html=True,
            )
        elif st.session_state.bulk_logs and not st.session_state.bulk_rodando:
            st.markdown(
                '<div class="badge badge-idle" style="margin:8px 0;">● Disparo finalizado</div>',
                unsafe_allow_html=True,
            )

        if st.session_state.bulk_logs:
            st.markdown(render_logs(st.session_state.bulk_logs[:60]), unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📂</div>
            <div>Importe uma planilha Excel ou CSV com os contatos para comecar.</div>
        </div>
        """, unsafe_allow_html=True)


with tab4:
    col_log_hdr, col_log_btn = st.columns([4, 1])
    with col_log_hdr:
        st.caption(f"{len(st.session_state.logs)} entradas")
    with col_log_btn:
        if st.button("🗑 Limpar", use_container_width=True):
            st.session_state.logs = []
            st.rerun()

    st.markdown(render_logs(st.session_state.logs[:60]), unsafe_allow_html=True)


# ── Auto-refresh quando scheduler ativo ──────────────────────────────────────
if st.session_state.scheduler_ativo:
    import time
    time.sleep(30)
    st.rerun()
