import pandas as pd
import os

def analisar_estrutura_arquivo(filepath):
    """
    Lê as primeiras 100 linhas de um arquivo (Excel ou CSV) e exibe 
    os nomes das colunas e seus tipos de dados inferidos.
    """
    if not os.path.exists(filepath):
        print(f"X ERRO: Arquivo não encontrado em:\n{filepath}\n")
        return

    try:
        filename = os.path.basename(filepath)
        print(f"--- 🔍 Analisando Arquivo: {filename} ---")

        if filepath.endswith('.csv'):
            # Tenta autodetectar o separador (comum ser ',' ou ';')
            # Lê apenas 100 linhas para ser rápido
            df = pd.read_csv(filepath, sep=None, engine='python', nrows=100)
        
        elif filepath.endswith('.xlsx') or filepath.endswith('.xls'):
            # Lê apenas a primeira aba (sheet_name=0) e 100 linhas
            df = pd.read_excel(filepath, sheet_name=0, nrows=100)
            print(f"(Lendo a primeira aba do Excel...)\n")
        
        else:
            print(f"X ERRO: Formato de arquivo não suportado '{filename}'.")
            print("Por favor, use arquivos .csv, .xlsx ou .xls.\n")
            return

        # A informação principal que precisamos:
        print("Estrutura das Colunas e Tipos (d-types):")
        print(df.dtypes)
        print("-" * 40 + "\n")

    except Exception as e:
        print(f"X ERRO Inesperado ao processar o arquivo {filename}:")
        print(f"{e}\n")
        print("Verifique se o arquivo não está corrompido ou se o formato é válido.\n")

# --- Início do Script ---

print("=" * 50)
print("Analisador de Estrutura de Relatórios (Sigeo x Balancete)")
print("=" * 50)
print("Por favor, cole o CAMINHO COMPLETO de cada arquivo abaixo.")
print(r"Exemplo Windows: C:\Usuarios\SeuNome\Downloads\relatorio_sigeo.xlsx")
print(r"Exemplo Mac/Linux: /home/seu_nome/documentos/relatorio_sigeo.csv")
print("\n")

# 1. Pedir o caminho do Relatório Consolidado (Sigeo)
path_sigeo = "Relatório Sigeo .xlsx"

# 2. Pedir o caminho do Balancete (Detalhado)
path_balancete = "Balancete prestação de contas - todos os projetos_Sigeo.xlsx"

print("\n" + "=" * 50 + "\n")

# Analisar os arquivos
if path_sigeo:
    analisar_estrutura_arquivo(path_sigeo)
else:
    print("Nenhum caminho fornecido para o Relatório Sigeo.\n")

if path_balancete:
    analisar_estrutura_arquivo(path_balancete)
else:
    print("Nenhum caminho fornecido para o Balancete.\n")

print("Análise concluída. Copie e cole os resultados acima para mim.")