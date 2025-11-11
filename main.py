import os
import pandas as pd
from github import Github
from dotenv import load_dotenv  # <<< 1. IMPORTAR

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")

if not TOKEN:
    raise EnvironmentError("GITHUB_TOKEN não foi definido. Crie o arquivo .env ou exporte a variável.")

g = Github(TOKEN)

print("Conectado à API do GitHub com sucesso.")

REPO_NOME = "facebook/react"
LABEL_BUG = "Type: Bug"

try:
    repo = g.get_repo(REPO_NOME)
    print(f"Repositório encontrado: {repo.full_name}")
except Exception as e:
    print(f"Erro ao encontrar o repositório: {e}")
    exit()

print(f"Buscando issues fechadas com a label: '{LABEL_BUG}'...")

issues_fechadas = repo.get_issues(state='all', labels=[LABEL_BUG])

lista_de_bugs = []

print(f"Processando as issues...")

for i, issue in enumerate(issues_fechadas):

    quem_fechou = None
    if issue.closed_by:
        quem_fechou = issue.closed_by.login

    lista_de_bugs.append({
        'id': issue.number,
        'titulo': issue.title,
        'criado_em': issue.created_at,
        'fechado_em': issue.closed_at,
        'quem_criou': issue.user.login,
        'quem_fechou': quem_fechou,
    })

    if (i + 1) % 50 == 0:
        print(f"Processado {i + 1} bugs...")

print(f"\nTotal de {len(lista_de_bugs)} bugs carregados.")

df_bugs = pd.DataFrame(lista_de_bugs)

df_bugs['criado_em'] = pd.to_datetime(df_bugs['criado_em'])
df_bugs['fechado_em'] = pd.to_datetime(df_bugs['fechado_em'])

print("\nDataFrame criado com sucesso!")
print(df_bugs.head())

df_bugs['tempo_correcao_dias'] = (df_bugs['fechado_em'] - df_bugs['criado_em']).dt.total_seconds() / (60*60*24)

print("\n--- Exemplo de Métrica (Tempo médio de correção) ---")
print(f"{df_bugs['tempo_correcao_dias'].mean():.2f} dias")

df_bugs.to_csv("react_bugs.csv", index=False)
print("\nDados salvos em 'react_bugs.csv'")