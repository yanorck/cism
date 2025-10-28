import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime
import gspread 
from streamlit_cookies_manager import EncryptedCookieManager # IMPORT NECESSÁRIO PARA PERSISTÊNCIA

# --- CONFIGURAÇÃO DE COOKIES PARA PERSISTÊNCIA DE LOGIN (NOVO) ---
try:
    # Tenta usar a chave secreta definida no secrets.toml
    cookies = EncryptedCookieManager(
        prefix="cism_dash_auth_",
        password=st.secrets["cookies"]["secret_key"] 
    )
except KeyError:
    # Mensagem de erro se a chave não for encontrada
    st.error("Erro de Configuração: A chave secreta do cookie (secrets.toml [cookies]) não foi definida.")
    st.stop()
except Exception as e:
    st.error(f"Erro ao inicializar Cookie Manager: {e}")
    st.stop()

# Aguarda o carregamento inicial dos cookies pelo componente (necessário pelo streamlit-cookies-manager)
if not cookies.ready():
    st.stop()


# --- VARIÁVEIS DE ESTADO E FUNÇÕES DE LOGIN/LOGOUT ---

def logout():
    """Função para deslogar, limpando a sessão e os cookies."""
    st.session_state["password_correct"] = False
    if "authenticated_user" in st.session_state:
        del st.session_state["authenticated_user"]
    
    # Limpa o estado de login nos cookies
    cookies['logged_in'] = 'False'
    cookies['user'] = '' # Limpa o usuário
    cookies.save()
    
    # Limpa o cache de dados para forçar o recarregamento (se necessário)
    st.cache_data.clear()
    
    st.rerun() 


def check_password():
    """
    Controla o fluxo de login, persistindo o estado via cookies.
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
            
            # NOVO: Salva o estado de login nos cookies
            cookies['logged_in'] = 'True'
            cookies['user'] = st.session_state["username"]
            cookies.save()
            
        else:
            st.session_state["password_correct"] = False

    # 2. VERIFICAÇÃO DE ESTADO
    
    # Verifica o cookie E a sessão
    is_logged_in_via_cookie = cookies.get('logged_in') == 'True'
    is_logged_in_via_session = st.session_state.get("password_correct", False)
    
    if is_logged_in_via_cookie or is_logged_in_via_session:
        # Se logado pelo Cookie, garante que a sessão também esteja correta (após F5)
        if is_logged_in_via_cookie and not is_logged_in_via_session:
             st.session_state["authenticated_user"] = cookies.get('user')
             st.session_state["password_correct"] = True 
             
        # Adiciona o botão de Logout na sidebar
        with st.sidebar:
            st.button("Sair (Logout)", on_click=logout)
        
        return True # Permite a execução do restante do código

    # 3. EXIBE O FORMULÁRIO DE LOGIN (Apenas se não estiver logado)
    with st.container():
        st.title("Acesso Restrito ao Dashboard CISM")
        st.info("Por favor, insira suas credenciais para continuar.")
        
        with st.form("login_form"):
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            st.form_submit_button("Entrar", on_click=password_entered)
        
        # Feedback de erro de login
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Usuário ou Senha incorretos.")
        
    return False

# --- Configuração da Página (Deve vir antes de qualquer saída do Streamlit) ---
st.set_page_config(layout="wide", page_title="Dashboard de Projetos Sigeo")

# --- Paleta de Cores e CSS ---
COLOR_PALETTE = {
    "primary": "#0D6E6E", 
    ""
    "secondary": "#007A9E", 
    "background": "#F0F2F6",
    "sidebar_bg": "#FFFFFF",
    "text_dark": "#31333F",
    "text_light": "#555555",
    "kpi_border": "#E0E0E0"
}
MEDICAL_BLUE = COLOR_PALETTE["secondary"]

st.markdown(f"""
<style>
    /* Estilos para o Streamlit */
    [data-testid="stAppViewContainer"] > .main {{ background-color: {COLOR_PALETTE['background']}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_PALETTE['sidebar_bg']}; }}
    h1, h2, h3 {{ color: {COLOR_PALETTE['primary']}; }}
    /* Estilo dos KPIs (Métricas) */
    [data-testid="stMetric"] {{
        background-color: #FFFFFF; border: 1px solid {COLOR_PALETTE['kpi_border']}; 
        border-radius: 10px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    [data-testid="stMetric"] div[data-testid="stMetricValue"] {{ color: {COLOR_PALETTE['text_dark']}; font-size: 2.2rem; }}
    /* Estilo dos Gráficos */
    [data-testid="stPlotlyChart"] {{
        background-color: #FFFFFF; border-radius: 10px; padding: 10px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
</style>
""", unsafe_allow_html=True)


# --- Funções de Ajuda ---
def limpar_nome_coluna(col_name):
    if isinstance(col_name, str):
        return col_name.strip()
    return col_name

# --- Carregamento SEGURO dos Dados do Google Sheets ---
@st.cache_data(ttl=600) # Dados cacheados por 10 minutos
def carregar_dados_sheets_seguro():
    """Conecta-se ao Google Sheets de forma segura, limpa e converte os dados."""
    
    def limpar_e_converter_monetario(series):
        if series.dtype == 'object':
            series = series.astype(str)
            # 1. Remove R$ e espaços
            series = series.str.replace(r'[R$\s]+', '', regex=True)
            # 2. Remove o ponto de milhar (padrão brasileiro)
            series = series.str.replace('.', '', regex=False)
            # 3. Substitui a vírgula decimal por ponto
            series = series.str.replace(',', '.', regex=False)
        return pd.to_numeric(series, errors='coerce') # Converte para número (float)
    
    try:
        # Puxa todas as configurações do st.secrets
        sheet_id = st.secrets["sheets_config"]["sheet_id"]
        sheet_name = st.secrets["sheets_config"]["sheet_name"]
        creds = st.secrets["gcp_service_account"]
        
        # 1. Autenticação com a Service Account e Leitura
        with st.spinner('⌛ Conectando ao Google Sheets e carregando dados...'):
            gc = gspread.service_account_from_dict(creds)
            sh = gc.open_by_key(sheet_id)
            worksheet = sh.worksheet(sheet_name)
            
            data = worksheet.get_all_values()
            
            # 2. Criação e Limpeza do DataFrame
            df = pd.DataFrame(data[1:], columns=data[0]) 
            df.columns = [limpar_nome_coluna(col) for col in df.columns]

            # Conversão de Tipos (financeiro)
            df['Liberações'] = limpar_e_converter_monetario(df['Liberações'])
            df['Valor Reservado'] = limpar_e_converter_monetario(df['Valor Reservado'])
            df['Valor Pago'] = limpar_e_converter_monetario(df['Valor Pago'])

            # Conversão de Datas (formato %d/%m/%Y)
            if 'Inic.Vigencia' in df.columns:
                df['Inic.Vigencia'] = pd.to_datetime(df['Inic.Vigencia'], format='%d/%m/%Y', errors='coerce')
            if 'Fim Vigencia' in df.columns:
                df['Fim Vigencia'] = pd.to_datetime(df['Fim Vigencia'], format='%d/%m/%Y', errors='coerce')
                
            df = df.dropna(subset=['Inic.Vigencia', 'Fim Vigencia'])
            return df
        
    except KeyError as e:
        st.error(f"Erro de Configuração: Falha ao acessar o segredo: {e}. Verifique o seu secrets.toml.")
        return pd.DataFrame()
    except Exception as e:
        st.error("🚨 Erro Crítico de Conexão: Não foi possível carregar os dados do Google Sheet.")
        st.warning(f"Detalhe: {e}")
        st.info("Verifique permissões do 'client_email' na planilha e se o `secrets.toml` está correto.")
        return pd.DataFrame()

# =================================================================
# === INÍCIO DO FLUXO DO APLICATIVO ===
# =================================================================

# 1. CHECAGEM DE ACESSO (O script para aqui se o login falhar)
if not check_password():
    st.stop()

# 2. Usuário autenticado 
st.sidebar.markdown(f"**Usuário Logado:** `{st.session_state.get('authenticated_user', 'N/A')}`")

# 3. CARREGAMENTO DOS DADOS
df = carregar_dados_sheets_seguro()

# --- Início do Dashboard ---
if not df.empty:
    
    st.sidebar.header("Filtros de Análise")

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
        # Filtra projetos cuja vigência (Início ou Fim) esteja no intervalo selecionado
        df_filtrado = df_filtrado[
            ((df_filtrado['Inic.Vigencia'].dt.date >= data_inicio) & (df_filtrado['Inic.Vigencia'].dt.date <= data_fim)) |
            ((df_filtrado['Fim Vigencia'].dt.date >= data_inicio) & (df_filtrado['Fim Vigencia'].dt.date <= data_fim))
        ]

    # --- Layout do Dashboard ---
    st.title("Dashboard de Análise de Projetos (Sigeo)")

    # 1. KPIs (Indicadores Chave)
    st.header("Indicadores Financeiros Chave")
    
    total_liberacoes = df_filtrado['Liberações'].sum() if not df_filtrado.empty else 0
    total_reservado = df_filtrado['Valor Reservado'].sum() if not df_filtrado.empty else 0
    total_pago = df_filtrado['Valor Pago'].sum() if not df_filtrado.empty else 0
    num_projetos = df_filtrado['Nº Processo'].nunique() if not df_filtrado.empty else 0
    
    # Função para formatar o BRL com vírgula como decimal e ponto como milhar
    def format_brl(value):
        return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Liberações", format_brl(total_liberacoes))
    col2.metric("Total Pago", format_brl(total_pago))
    col3.metric("Total Reservado", format_brl(total_reservado))
    col4.metric("Nº de Projetos", f"{num_projetos}")

    st.markdown("---")
    st.header("Análises Visuais")
    
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
    else:
        col_graf1, col_graf2 = st.columns(2)

        # Gráfico 1: Valor Pago por Departamento
        with col_graf1:
            st.subheader("Valor Pago por Departamento")
            df_graf_dept = df_filtrado.groupby('Departamento', dropna=False)['Valor Pago'].sum().reset_index()
            df_graf_dept = df_graf_dept.sort_values(by='Valor Pago', ascending=False)
            
            fig_dept = px.bar(
                df_graf_dept, x='Departamento', y='Valor Pago', title="Total Pago por Departamento",
                labels={'Valor Pago': 'Valor Total Pago (R$)'}, text_auto='.2s', template="plotly_white"
            )
            fig_dept.update_traces(marker_color=MEDICAL_BLUE)
            fig_dept.update_layout(plot_bgcolor='rgba(0,0,0,0)') 
            st.plotly_chart(fig_dept, use_container_width=True)

        # Gráfico 2: Projetos por Modalidade
        with col_graf2:
            st.subheader("Projetos por Modalidade")
            df_graf_mod = df_filtrado['Modalidade'].value_counts().reset_index(name='count')
            
            fig_mod = px.pie(
                df_graf_mod, names='Modalidade', values='count', title="Distribuição de Projetos por Modalidade",
                template="plotly_white", color_discrete_sequence=px.colors.sequential.Blues_r
            )
            fig_mod.update_layout(plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_mod, use_container_width=True)

        # Gráfico 3: Cronograma de Projetos (Gantt)
        st.subheader("Cronograma de Projetos (Gantt)")
        
        df_gantt = df_filtrado.dropna(subset=['Inic.Vigencia', 'Fim Vigencia', 'Titulo Projeto']).sort_values(by='Inic.Vigencia')
        if not df_gantt.empty:
            # Limita a 20 projetos para melhor visualização (opcional)
            df_gantt_top = df_gantt.head(20) 

            fig_timeline = px.timeline(
                df_gantt_top, x_start="Inic.Vigencia", x_end="Fim Vigencia",
                y="Titulo Projeto", color="Departamento", title="Linha do Tempo dos Projetos (Top 20)",
                labels={'Titulo Projeto': 'Projeto'}, template="plotly_white", color_discrete_sequence=px.colors.sequential.Teal
            )
            fig_timeline.update_yaxes(autorange="reversed")
            fig_timeline.update_layout(plot_bgcolor='rgba(0,0,0,0)', height=600)
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("Não há dados de cronograma válidos para exibir o Gráfico de Gantt.")

        # 4. Tabela de Detalhamento
        st.markdown("---")
        st.header("Detalhamento dos Dados Filtrados")
        # Ajusta a exibição da tabela com formatação de data e float
        st.dataframe(
            df_filtrado,
            column_config={
                "Inic.Vigencia": st.column_config.DatetimeColumn("Inic.Vigencia", format="DD/MM/YYYY"),
                "Fim Vigencia": st.column_config.DatetimeColumn("Fim Vigencia", format="DD/MM/YYYY"),
                "Liberações": st.column_config.NumberColumn("Liberações", format="R$ %,.2f"),
                "Valor Reservado": st.column_config.NumberColumn("Valor Reservado", format="R$ %,.2f"),
                "Valor Pago": st.column_config.NumberColumn("Valor Pago", format="R$ %,.2f"),
            }
        )

else:
    # Mensagem de erro de dados (só ocorre se o check_password for True)
    st.error("Nenhum dado carregado. O dashboard não pode ser exibido.")
    st.info("Por favor, verifique as mensagens de erro de conexão no topo da página e o console para mais detalhes.")