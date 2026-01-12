import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from streamlit_cookies_manager import EncryptedCookieManager
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard CISM (Gestão Financeira)")

# --- Configuração de Cookies ---
try:
    cookies = EncryptedCookieManager(
        prefix="cism_dash_v2_",
        password=st.secrets["cookies"]["secret_key"]
    )
except Exception:
    st.error("Erro no Cookie Manager. Verifique secrets.toml [cookies].")
    st.stop()

if not cookies.ready():
    st.stop()

# --- CSS: Estilo "One Page" Compacto & Tema Dinâmico ---
st.markdown("""
<style>
    /* 1. Remove cabeçalho e rodapé padrão */
    .stAppHeader, footer, #MainMenu {visibility: hidden; display: none;}
    
    /* 2. Reduz padding do container principal - MAXIMIZA ESPAÇO */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* 3. Cards de KPI - Compatível com Dark/Light Mode */
    [data-testid="stMetric"] {
        background-color: var(--streamlit-secondary-background-color); /* Usa a cor secundária do tema atual */
        border: 1px solid var(--streamlit-base-border-color); /* Borda sutil do tema */
        padding: 10px !important;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 600;
        color: var(--streamlit-text-color) !important; /* Cor texto padrão */
        opacity: 0.8;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
        font-weight: 700;
        color: var(--streamlit-primary-color) !important; /* Cor primária (azul/rosa do tema) */
    }

    /* 4. Estilo dos Gráficos Plotly no Streamlit */
    [data-testid="stPlotlyChart"] {
        background-color: var(--streamlit-secondary-background-color);
        border-radius: 8px;
        border: 1px solid var(--streamlit-base-border-color);
        padding: 5px;
    }

    /* 5. Títulos mais compactos */
    h3, h4, h5 {
        margin-top: 0.2rem !important;
        margin-bottom: 0.5rem !important;
        padding-top: 0rem !important;
    }
</style>
""", unsafe_allow_html=True)


# --- Funções de Autenticação (Mantidas) ---
def check_password():
    if cookies.get('logged_in') == 'True':
        return True
    
    # Centraliza login
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("🔐 Login CISM")
        st.markdown("Acesso restrito ao dashboard financeiro.")
        with st.form("login"):
            user = st.text_input("Usuário")
            pwd = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                try:
                    if user == st.secrets["auth"]["username"] and pwd == st.secrets["auth"]["password"]:
                        cookies['logged_in'] = 'True'
                        cookies.save()
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")
                except Exception:
                    st.error("Configure [auth] no secrets.toml")
    return False

if not check_password():
    st.stop()
    
def logout():
    cookies['logged_in'] = 'False'
    cookies.save()
    st.rerun()

# --- Carregamento de Dados (Aba CISM) ---
@st.cache_data(ttl=600)
def load_data():
    try:
        creds = st.secrets["gcp_service_account"]
        sheet_id = st.secrets["sheets_config"]["sheet_id"]
        try: sheet_name = st.secrets["sheets_config"]["sheet_name"]
        except: sheet_name = "CISM"

        gc = gspread.service_account_from_dict(creds)
        sh = gc.open_by_key(sheet_id)
        
        try: ws = sh.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound: ws = sh.worksheet("CISM")

        data = ws.get_all_values()
        if len(data) < 2: return pd.DataFrame()
            
        header = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=header)
        
        # --- LIMPEZA DOS NOMES DAS COLUNAS (Espaços invisíveis) ---
        df.columns = [c.strip() for c in df.columns]

        # Verifica 'Fonte'
        if 'Fonte' not in df.columns:
            st.error(f"Coluna 'Fonte' não encontrada. Colunas: {list(df.columns)}")
            return pd.DataFrame()

        # Limpeza Numérica
        def clean_currency(x):
            if isinstance(x, str):
                x = x.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
            return pd.to_numeric(x, errors='coerce')

        if 'Valor' in df.columns:
            df['Valor_Num'] = df['Valor'].apply(clean_currency)
        else:
            df['Valor_Num'] = 0.0

        # Data
        if 'Data' in df.columns:
            df['Data_dt'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

df = load_data()

# --- BARRA SUPERIOR (Compacta) ---
# Título na esquerda, Botão Sair na direita
c_top1, c_top2 = st.columns([6, 1])
with c_top1:
    st.markdown("### 📊 Dashboard Financeiro CISM")
with c_top2:
    if st.button("Sair", key="logout_btn"):
        logout()

if df.empty:
    st.warning("Dados não carregados.")
    st.stop()

# --- FILTROS (Linha única, muito compacta) ---
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    fontes_lst = sorted(list(df['Fonte'].astype(str).unique()))
    projetos_lst = sorted(list(df['Projeto'].astype(str).unique()))
    anos_lst = sorted(list(df['ano'].astype(str).unique()))
    
    # Filtros com label_visibility="collapsed" para economizar altura se precisar, 
    # mas mantive labels curtos para clareza
    sel_anos = c1.multiselect("Ano", options=anos_lst, placeholder="Todos")
    sel_fontes = c2.multiselect("Fonte Pagadora", options=fontes_lst, placeholder="Todas")
    sel_projs = c3.multiselect("Projeto", options=projetos_lst, placeholder="Todos")
    
    # Status (se existir)
    status_lst = sorted(list(df['status'].astype(str).unique())) if 'status' in df.columns else []
    sel_status = c4.multiselect("Status", options=status_lst, placeholder="Todos")

# Aplica Filtros
df_ok = df.copy()
if sel_fontes: df_ok = df_ok[df_ok['Fonte'].isin(sel_fontes)]
if sel_projs: df_ok = df_ok[df_ok['Projeto'].isin(sel_projs)]
if sel_anos: df_ok = df_ok[df_ok['ano'].isin(sel_anos)]
if sel_status: df_ok = df_ok[df_ok['status'].isin(sel_status)]

st.markdown("---") 

# --- LINHA 1: KPIs (Cards) ---
# Cálculo
val_total = df_ok['Valor_Num'].sum()
qtd_proj = df_ok['Projeto'].nunique()
# Fonte que mais pagou no filtro
top_fonte_nome = "-"
if not df_ok.empty:
    grp_fonte = df_ok.groupby('Fonte')['Valor_Num'].sum()
    if not grp_fonte.empty:
        top_fonte_nome = f"{grp_fonte.idxmax()} ({grp_fonte.max()/val_total:.0%})"

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Executado", f"R$ {val_total:,.2f}".replace(",", "_").replace(".", ",").replace("_", "."))
k2.metric("Projetos Ativos", qtd_proj)
k3.metric("Fonte Principal (%)", top_fonte_nome)
k4.metric("Registros", len(df_ok))

# --- GRÁFICOS (Layout Otimizado) ---
st.markdown("#### 🔄 Fluxos e Distribuição dos Recursos")

# Configuração Padrão Plotly (Remove fundo para fundir com card)
pc = {'displayModeBar': False}
layout_transparent = {
    'paper_bgcolor': 'rgba(0,0,0,0)',
    'plot_bgcolor': 'rgba(0,0,0,0)',
    'margin': dict(t=20, b=20, l=10, r=10),
    'font': {'family': "Arial, sans-serif"}
}

# LINHA 2: Sankey (Esquerda) + Barra de Top Fontes (Direita)
r2_col1, r2_col2 = st.columns([2, 1])

with r2_col1:
    st.markdown("##### 🔀 Fluxo Financeiro: Fonte ➝ Projeto")
    
    if not df_ok.empty:
        # Prepara dados
        df_sk = df_ok.groupby(['Fonte', 'Projeto'])['Valor_Num'].sum().reset_index()
        
        # [CORREÇÃO] Filtro de Ruído: Remove fluxos muito pequenos que causam sobreposição de texto
        # Remove conexões que representam menos de 0.1% do total filtrado para limpar o gráfico
        limit_val = df_sk['Valor_Num'].sum() * 0.001 
        df_sk = df_sk[df_sk['Valor_Num'] > limit_val]

        nodes = list(pd.concat([df_sk['Fonte'], df_sk['Projeto']]).unique())
        node_map = {n: i for i, n in enumerate(nodes)}
        
        # Cores dos Nós (Azul para Fonte, Verde para Projeto)
        node_colors = ['#1f77b4' if n in df_sk['Fonte'].values else '#2ca02c' for n in nodes]
        
        # [CORREÇÃO] Cores dos Links: Cinza semitransparente para ser visível no branco
        # Antes estava automático (branco/transparente que sumia)
        
        fig_sk = go.Figure(data=[go.Sankey(
            node=dict(
                pad=30, # [CORREÇÃO] Maior espaçamento vertical para evitar texto encavalado
                thickness=20,
                line=dict(color="black", width=0.5),
                label=nodes,
                color=node_colors
            ),
            link=dict(
                source=df_sk['Fonte'].map(node_map),
                target=df_sk['Projeto'].map(node_map),
                value=df_sk['Valor_Num'],
                color='rgba(150, 150, 150, 0.5)', # [CORREÇÃO] Cor cinza visível
                hovertemplate='De: %{source.label}<br>Para: %{target.label}<br>Valor: R$ %{value:,.2f}<extra></extra>'
            ),
            textfont=dict(size=11, color="rgba(0,0,0,1)") # [CORREÇÃO] Texto preto forçado para legibilidade
        )])

        fig_sk.update_layout(height=500, **layout_transparent)
        st.plotly_chart(fig_sk, use_container_width=True, config=pc)
    else:
        st.info("Sem dados.")

with r2_col2:
    st.markdown("**Top Fontes de Recurso**")
    if not df_ok.empty:
        df_bar_src = df_ok.groupby('Fonte')['Valor_Num'].sum().reset_index().sort_values('Valor_Num', ascending=True)
        fig_src = px.bar(df_bar_src, x='Valor_Num', y='Fonte', orientation='h', text_auto='.2s')
        fig_src.update_layout(height=500, xaxis_title=None, yaxis_title=None, **layout_transparent)
        fig_src.update_traces(marker_color='#3366CC')
        st.plotly_chart(fig_src, use_container_width=True, config=pc)

# LINHA 3: Composição por Projeto (Novo!) + Evolução
st.markdown("#### 📊 Análise por Projeto")
r3_col1, r3_col2 = st.columns([1.5, 1])

with r3_col1:
    st.markdown("**Composição de Custo: Qual Fonte paga cada Projeto?**")
    if not df_ok.empty:
        # Gráfico de barras empilhadas: Eixo X = Projeto, Cor = Fonte
        df_comp = df_ok.groupby(['Projeto', 'Fonte'])['Valor_Num'].sum().reset_index()
        # Ordena projetos pelo valor total
        order_proj = df_ok.groupby('Projeto')['Valor_Num'].sum().sort_values(ascending=False).index
        
        fig_comp = px.bar(
            df_comp, x='Projeto', y='Valor_Num', color='Fonte',
            category_orders={'Projeto': order_proj},
            labels={'Valor_Num': 'Valor (R$)'}
        )
        # Move legenda para o topo para não bater nos nomes dos projetos (eixo X rotacionado)
        fig_comp.update_layout(
            height=400, 
            legend=dict(orientation="h", y=1.2, x=0, xanchor='left'), 
            **layout_transparent
        )
        st.plotly_chart(fig_comp, use_container_width=True, config=pc)

with r3_col2:
    st.markdown("**Desembolso no Tempo (Mês)**")
    if not df_ok.empty and 'Data_dt' in df_ok.columns:
        df_time = df_ok.groupby(pd.Grouper(key='Data_dt', freq='M'))['Valor_Num'].sum().reset_index()
        fig_line = px.area(df_time, x='Data_dt', y='Valor_Num')
        fig_line.update_layout(height=400, xaxis_title=None, yaxis_title=None, **layout_transparent)
        st.plotly_chart(fig_line, use_container_width=True, config=pc)

# Detalhes finais (escondidos)
with st.expander("📋 Ver Tabela de Dados Completa"):
    st.dataframe(
        df_ok,
        use_container_width=True,
        hide_index=True,
        column_config={"Valor_Num": st.column_config.NumberColumn("Valor", format="R$ %.2f")}
    )
