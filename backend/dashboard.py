import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy.orm import Session
from models import engine, Issue, FileModification
from datetime import datetime, timedelta

# Configuração da Página
st.set_page_config(page_title="Monitoramento de Bugs", layout="wide")


# --- FUNÇÃO DE CARGA DE DADOS ---
# Usamos o cache do Streamlit para não bater no banco a cada clique
def load_data():
    with engine.connect() as conn:
        df_issues = pd.read_sql(
            "SELECT * FROM issues WHERE state != 'pull_request'", conn
        )
        df_files = pd.read_sql(
            "SELECT * FROM file_modifications ORDER BY changes DESC LIMIT 20", conn
        )

    # Garantir que as colunas de data sejam datetime
    df_issues['created_at'] = pd.to_datetime(df_issues['created_at'])
    df_issues['closed_at'] = pd.to_datetime(df_issues['closed_at'])

    # Calcular tempo de correção (dias)
    df_issues['days_to_fix'] = (df_issues['closed_at'] - df_issues['created_at']).dt.days

    return df_issues, df_files


# --- CARREGAR DADOS ---
try:
    df_issues, df_files = load_data()
except Exception as e:
    st.error(f"Erro ao conectar no banco de dados: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros")

# Datas de referência
today = datetime.now().date()
min_date_db = df_issues['created_at'].min().date() if not df_issues.empty else today

# Lógica dos 30 dias atrás
date_30_days_ago = today - timedelta(days=30)

# Proteção: Se o banco tiver dados de apenas 10 dias atrás, usamos a data do banco
# para não gerar erro de "value < min_value"
default_start_value = max(date_30_days_ago, min_date_db)

# Inputs de Data
# value = Valor que vem marcado por padrão (30 dias atrás)
# min_value = Até onde o usuário PODE voltar se quiser (Data mais antiga do banco)
start_date = st.sidebar.date_input(
    "Data Início",
    value=default_start_value,
    min_value=min_date_db,
    max_value=today
)

end_date = st.sidebar.date_input(
    "Data Fim",
    value=today,
    max_value=today
)

# --- APLICAR FILTROS ---
if not df_issues.empty:
    mask = (df_issues['created_at'].dt.date >= start_date) & (df_issues['created_at'].dt.date <= end_date)
    df_filtered = df_issues.loc[mask]
else:
    df_filtered = df_issues # Vazio

# --- DASHBOARD ---
st.title("🐞 Dashboard de Monitoramento de Bugs")
st.subheader("https://github.com/facebook/react")
st.markdown("---")

# KPIs (Métricas rápidas)
col1, col2, col3 = st.columns(3)
col1.metric("Total de Bugs no Período", len(df_filtered))
col2.metric("Média de Dias para Corrigir", f"{df_filtered['days_to_fix'].mean():.1f} dias")
col3.metric("Desenvolvedores Ativos", df_filtered['closed_by'].nunique())

st.markdown("---")

# --- GRÁFICOS (Layout em Grid) ---
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.subheader("Bugs ao Longo do Tempo")
    # Agrupar por dia
    bugs_over_time = df_filtered.set_index('created_at').resample('D').size().reset_index(name='count')

    fig_line = px.line(bugs_over_time, x='created_at', y='count',
                       labels={'created_at': 'Data', 'count': 'Qtd Bugs'},
                       markers=True)
    st.plotly_chart(fig_line, use_container_width=True)

with row1_col2:
    st.subheader("Tempo de Correção (Distribuição)")
    # Histograma mostra a frequência dos tempos de correção
    fig_hist = px.histogram(df_filtered, x="days_to_fix", nbins=20,
                            labels={'days_to_fix': 'Dias'},
                            color_discrete_sequence=['#f1c40f'])
    st.plotly_chart(fig_hist, use_container_width=True)

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.subheader("Top Desenvolvedores")
    top_devs = df_filtered['closed_by'].value_counts().head(10).reset_index()
    top_devs.columns = ['developer', 'count']

    fig_bar_dev = px.bar(top_devs, x='developer', y='count',
                         color='count',  # Gradiente de cor
                         labels={'developer': 'Dev', 'count': 'Bugs Fechados'})
    st.plotly_chart(fig_bar_dev, use_container_width=True)

with row2_col2:
    st.subheader("Arquivos Mais Modificados (Histórico Total)")
    # Nota: FileModification geralmente é histórico total, não filtrado por data
    fig_bar_files = px.bar(df_files.head(10), x='changes', y='file_name',
                           orientation='h',  # Barra horizontal
                           labels={'changes': 'Modificações', 'file_name': 'Arquivo'},
                           color_discrete_sequence=['#2ecc71'])
    # Inverte eixo Y para o mais modificado ficar no topo
    fig_bar_files.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_bar_files, use_container_width=True)

# Botão para recarregar dados manualmente
if st.sidebar.button('Atualizar Dados'):
    st.cache_data.clear()
    st.rerun()