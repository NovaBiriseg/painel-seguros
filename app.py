import streamlit as st
import pandas as pd
import plotly.express as px
from config import EXCEL_URL
from io import BytesIO
import requests

st.set_page_config(page_title="Painel de Seguros", layout="wide")

# ---- CSS GLOBAL (colocado fora de qualquer função/cache) ----
st.markdown("""
<style>
/* Indicadores */
.indicador { width: 14px; height: 14px; border-radius: 50%; display: inline-block; margin-right: 8px; vertical-align: middle; }
.pendente { background-color: #ff4444; animation: pulse 1.2s infinite; }
.renovado { background-color: #16a34a; }

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.7; }
  50% { transform: scale(1.25); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.7; }
}

/* Layout tabela */
.table-wrap { overflow:auto; }
table.custom { width:100%; border-collapse:collapse; font-family: Inter, Arial, sans-serif; }
table.custom th { text-align:left; padding:10px; border-bottom:1px solid #eee; background:#fafafa; font-weight:700; }
table.custom td { padding:10px; border-bottom:1px solid #f6f7fb; vertical-align:top; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Painel de Produção & Renovações – Corretora de Seguros")
st.write("Leia a planilha (export .xlsx) e selecione a aba desejada.")

# ---- Helper: load all sheets as dict of DataFrames (serializável) ----
@st.cache_data(ttl=60)
def load_all_sheets(url):
    try:
        # baixar bytes e usar pandas.read_excel(sheet_name=None)
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        xls = pd.read_excel(BytesIO(resp.content), sheet_name=None, engine="openpyxl")
        # trim column names
        for k, df in xls.items():
            df.columns = [str(c).strip() for c in df.columns]
        return xls
    except Exception as e:
        st.error("Erro ao carregar planilha: " + str(e))
        return None

sheets = load_all_sheets(EXCEL_URL)
if sheets is None:
    st.stop()

abas = list(sheets.keys())
aba = st.selectbox("Escolha a aba da planilha:", abas)

# DataFrame da aba selecionada
df = sheets.get(aba).copy()
df.columns = [str(c).strip() for c in df.columns]

# ---- Sidebar filtros ----
st.sidebar.header("Filtros")
colaborador_list = ["Todos"]
if "Colaborador" in df.columns:
    colaborador_list += sorted(df["Colaborador"].dropna().astype(str).unique().tolist())
colaborador = st.sidebar.selectbox("Colaborador", colaborador_list)

status_options = ["Todos"]
if "Status" in df.columns:
    # pegar valores únicos normalizados
    uniques = sorted(df["Status"].dropna().astype(str).str.lower().unique().tolist())
    for u in uniques:
        if u not in status_options:
            status_options.append(u)
status_filter = st.sidebar.selectbox("Status", status_options)

busca = st.sidebar.text_input("Buscar por CPF / Apólice / Segurado")

# ---- Aplicar filtros ----
df_filtered = df.copy()
if colaborador != "Todos" and "Colaborador" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Colaborador"] == colaborador]

if status_filter and status_filter != "Todos" and "Status" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Status"].astype(str).str.lower() == status_filter.lower()]

if busca and busca.strip() != "":
    q = busca.strip().lower()
    mask = pd.Series(False, index=df_filtered.index)
    for c in ["CPF/CNPJ", "Apólice", "Segurado"]:
        if c in df_filtered.columns:
            mask = mask | df_filtered[c].astype(str).str.lower().str.contains(q)
    df_filtered = df_filtered[mask]

# ---- Métricas ----
st.subheader("Resumo")
col1, col2, col3 = st.columns(3)

total_premio = 0
if "Prêmio Líquido" in df_filtered.columns:
    total_premio = pd.to_numeric(df_filtered["Prêmio Líquido"].astype(str).str.replace('[^0-9,.-]','', regex=True).str.replace(',', '.'), errors='coerce').sum()

total_pendente = 0
total_renovado = 0
if "Status" in df_filtered.columns:
    s = df_filtered["Status"].astype(str).str.lower()
    total_pendente = (s == "pendente").sum()
    total_renovado = (s == "renovado").sum()

col1.metric("💰 Produção Total (R$)", f"{total_premio:,.2f}".replace(',','X').replace('.',',').replace('X','.'))
col2.metric("🔴 Pendentes", total_pendente)
col3.metric("🟢 Renovados", total_renovado)

# ---- Gráfico por Dia (se disponível) ----
if "Dia" in df_filtered.columns and "Prêmio Líquido" in df_filtered.columns:
    try:
        df_chart = df_filtered.copy()
        df_chart["Dia_dt"] = pd.to_datetime(df_chart["Dia"], dayfirst=True, errors="coerce")
        df_chart["Prêmio Líquido"] = pd.to_numeric(df_chart["Prêmio Líquido"].astype(str).str.replace('[^0-9,.-]','', regex=True).str.replace(',', '.'), errors="coerce")
        df_group = df_chart.dropna(subset=["Dia_dt"]).groupby("Dia_dt", as_index=False)["Prêmio Líquido"].sum()
        fig = px.bar(df_group, x="Dia_dt", y="Prêmio Líquido", labels={"Dia_dt":"Dia","Prêmio Líquido":"Prêmio"}, title="Produção por Dia")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info("Não foi possível gerar gráfico por Dia: " + str(e))

# ---- Tabela (HTML) com indicadores ----
st.subheader("Tabela de Registros")

# Decide colunas a mostrar (ordem amigável)
preferred = ["Dia","Segurado","Apólice","Prêmio Líquido","Cia","Item","CPF/CNPJ","Franquia","Colaborador","Status"]
show_cols = [c for c in preferred if c in df_filtered.columns]
if not show_cols:
    show_cols = df_filtered.columns.tolist()

display_df = df_filtered[show_cols].copy()

def render_indicator(val):
    v = str(val).strip().lower()
    if v == "pendente":
        return '<span class="indicador pendente"></span><span style="color:#d10b0b;font-weight:600">Pendente</span>'
    elif v == "renovado":
        return '<span class="indicador renovado"></span><span style="color:#107f3a;font-weight:600">Renovado</span>'
    else:
        return str(val)

if "Status" in display_df.columns:
    display_df["Status"] = display_df["Status"].apply(render_indicator)

# build HTML table
html = '<div class="table-wrap"><table class="custom">'
html += '<thead><tr>' + ''.join(f'<th>{c}</th>' for c in show_cols) + '</tr></thead><tbody>'
for _, row in display_df.iterrows():
    html += '<tr>'
    for c in show_cols:
        cell = row.get(c, "")
        html += f'<td>{cell}</td>'
    html += '</tr>'
html += '</tbody></table></div>'

st.markdown(html, unsafe_allow_html=True)

st.caption("Atualize a planilha no Google Sheets e recarregue o app para ver as mudanças.")
