import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from config import EXCEL_URL

st.set_page_config(page_title="Painel de Produção & Renovações", layout="wide")
st.markdown("""
<style>
/* Styles for pulsing indicators */
.pulse-red { height: 12px; width: 12px; background: #ff3b3b; border-radius: 50%; display: inline-block; margin-right:8px; animation: pulse 1s infinite; }
.pulse-green { height: 12px; width: 12px; background: #16a34a; border-radius: 50%; display: inline-block; margin-right:8px; }
@keyframes pulse { 0% { transform: scale(0.95); opacity:0.75 } 50% { transform: scale(1.25); opacity:1 } 100% { transform: scale(0.95); opacity:0.75 } }
.table-wrap { overflow:auto }
</style>
""", unsafe_allow_html=True)

st.title("📊 Painel de Produção & Renovações – Corretora de Seguros")
st.markdown("---")

@st.cache_data(ttl=60)
def load_excel(url):
    # read as bytes then use pandas ExcelFile to support Google export links
    try:
        df_xls = pd.ExcelFile(url)
        return df_xls
    except Exception as e:
        st.error(f"Erro ao carregar a planilha: {e}")
        return None

xls = load_excel(EXCEL_URL)
if xls is None:
    st.stop()

abas = xls.sheet_names
aba = st.selectbox("Escolha a ABA da planilha:", abas)

try:
    df = pd.read_excel(xls, sheet_name=aba)
except Exception as e:
    st.error(f"Erro ao ler a aba selecionada: {e}")
    st.stop()

# Normalize column names (strip)
df.columns = [str(c).strip() for c in df.columns]

# Ensure expected columns exist (best-effort)
expected_cols = ["Dia","Segurado","Apólice","Prêmio Líquido","Fator %","Status","Cia","Item","CPF/CNPJ","Franquia","Colaborador"]

st.sidebar.header("Filtros")
# Filters
colaborador_list = ["Todos"] + sorted(df.get('Colaborador', pd.Series([])).dropna().astype(str).unique().tolist())
colaborador = st.sidebar.selectbox("Colaborador", colaborador_list)
status_filter = st.sidebar.selectbox("Status", ["Todos","pendente","renovado"]) 
busca = st.sidebar.text_input("Buscar por CPF / Apólice / Segurado")

# Apply filters
df_filtered = df.copy()
if colaborador != "Todos":
    if 'Colaborador' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Colaborador'] == colaborador]

if status_filter and status_filter != "Todos":
    if 'Status' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Status'].astype(str).str.lower() == status_filter.lower()]

if busca and busca.strip() != "":
    q = busca.strip().lower()
    mask = pd.Series(False, index=df_filtered.index)
    for c in ['CPF/CNPJ','Apólice','Segurado']:
        if c in df_filtered.columns:
            mask = mask | df_filtered[c].astype(str).str.lower().str.contains(q)
    df_filtered = df_filtered[mask]

# Metrics
st.subheader("Resumo")
col1, col2, col3 = st.columns(3)

total_premio = 0
if 'Prêmio Líquido' in df_filtered.columns:
    # try to coerce to numeric
    total_premio = pd.to_numeric(df_filtered['Prêmio Líquido'].astype(str).str.replace('[^0-9,.-]','', regex=True).str.replace(',', '.'), errors='coerce').sum()

total_pendente = 0
total_renovado = 0
if 'Status' in df_filtered.columns:
    s = df_filtered['Status'].astype(str).str.lower()
    total_pendente = (s == 'pendente').sum()
    total_renovado = (s == 'renovado').sum()

col1.metric("💰 Produção Total (R$)", f"{total_premio:,.2f}".replace(',','X').replace('.',',').replace('X','.'))
col2.metric("🔴 Pendentes", total_pendente)
col3.metric("🟢 Renovados", total_renovado)

# Chart: production by day
if 'Dia' in df_filtered.columns and 'Prêmio Líquido' in df_filtered.columns:
    # try convert Dia to datetime
    try:
        df_chart = df_filtered.copy()
        df_chart['Dia_dt'] = pd.to_datetime(df_chart['Dia'], dayfirst=True, errors='coerce')
        df_chart = df_chart.dropna(subset=['Dia_dt'])
        df_group = df_chart.groupby('Dia_dt', as_index=False)['Prêmio Líquido'].sum()
        df_group['Prêmio Líquido'] = pd.to_numeric(df_group['Prêmio Líquido'].astype(str).str.replace('[^0-9,.-]','', regex=True).str.replace(',', '.'), errors='coerce')
        fig = px.bar(df_group, x='Dia_dt', y='Prêmio Líquido', labels={'Dia_dt':'Dia','Prêmio Líquido':'Prêmio'}, title='Produção por Dia')
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info('Não foi possível gerar gráfico por Dia: ' + str(e))

st.subheader('Tabela de Registros')

# Build display table with status indicator
show_cols = [c for c in df_filtered.columns if c in expected_cols]
# If not all expected, just display common ones
if not show_cols:
    show_cols = df_filtered.columns.tolist()

# create copy for display
display_df = df_filtered.copy()

# Create HTML column for status indicator
def render_status_cell(val):
    v = str(val).strip().lower()
    if v == 'pendente':
        return '<span style="display:flex;align-items:center;gap:8px;"><span class="pulse-red"></span><span style="color:#d10b0b;font-weight:600">Pendente</span></span>'
    elif v == 'renovado':
        return '<span style="display:flex;align-items:center;gap:8px;"><span class="pulse-green"></span><span style="color:#107f3a;font-weight:600">Renovado</span></span>'
    else:
        return str(val)

if 'Status' in display_df.columns:
    display_df['Status'] = display_df['Status'].apply(render_status_cell)

# Use st.write with unsafe_allow_html by converting to HTML table
# Simpler: render rows manually

table_html = '<table style="width:100%;border-collapse:collapse">'
# header
table_html += '<thead><tr>'
for col in show_cols:
    table_html += f'<th style="text-align:left;padding:8px;border-bottom:1px solid #eee">{col}</th>'
# ensure Status shown last
if 'Status' in display_df.columns and 'Status' not in show_cols:
    table_html += '<th style="text-align:left;padding:8px;border-bottom:1px solid #eee">Status</th>'

table_html += '</tr></thead>'
# body
table_html += '<tbody>'
for _, row in display_df.iterrows():
    table_html += '<tr>'
    for col in show_cols:
        val = row.get(col, '')
        table_html += f'<td style="padding:10px;border-bottom:1px solid #fafafa;vertical-align:top">{val}</td>'
    # status cell
    if 'Status' in display_df.columns and 'Status' not in show_cols:
        table_html += f'<td style="padding:10px;border-bottom:1px solid #fafafa;vertical-align:top">{row.get("Status","")}</td>'
    table_html += '</tr>'

table_html += '</tbody></table>'

st.markdown(table_html, unsafe_allow_html=True)

st.markdown('\n---\n')
st.caption('Painel gerado automaticamente. Atualize a planilha no Google Sheets e recarregue a página.')
