import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime
import gspread 
from streamlit_cookies_manager import EncryptedCookieManager

# --- CONFIGURAÇÃO DE COOKIES PARA PERSISTÊNCIA DE LOGIN ---
try:
    cookies = EncryptedCookieManager(
        prefix="cism_dash_auth_",
        password=st.secrets["cookies"]["secret_key"] 
    )
except KeyError:
    st.error("Erro de Configuração: A chave secreta do cookie (secrets.toml [cookies]) não foi definida.")
    st.stop()
except Exception as e:
    st.error(f"Erro ao inicializar Cookie Manager: {e}")
    st.stop()

if not cookies.ready():
    st.stop()


# --- VARIÁVEIS DE ESTADO E FUNÇÕES DE LOGIN/LOGOUT ---

def logout():
    """Função para deslogar, limpando a sessão e os cookies."""
    st.session_state["password_correct"] = False
    if "authenticated_user" in st.session_state:
        del st.session_state["authenticated_user"]
    
    cookies['logged_in'] = 'False'
    cookies['user'] = ''
    cookies.save()
    st.cache_data.clear()
    st.rerun() 


def check_password():
    """
    Controla o fluxo de login, persistindo o estado via cookies, e exibe a tela de login profissional.
    Retorna True se o usuário estiver autenticado, senão False.
    """
    
    # 1. Tenta acessar os segredos de autenticação
    try:
        users = {st.secrets["auth"]["username"]: st.secrets["auth"]["password"]}
    except KeyError:
        st.error("Erro de Configuração: As credenciais de login não foram encontradas no st.secrets. Verifique a seção [auth].")
        return False
    
    # --- Lógica de Login: Define o estado após submissão ---
    def password_entered():
        if st.session_state["username"] in users and st.session_state["password"] == users[st.session_state["username"]]:
            st.session_state["password_correct"] = True
            st.session_state["authenticated_user"] = st.session_state["username"]
            del st.session_state["password"]
            
            cookies['logged_in'] = 'True'
            cookies['user'] = st.session_state["username"]
            cookies.save()
            
        else:
            st.session_state["password_correct"] = False

    # 2. VERIFICAÇÃO DE ESTADO
    is_logged_in_via_cookie = cookies.get('logged_in') == 'True'
    is_logged_in_via_session = st.session_state.get("password_correct", False)
    
    if is_logged_in_via_cookie or is_logged_in_via_session:
        if is_logged_in_via_cookie and not is_logged_in_via_session:
             st.session_state["authenticated_user"] = cookies.get('user')
             st.session_state["password_correct"] = True 
             
        # Adiciona o botão de Logout na sidebar
        with st.sidebar:
            st.button("Sair (Logout)", on_click=logout, type="secondary")
        
        return True 

    # 3. EXIBE O FORMULÁRIO DE LOGIN (APARÊNCIA PROFISSIONAL E CENTRALIZADA)
    col_vazio1, col_form, col_vazio2 = st.columns([1, 2, 1])
    
    with col_form:
        st.title("Acesso Restrito - Dashboard CISM")
        st.info("Por favor, insira suas credenciais para continuar.")
        
        with st.form("login_form", clear_on_submit=False):
            st.subheader("Autenticação de Usuário")
            
            st.text_input("Usuário", key="username", placeholder="Nome de usuário")
            st.text_input("Senha", type="password", key="password", placeholder="Senha de acesso")
            
            st.form_submit_button("Acessar o Dashboard", on_click=password_entered, type="primary")
        
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("Usuário ou Senha incorretos.")
            
    return False

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard de Projetos Sigeo")

# --- Paleta de Cores e CSS ---
COLOR_PALETTE = {
    "primary": "#0D6E6E", 
    "secondary": "#007A9E", 
    "background": "#F0F2F6",
    "sidebar_bg": "#FFFFFF",
    "text_dark": "#31333F",
    "text_light": "#555555",
    "kpi_border": "#E0E0E0" 
}
MEDICAL_BLUE = COLOR_PALETTE["secondary"]

# --- CSS INJETADO (ESTILO "ROBUSTO PROFISSIONAL" + RESPONSIVIDADE) ---
st.markdown(f"""
<style>
    /* --- CONFIGURAÇÃO GERAL "ROBUSTO PROFISSIONAL" --- */
    /* Define a fonte Arial (robusta) para todo o app */
    body, .stApp, input, textarea, button, select, p, div, span {{
        font-family: Arial, Helvetica, sans-serif !important; 
    }}

    /* --- PÁGINA PRINCIPAL E SIDEBAR --- */
    [data-testid="stAppViewContainer"] > .main {{ 
        background-color: {COLOR_PALETTE['background']}; 
    }}
    
    [data-testid="stSidebar"] {{ 
        background-color: {COLOR_PALETTE['sidebar_bg']}; 
        border-right: 1px solid {COLOR_PALETTE['kpi_border']};
        border-radius: 0px;
    }}
    
    h1, h2, h3 {{ 
        color: {COLOR_PALETTE['primary']}; 
        font-family: Arial, Helvetica, sans-serif !important; 
    }}
    
    /* --- ESTILO DE "CARDS" (Melhor Prática) --- */

    /* Estilo dos KPIs (Métricas) */
    [data-testid="stMetric"] {{
        background-color: #FFFFFF; 
        border: 1px solid {COLOR_PALETTE['kpi_border']}; 
        border-radius: 10px; /* Cantos levemente arredondados */
        padding: 20px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); /* Sombra sutil */
    }}
    
    /* Estilo dos Gráficos */
    [data-testid="stPlotlyChart"] {{
        background-color: #FFFFFF; 
        border: 1px solid {COLOR_PALETTE['kpi_border']};
        border-radius: 10px; /* Cantos levemente arredondados */
        padding: 10px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); /* Sombra sutil */
    }}
    
    /* Estilo do Formulário de Login (na página de login) */
    [data-testid="stForm"] {{
        background-color: #FFFFFF;
        border: 1px solid {COLOR_PALETTE['kpi_border']};
        padding: 25px;
        border-radius: 10px; /* Cantos levemente arredondados */
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); /* Sombra sutil */
    }}
    
    /* --- OUTROS ELEMENTOS --- */
    
    /* Tabela de dados */
    [data-testid="stDataFrame"] {{
        border: 1px solid {COLOR_PALETTE['kpi_border']};
        border-radius: 8px; /* Arredondamento sutil para combinar */
    }}
    
    /* Botões */
    [data-testid="stButton"] > button, 
    [data-testid="stFormSubmitButton"] > button {{
        border-radius: 8px !important; /* Cantos sutis */
        border: 1px solid {COLOR_PALETTE['kpi_border']};
    }}

    /* Correção de KPI (mantida) */
    [data-testid="stMetricValue"] {{ 
        color: {COLOR_PALETTE['text_dark']}; 
        font-size: 2.2rem; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        font-family: Arial, Helvetica, sans-serif !important; 
    }}

    /* --- AJUSTES PARA RESPONSIVIDADE MÓVEL --- */
    @media (max-width: 768px) {{
        
        /* Força os st.columns() a empilhar verticalmente em telas pequenas */
        [data-testid="stHorizontalBlock"] {{
            flex-direction: column !important;
            flex-wrap: wrap !important;
        }}

        /* Garante que os itens empilhados ocupem a largura total */
        [data-testid="stHorizontalBlock"] > div[data-testid^="stVerticalBlock"] {{
             width: 100% !important;
             flex: 1 1 100% !important; 
             margin-bottom: 15px; 
        }}
        
        [data-testid="stHorizontalBlock"] > div[data-testid^="stVerticalBlock"]:last-child {{
             margin-bottom: 0px;
        }}

        [data-testid="stMetric"] {{
            padding: 15px;
        }}

        [data-testid="stMetricValue"] {{ 
            font-size: 1.8rem;
        }}
    }}
</style>
""", unsafe_allow_html=True)


# --- Funções de Ajuda ---
def limpar_nome_coluna(col_name):
    if isinstance(col_name, str):
        return col_name.strip()
    return col_name

def limpar_e_converter_monetario(series):
    """Limpa e converte colunas monetárias (string 'R$ 1.000,00') para número."""
    if series.dtype == 'object':
        series = series.astype(str)
        series = series.str.replace(r'[R$\s]+', '', regex=True) # Remove R$ e espaços
        series = series.str.replace('.', '', regex=False)      # Remove . de milhar
        series = series.str.replace(',', '.', regex=False)      # Troca , de decimal por .
    return pd.to_numeric(series, errors='coerce')

# --- Carregamento SEGURO dos Dados do Google Sheets (Aba 1 - Projetos) ---
@st.cache_data(ttl=600)
def carregar_dados_sheets_seguro():
    """Conecta-se ao Google Sheets de forma segura, limpa e converte os dados."""
    
    try:
        sheet_id = st.secrets["sheets_config"]["sheet_id"]
        sheet_name = st.secrets["sheets_config"]["sheet_name"]
        creds = st.secrets["gcp_service_account"]
        
        with st.spinner('⌛ Conectando ao Google Sheets e carregando dados (Aba 1)...'):
            gc = gspread.service_account_from_dict(creds)
            sh = gc.open_by_key(sheet_id)
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_values()
            
            df = pd.DataFrame(data[1:], columns=data[0]) 
            df.columns = [limpar_nome_coluna(col) for col in df.columns]

            df['Liberações'] = limpar_e_converter_monetario(df['Liberações'])
            df['Valor Reservado'] = limpar_e_converter_monetario(df['Valor Reservado'])
            df['Valor Pago'] = limpar_e_converter_monetario(df['Valor Pago'])

            if 'Inic.Vigencia' in df.columns:
                df['Inic.Vigencia'] = pd.to_datetime(df['Inic.Vigencia'], format='%d/%m/%Y', errors='coerce')
            if 'Fim Vigencia' in df.columns:
                df['Fim Vigencia'] = pd.to_datetime(df['Fim Vigencia'], format='%d/%m/%Y', errors='coerce')
            df = df.dropna(subset=['Inic.Vigencia', 'Fim Vigencia'])
            return df
        
    except KeyError as e:
        st.error(f"Erro de Configuração (Aba 1): Falha ao acessar o segredo: {e}. Verifique o seu secrets.toml.")
        return pd.DataFrame()
    except Exception as e:
        st.error("Erro Crítico de Conexão (Aba 1): Não foi possível carregar os dados do Google Sheet.")
        st.warning(f"Detalhe: {e}")
        st.info("Verifique as permissões de acesso da Aba 1.")
        return pd.DataFrame()

# --- [ATUALIZADO V4] Carregamento SEGURO dos Dados (Aba 2 - Relatório "Balancete") ---
@st.cache_data(ttl=600)
def carregar_dados_relatorio_seguro():
    """
    Conecta-se ao Google Sheets e processa a aba de "Relatório" (Balancete),
    usando a lógica de parsing V4 (flexível com st.secrets).
    """
    try:
        # --- 1. LEITURA DOS SECRETS ---
        sheet_id = st.secrets["sheets_config"]["sheet_id"]
        sheet_name = st.secrets["sheets_config"]["sheet_name_report"] 
        creds = st.secrets["gcp_service_account"]
        
        col_conta = st.secrets["parser_config"]["col_conta_corrente"]
        col_alinea = st.secrets["parser_config"]["col_alinea"]
        col_desc = st.secrets["parser_config"]["col_descricao"]
        col_val_concedido = st.secrets["parser_config"]["col_valor_concedido"]
        
    except KeyError as e:
        st.error(f"Erro de Configuração: Falha ao acessar o segredo: {e}.")
        st.info(f"Verifique se as seções [sheets_config] e [parser_config] existem no seu secrets.toml.")
        return pd.DataFrame()
        
    try:
        # --- 2. CONEXÃO ---
        with st.spinner(f'⌛ Conectando ao Google Sheets e processando Relatório ("{sheet_name}")...'):
            gc = gspread.service_account_from_dict(creds)
            sh = gc.open_by_key(sheet_id)
            worksheet = sh.worksheet(sheet_name)
            data = worksheet.get_all_values()
            
        # --- 3. LÓGICA DE PARSING V4 ---
        header = [str(col).strip() for col in data[0]]
        
        try:
            col_idx_conta = header.index(col_conta)
            col_idx_alinea = header.index(col_alinea)
            col_idx_desc = header.index(col_desc)
            col_idx_val_concedido = header.index(col_val_concedido)
        except ValueError as e:
            col_nome = e.args[0].split("'")[1] if "'" in e.args[0] else "desconhecida"
            st.error(f"Erro de Parser: A coluna '{col_nome}' não foi encontrada no cabeçalho da '{sheet_name}'.")
            st.info(f"Verifique se o nome em [parser_config] no seu secrets.toml bate EXATAMENTE com o da planilha.")
            return pd.DataFrame()

        dados_processados = []
        projeto_atual = "N/A"
        projeto_encontrado = False 

        for row in data[1:]:
            if len(row) < max(col_idx_conta, col_idx_alinea, col_idx_desc, col_idx_val_concedido): 
                continue

            celula_A_str = str(row[col_idx_conta]).strip()
            celula_B_str = str(row[col_idx_alinea]).strip()
            celula_C_str = str(row[col_idx_desc]).strip()
            search_str = f"{celula_A_str} {celula_B_str} {celula_C_str}"

            if "PROJETO:" in search_str:
                _pre, _sep, nome_projeto = search_str.partition("PROJETO:")
                projeto_atual = nome_projeto.strip()
                projeto_encontrado = True 
                continue 

            if celula_A_str.startswith("TOTAL:") or celula_A_str.startswith("PROJETOS VERBAS"):
                continue 
            
            if not projeto_encontrado:
                continue
            
            celula_B_val = row[col_idx_alinea]
            celula_D_val = row[col_idx_val_concedido]

            is_B_valid = celula_B_val is not None and celula_B_val != "" and str(celula_B_val).lower() != "nan"
            is_D_valid = celula_D_val is not None and celula_D_val != "" and str(celula_D_val).lower() != "nan"
            
            if is_B_valid and is_D_valid: 
                linha_dados = {}
                for i, col_name in enumerate(header):
                    if i < len(row):
                        linha_dados[col_name] = row[i]
                    else:
                        linha_dados[col_name] = None
                
                linha_dados["Projeto"] = projeto_atual 
                dados_processados.append(linha_dados)
        
        if not dados_processados:
            st.warning(f"Nenhum dado de projeto foi extraído da aba '{sheet_name}'.")
            return pd.DataFrame()

        df = pd.DataFrame(dados_processados)

        # 4. Limpa os dados
        cols_monetarias = [
            'Valor Concedido', 'Valor Reservado', 'Valor Pago', 
            '$ Executado', 'Saldo Projeto', 'Saldo C.Cor',
            'Aditivo/Anulação', 'Reman. Rec', 'Reman. Env', 'Lib. Recursos'
        ]
        cols_parser_config = [ col_val_concedido ]
        for col_name in cols_parser_config:
             if col_name not in cols_monetarias:
                  cols_monetarias.append(col_name)

        for col in cols_monetarias:
            if col in df.columns:
                df[col] = limpar_e_converter_monetario(df[col])

        if 'Vigência' in df.columns:
            df['Vigência'] = pd.to_datetime(df['Vigência'], format='%d/%m/%Y', errors='coerce')
        
        df = df.dropna(subset=[col_alinea, 'Projeto'])
        return df
            
    except Exception as e:
        st.error(f"Erro Crítico de Conexão (Aba '{sheet_name}'): Não foi possível carregar os dados.")
        st.warning(f"Detalhe: {e}")
        return pd.DataFrame()

# =================================================================
# === INÍCIO DO FLUXO DO APLICATIVO ===
# =================================================================

# 1. CHECAGEM DE ACESSO
if not check_password():
    st.stop()

# 2. Usuário autenticado 
st.sidebar.markdown(f"**Usuário Logado:** `{st.session_state.get('authenticated_user', 'N/A')}`")

# 3. CARREGAMENTO DOS DADOS (AMBAS AS ABAS)
df = carregar_dados_sheets_seguro()
df_detalhado = carregar_dados_relatorio_seguro() 

# --- Início do Dashboard (Aba 1) ---
if not df.empty:
    
    st.sidebar.header("Filtros de Análise (Projetos)")

    # Filtros de Seleção Múltipla
    lista_dept = sorted(df['Departamento'].dropna().unique())
    dept_selecionados = st.sidebar.multiselect("Departamento:", options=lista_dept)
    lista_coord = sorted(df['Coordenador'].dropna().unique())
    coord_selecionados = st.sidebar.multiselect("Coordenador:", options=lista_coord)
    lista_agencia = sorted(df['Agência'].dropna().unique())
    agencia_selecionadas = st.sidebar.multiselect("Agência:", options=lista_agencia)
    lista_modalidade = sorted(df['Modalidade'].dropna().unique())
    modalidade_selecionadas = st.sidebar.multiselect("Modalidade:", options=lista_modalidade)
    
    # Filtro de Data
    data_min_series = df['Inic.Vigencia'].dropna().min()
    data_max_series = df['Fim Vigencia'].dropna().max()

    if data_min_series is not pd.NaT and data_max_series is not pd.NaT:
        data_min = data_min_series.date()
        data_max = data_max_series.date()
        data_selecionada = st.sidebar.date_input(
            "Filtrar Vigência (Início ou Fim):",
            value=(data_min, data_max), min_value=data_min, max_value=data_max
        )
    else:
        st.sidebar.warning("Datas de Vigência inválidas ou ausentes nos dados.")
        data_selecionada = (datetime.today().date(), datetime.today().date())

    # --- Lógica de Filtragem ---
    df_filtrado = df.copy()
    if dept_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Departamento'].isin(dept_selecionados)]
    if coord_selecionados:
        df_filtrado = df_filtrado[df_filtrado['Coordenador'].isin(coord_selecionados)]
    if agencia_selecionadas:
        df_filtrado = df_filtrado[df_filtrado['Agência'].isin(agencia_selecionadas)]
    if modalidade_selecionadas:
        df_filtrado = df_filtrado[df_filtrado['Modalidade'].isin(modalidade_selecionadas)]
    
    if len(data_selecionada) == 2:
        data_inicio, data_fim = data_selecionada
        df_filtrado = df_filtrado[
            ((df_filtrado['Inic.Vigencia'].dt.date >= data_inicio) & (df_filtrado['Inic.Vigencia'].dt.date <= data_fim)) |
            ((df_filtrado['Fim Vigencia'].dt.date >= data_inicio) & (df_filtrado['Fim Vigencia'].dt.date <= data_fim))
        ]

    # --- Layout do Dashboard ---
    st.title("Dashboard de Análise de Projetos (Sigeo)")

    # 1. KPIs (Indicadores Chave)
    st.header("Indicadores Financeiros Chave (Visão Geral)")
    
    total_liberacoes = df_filtrado['Liberações'].sum() if not df_filtrado.empty else 0
    total_reservado = df_filtrado['Valor Reservado'].sum() if not df_filtrado.empty else 0
    total_pago = df_filtrado['Valor Pago'].sum() if not df_filtrado.empty else 0
    num_projetos = df_filtrado['Nº Processo'].nunique() if not df_filtrado.empty else 0
    
    def format_brl(value):
        return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

    col_l1_1, col_l1_2 = st.columns(2)
    with col_l1_1:
        st.metric("Total de Liberações", format_brl(total_liberacoes))
    with col_l1_2:
        st.metric("Nº de Projetos", f"{num_projetos}")
        
    st.markdown("---") 

    col_l2_1, col_l2_2 = st.columns(2)
    with col_l2_1:
        st.metric("Total Pago", format_brl(total_pago))
    with col_l2_2:
        st.metric("Total Reservado", format_brl(total_reservado))

    st.markdown("---") 

    st.header("Análises Visuais (Visão Geral)")
    
    plotly_config = {'displayModeBar': False, 'responsive': True} 
    
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados (Visão Geral).")
    else:
        col_graf1, col_graf2 = st.columns(2)

        # Gráfico 1: Valor Pago por Departamento
        with col_graf1:
            st.subheader("Valor Pago por Departamento")
            df_graf_dept = df_filtrado.groupby('Departamento', dropna=False)['Valor Pago'].sum().reset_index()
            df_graf_dept = df_graf_dept.sort_values(by='Valor Pago', ascending=False)
            fig_dept = px.bar(
                df_graf_dept, x='Departamento', y='Valor Pago', title="Total Pago por Departamento",
                labels={'Valor Pago': 'Valor Total Pago (R$)'}, template="plotly_white"
            )
            fig_dept.update_yaxes(tickprefix="R$ ", separatethousands=True, tickformat=",")
            fig_dept.update_traces(marker_color=MEDICAL_BLUE, hovertemplate='Departamento: %{x}<br>Valor Pago: R$ %{y:,.2f}<extra></extra>')
            fig_dept.update_layout(plot_bgcolor='rgba(0,0,0,0)', font_family="Arial") 
            st.plotly_chart(fig_dept, config={**plotly_config, 'width': 'stretch'}) 

        # Gráfico 2: Projetos por Modalidade
        with col_graf2:
            st.subheader("Projetos por Modalidade")
            df_graf_mod = df_filtrado['Modalidade'].value_counts().reset_index(name='count')
            fig_mod = px.pie(
                df_graf_mod, names='Modalidade', values='count', title="Distribuição de Projetos por Modalidade",
                template="plotly_white", color_discrete_sequence=px.colors.sequential.Blues_r
            )
            fig_mod.update_layout(plot_bgcolor='rgba(0,0,0,0)', font_family="Arial")
            st.plotly_chart(fig_mod, config={**plotly_config, 'width': 'stretch'}) 

        # --- [NOVO GRÁFICO 1] Valores por Agência ---
        st.subheader("Valores por Agência (Gasto vs. Reservado)")
        df_agencia = df_filtrado.groupby('Agência')[['Valor Pago', 'Valor Reservado']].sum().reset_index()
        df_agencia_melted = df_agencia.melt(id_vars='Agência', var_name='Tipo', value_name='Valor')
        df_agencia_melted = df_agencia_melted.sort_values(by='Valor', ascending=False)
        
        fig_agencia = px.bar(
            df_agencia_melted, x='Agência', y='Valor', color='Tipo',
            title='Total Pago vs. Reservado por Agência',
            labels={'Valor': 'Valor Total (R$)', 'Agência': 'Agência', 'Tipo': 'Tipo de Valor'},
            template="plotly_white",
            barmode='group' # Cria barras agrupadas
        )
        fig_agencia.update_yaxes(tickprefix="R$ ", separatethousands=True, tickformat=",")
        fig_agencia.update_traces(hovertemplate='Agência: %{x}<br>Valor: R$ %{y:,.2f}<extra></extra>')
        fig_agencia.update_layout(plot_bgcolor='rgba(0,0,0,0)', font_family="Arial")
        st.plotly_chart(fig_agencia, config={**plotly_config, 'width': 'stretch'})
        # --- Fim do Novo Gráfico 1 ---

        # Gráfico 3: Cronograma de Projetos (Gantt)
        st.subheader("Cronograma de Projetos (Gantt)")
        df_gantt = df_filtrado.dropna(subset=['Inic.Vigencia', 'Fim Vigencia', 'Titulo Projeto']).sort_values(by='Inic.Vigencia')
        if not df_gantt.empty:
            df_gantt_top = df_gantt.head(20) 
            fig_timeline = px.timeline(
                df_gantt_top, x_start="Inic.Vigencia", x_end="Fim Vigencia",
                y="Titulo Projeto", color="Departamento", title="Linha do Tempo dos Projetos (Top 20 por Início)",
                labels={'Titulo Projeto': 'Projeto'}, template="plotly_white", color_discrete_sequence=px.colors.sequential.Teal
            )
            fig_timeline.update_yaxes(autorange="reversed")
            fig_timeline.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=600, font_family="Arial") 
            st.plotly_chart(fig_timeline, config={**plotly_config, 'width': 'stretch'}) 
        else:
            st.info("Não há dados de cronograma válidos para exibir o Gráfico de Gantt.")

        # 4. Tabela de Detalhamento
        st.markdown("---")
        st.header("Detalhamento dos Dados Filtrados (Visão Geral)")
        st.dataframe(
            df_filtrado,
            column_config={
                "Inic.Vigencia": st.column_config.DatetimeColumn("Inic.Vigencia", format="DD/MM/YYYY"),
                "Fim Vigencia": st.column_config.DatetimeColumn("Fim Vigencia", format="DD/MM/YYYY"),
                "Liberações": st.column_config.NumberColumn("Liberações", format="R$ %,.2f"),
                "Valor Reservado": st.column_config.NumberColumn("Valor Reservado", format="R$ %,.2f"),
                "Valor Pago": st.column_config.NumberColumn("Valor Pago", format="R$ %,.2f"),
            },
            width='stretch' 
        )

elif df.empty and df_detalhado.empty:
    st.error("Nenhum dado carregado de nenhuma das abas. O dashboard não pode ser exibido.")
    st.info("Por favor, verifique as mensagens de erro de conexão no topo da página.")


# --- [SEÇÃO] Exibição dos dados do Relatório (Aba "Balancete") ---
if not df_detalhado.empty:
    st.markdown("---")
    
    # Nomes das colunas do secrets.toml
    try:
        col_alinea_nome = st.secrets["parser_config"]["col_alinea"]
        col_val_concedido_nome = st.secrets["parser_config"]["col_valor_concedido"]
        col_descricao_nome = st.secrets["parser_config"]["col_descricao"]
    except KeyError:
        col_alinea_nome = "Alínea"
        col_val_concedido_nome = "Valor Concedido"
        col_descricao_nome = "Descrição"
        
    st.header(f"Detalhamento Financeiro por Projeto (Aba: {st.secrets['sheets_config']['sheet_name_report']})")
    
    # Filtro de Projeto para a tabela e gráficos
    projetos_lista = sorted(df_detalhado['Projeto'].unique())
    
    projeto_selecionado = st.multiselect(
        "Filtrar por Projeto (Detalhado):",
        options=projetos_lista,
        default=[] # [CORREÇÃO] Inicia com lista vazia (mostra tudo)
    )
    
    if projeto_selecionado:
        df_detalhado_filtrado = df_detalhado[df_detalhado['Projeto'].isin(projeto_selecionado)]
    else:
        df_detalhado_filtrado = df_detalhado # Mostra tudo por padrão

    # Exibe a tabela detalhada
    st.dataframe(
        df_detalhado_filtrado,
        column_config={
            "Vigência": st.column_config.DatetimeColumn("Vigência", format="DD/MM/YYYY"),
            col_val_concedido_nome: st.column_config.NumberColumn(col_val_concedido_nome, format="R$ %,.2f"),
            "Valor Reservado": st.column_config.NumberColumn("Valor Reservado", format="R$ %,.2f"),
            "Valor Pago": st.column_config.NumberColumn("Valor Pago", format="R$ %,.2f"),
            "$ Executado": st.column_config.NumberColumn("$ Executado", format="R$ %,.2f"),
            "Saldo Projeto": st.column_config.NumberColumn("Saldo Projeto", format="R$ %,.2f"),
            "Saldo C.Cor": st.column_config.NumberColumn("Saldo C.Cor", format="R$ %,.2f"),
        },
        width='stretch'
    )

    # --- [NOVOS GRÁFICOS 2 & 3] Análises Detalhadas do Balancete ---
    st.markdown("---")
    st.header("Análises Detalhadas do Balancete")
    st.info("Os gráficos abaixo são filtrados pela seleção de projetos feita acima.")

    if not df_detalhado_filtrado.empty:
        col_det1, col_det2 = st.columns(2)

        # Gráfico 2a: Gastos por Descrição
        with col_det1:
            st.subheader(f"Top 15 Gastos por {col_descricao_nome}")
            df_graf_desc = df_detalhado_filtrado.groupby(col_descricao_nome)['Valor Pago'].sum().reset_index()
            df_graf_desc = df_graf_desc.sort_values(by='Valor Pago', ascending=False).head(15)
            
            fig_desc = px.bar(
                df_graf_desc, x=col_descricao_nome, y='Valor Pago',
                title=f"Top 15 Gastos por {col_descricao_nome}",
                labels={'Valor Pago': 'Valor Total Pago (R$)'},
                template="plotly_white"
            )
            fig_desc.update_yaxes(tickprefix="R$ ", separatethousands=True, tickformat=",")
            fig_desc.update_traces(marker_color=MEDICAL_BLUE, hovertemplate='Descrição: %{x}<br>Valor Pago: R$ %{y:,.2f}<extra></extra>')
            fig_desc.update_layout(plot_bgcolor='rgba(0,0,0,0)', font_family="Arial")
            st.plotly_chart(fig_desc, config={**plotly_config, 'width': 'stretch'})
        
        # Gráfico 2b: Gastos por Alínea
        with col_det2:
            st.subheader(f"Top 15 Gastos por {col_alinea_nome}")
            df_graf_alinea = df_detalhado_filtrado.groupby(col_alinea_nome)['Valor Pago'].sum().reset_index()
            df_graf_alinea = df_graf_alinea.sort_values(by='Valor Pago', ascending=False).head(15)

            fig_alinea = px.bar(
                df_graf_alinea, x=col_alinea_nome, y='Valor Pago',
                title=f"Top 15 Gastos por {col_alinea_nome}",
                labels={'Valor Pago': 'Valor Total Pago (R$)'},
                template="plotly_white"
            )
            fig_alinea.update_yaxes(tickprefix="R$ ", separatethousands=True, tickformat=",")
            fig_alinea.update_traces(marker_color=COLOR_PALETTE['primary'], hovertemplate='Alínea: %{x}<br>Valor Pago: R$ %{y:,.2f}<extra></extra>')
            fig_alinea.update_layout(plot_bgcolor='rgba(0,0,0,0)', font_family="Arial")
            st.plotly_chart(fig_alinea, config={**plotly_config, 'width': 'stretch'})

    else:
        # Isso acontece se o usuário remover todos os projetos do filtro
        st.warning("Nenhum projeto selecionado para exibir os gráficos detalhados.")