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
st.markdown("<h1 style='text-align: center;'>🐞 Monitoramento de Bugs 🐞</h1>", unsafe_allow_html=True)

st.markdown(
        "<h4 style='text-align: center;'>Repositório <a href='https://github.com/facebook/react' target='_blank'>https://github.com/facebook/react</a></h4>",
        unsafe_allow_html=True
    )

st.markdown("---")

# KPIs (Métricas rápidas)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"<div style='text-align: center; font-size: 23px;'>{len(df_filtered)}<br>Total de bugs no período</div>", unsafe_allow_html=True)

with col2:
    avg_days = f"{df_filtered['days_to_fix'].mean():.1f} dias"
    st.markdown(f"<div style='text-align: center; font-size: 23px;'>{avg_days}<br>Média de dias para corrigir</div>", unsafe_allow_html=True)

with col3:
    st.markdown(f"<div style='text-align: center; font-size: 23px;'>{df_filtered['closed_by'].nunique()}<br>Desenvolvedores ativos</div>", unsafe_allow_html=True)


st.markdown("---")

# --- GRÁFICOS (Layout em Grid) ---
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.markdown("<h3 style='text-align: center;'>Bugs ao longo do tempo</h3>", unsafe_allow_html=True)
    
    # Aggregate weekly to avoid clutter
    bugs_weekly = df_filtered.set_index('created_at').resample('W').size().reset_index(name='count')

    # Optional: add rolling average (e.g., 2-week)
    bugs_weekly['rolling_avg'] = bugs_weekly['count'].rolling(2).mean()

    fig_line = px.line(
        bugs_weekly,
        x='created_at',
        y='count',
        labels={'created_at': 'Data', 'count': 'Qtd Bugs'},
        line_shape='spline'  # <-- smooth curves
    )

    st.plotly_chart(fig_line, use_container_width=True)

with row1_col2:
    st.markdown("<h3 style='text-align: center;'>Tempo para correção</h3>", unsafe_allow_html=True)
    
    # Histograma mostra a frequência dos tempos de correção
    fig_hist = px.histogram(df_filtered, x="days_to_fix", nbins=20,
                            labels={'days_to_fix': 'Dias'},
                            color_discrete_sequence=['#f1c40f'])
    st.plotly_chart(fig_hist, use_container_width=True)

row2_col1, row2_col2 = st.columns(2)

TOP_N = 10
with row2_col1:
    st.markdown(
        "<h3 style='text-align: center;'>🏆 TOP Desenvolvedores ativos em fechar bugs</h3>",
        unsafe_allow_html=True
    )

    # Count developers and keep top N
    dev_counts = df_filtered['closed_by'].value_counts()
    top_devs = dev_counts.head(TOP_N).reset_index()
    top_devs.columns = ['Desenvolvedor', 'Bugs Fechados']

    # Remove the index by converting to list of dicts
    table_data = top_devs.to_dict('records')

    # Create HTML table manually for styling
    table_html = "<table style='width:100%; text-align:center; font-size:18px; font-family: Arial; border-collapse: collapse;'>"
    table_html += "<tr style='background-color:#e0f0ff; font-weight:bold;'><th>Desenvolvedor</th><th>Bugs Fechados</th></tr>"

    for i, row in enumerate(table_data):
        bg_color = '#d0e4ff' if i % 2 == 0 else '#f0f8ff'  # alternate row colors
        table_html += f"<tr style='background-color:{bg_color}; text-align:center;'>"
        table_html += f"<td>{row['Desenvolvedor']}</td>"
        table_html += f"<td>{row['Bugs Fechados']}</td>"
        table_html += "</tr>"

    table_html += "</table>"

    st.markdown(table_html, unsafe_allow_html=True)

with row2_col2:
    st.markdown("<h3 style='text-align: center;'>Arquivos mais modificados (últimos 5000 commits)</h3>", unsafe_allow_html=True)

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