import pandas as pd

def limpar_e_converter_monetario(series):
    """Limpa e converte colunas monetárias (string 'R$ 1.000,00') para número."""
    if series.dtype == 'object':
        series = series.astype(str)
        series = series.str.replace(r'[R$\s]+', '', regex=True) # Remove R$ e espaços
        series = series.str.replace('.', '', regex=False)      # Remove . de milhar
        series = series.str.replace(',', '.', regex=False)      # Troca , de decimal por .
    return pd.to_numeric(series, errors='coerce')

def processar_relatorio(file_path, sheet_name):
    """
    Processa um arquivo Excel com formato de relatório, extraindo e "achatando"
    os dados de projeto e suas linhas de item.
    """
    try:
        # ATUALIZADO: Removemos o 'dtype=str' para o pandas identificar
        # células vazias como NaN (Not a Number), e não como a string "nan".
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
        df_raw.columns = [str(col).strip() for col in df_raw.columns]

    except FileNotFoundError:
        print(f"Erro: O arquivo '{file_path}' não foi encontrado.")
        print("Verifique se o script está na mesma pasta do arquivo Excel.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Erro ao ler o arquivo Excel: {e}")
        print(f"Verifique se o nome da aba ('{sheet_name}') está correto.")
        return pd.DataFrame()

    # Colunas-chave que usaremos para checagem
    COL_PROJETO_CHECK = "Conta Corrente" 
    COL_ALINEA = "Alínea"
    COL_DESCRICAO = "Descrição"
    COL_VALOR_CONCEDIDO = "Valor Concedido"
    
    dados_processados = []
    projeto_atual = "N/A"
    
    # --- [NOVA LÓGICA V3] ---
    # "Trava" para ignorar dados antes do primeiro projeto
    projeto_encontrado = False 

    print("Iniciando processamento linha a linha (Lógica Corrigida V3)...")

    # Itera sobre cada linha do DataFrame lido
    for index, row in df_raw.iterrows():
        
        # Converte as colunas de busca para string, tratando NaNs corretamente
        celula_A_str = str(row.get(COL_PROJETO_CHECK, "")).strip()
        celula_B_str = str(row.get(COL_ALINEA, "")).strip()
        celula_C_str = str(row.get(COL_DESCRICAO, "")).strip()
        
        # Junta as primeiras colunas em uma única string para busca
        search_str = f"{celula_A_str} {celula_B_str} {celula_C_str}"

        # CASO 1: É uma linha de "PROJETO"?
        if "PROJETO:" in search_str:
            _pre, _sep, nome_projeto = search_str.partition("PROJETO:")
            projeto_atual = nome_projeto.strip()
            projeto_encontrado = True # Destrava o salvamento de dados
            # print(f"--- Encontrado Projeto: {projeto_atual} ---") # (Descomente para debug)
            continue 

        # CASO 2: É uma linha de "TOTAL" ou um título de seção?
        if celula_A_str.startswith("TOTAL:") or celula_A_str.startswith("PROJETOS VERBAS"):
            continue 

        # --- [NOVO FILTRO V3] ---
        # Só processa se a "trava" estiver destravada
        if not projeto_encontrado:
            continue
            
        # CASO 3: É uma linha de dados válida?
        # Critério: 'Alínea' (célula B) não pode ser vazia/NaN
        # E 'Valor Concedido' (célula D) não pode ser vazio/NaN
        # Usamos pd.notna() que funciona com NaNs reais
        celula_B_val = row.get(COL_ALINEA)
        celula_D_val = row.get(COL_VALOR_CONCEDIDO)
        
        if pd.notna(celula_B_val) and pd.notna(celula_D_val): 
            
            # Tenta extrair todas as colunas do cabeçalho original
            linha_dados = {
                "Projeto": projeto_atual,
                "Conta Corrente": celula_A_str,
                "Alínea": str(celula_B_val).strip(), # celula_B_str pode ser "nan"
                "Descrição": celula_C_str,
                "Valor Concedido": row.get("Valor Concedido"),
                "Valor Reservado": row.get("Valor Reservado"),
                "Valor Pago": row.get("Valor Pago"),
                "$ Executado": row.get("$ Executado"),
                "Aditivo/Anulação": row.get("Aditivo/Anulação"),
                "Reman. Rec": row.get("Reman. Rec"),
                "Reman. Env": row.get("Reman. Env"),
                "Lib. Recursos": row.get("Lib. Recursos"),
                "Saldo Projeto": row.get("Saldo Projeto"),
                "Saldo C.Cor": row.get("Saldo C.Cor"),
                "Vigência": row.get("Vigência")
            }
            dados_processados.append(linha_dados)
    
    print(f"Processamento concluído. {len(dados_processados)} linhas de dados extraídas.")

    if not dados_processados:
        print("Aviso: Nenhum dado de projeto foi extraído. Verifique os critérios de filtro.")
        return pd.DataFrame()

    # --- Criação e Limpeza do DataFrame Final ---
    df_final = pd.DataFrame(dados_processados)

    # Aplica a limpeza final (monetária e datas)
    cols_monetarias = [
        'Valor Concedido', 'Valor Reservado', 'Valor Pago', 
        '$ Executado', 'Saldo Projeto', 'Saldo C.Cor'
    ]
    for col in cols_monetarias:
        if col in df_final.columns:
            df_final[col] = limpar_e_converter_monetario(df_final[col])

    if 'Vigência' in df_final.columns:
        df_final['Vigência'] = pd.to_datetime(df_final['Vigência'], errors='coerce')

    return df_final

# --- PONTO DE PARTIDA DO SCRIPT ---
if __name__ == "__main__":
    
    # --- CONFIGURAÇÕES ---
    file_name = "Balancete prestação de contas - todos os projetos_Sigeo.xlsx"
    
    # ATUALIZADO: Conforme seu pedido
    sheet_name = "Planilha1" 
    
    # ---------------------

    print(f"Processando arquivo: {file_name} (Aba: {sheet_name})...")
    
    df_processado = processar_relatorio(file_name, sheet_name)

    if not df_processado.empty:
        print("\n--- Processamento concluído com sucesso ---")
        
        print("\n--- Cabeçalho (head) do DataFrame resultante ---")
        print(df_processado.head())
        
        print("\n--- Informações (info) do DataFrame resultante ---")
        df_processado.info()
        
        # Salva em CSV para fácil validação
        output_csv = "dados_processados_validacao.csv"
        try:
            df_processado.to_csv(output_csv, index=False, sep=';', decimal=',', encoding='utf-8-sig')
            print(f"\nArquivo de validação salvo com sucesso em: '{output_csv}'")
        except Exception as e:
            print(f"\nErro ao salvar o CSV de validação: {e}")
    else:
        print("\nO processamento não gerou dados. Verifique o nome da aba e o formato do arquivo.")