import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import requests

st.set_page_config(page_title="Painel de Seguros", layout="wide")

# ----------------------------------------------------
# 🔗 LINK DIRETO DO GOOGLE SHEETS (EXPORT XLSX)
# ----------------------------------------------------
EXCEL_URL = "https://docs.google.com/spreadsheets/d/18DKFhsyTjJZcG7FqfB757DkPDDA2YgT0/export?format=xlsx"


# ----------------------------------------------------
# 🎨 CSS GLOBAL
# ----------------------------------------------------
st.markdown("""
<style>
.indicador { width: 14px; height: 14px; border-radius: 50%; display: inline-block; margin-right: 8px; vertical-align: middle; }
.pendente { background-color: #ff4444; animation: pulse 1.2s infinite; }
.renovado { background-color: #16a34a; }

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.7; }
  50% { transform: scale(1.25); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.7; }
}

.table-wrap { overflow:auto; }
table.custom { width:100%; border-collapse:collapse; font-family: Inter, Arial, sans-serif; }
table.custom th { text-align:left; padding:10px; border-bottom:1px solid #eee; background:#fafafa; font-weight:700; }
table.custom td { padding:10px; border-bottom:1px solid #f6f7fb; vertical-align:top; }
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------
# 📥 CARREGAR TODAS AS ABAS DO GOOGLE SHEETS
# ----------------------------------------------------
@st.cache_data(ttl=60)
def load_all_sheets(url):
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()

        xls = pd.read_excel(BytesIO(resp.content), sheet_name=None, engine="openpyxl")

        # limpar nomes de colunas
        for k, df in xls.items():
            df.columns = [str(c).strip() for c in df.columns]

        return xls

    except Exception as e:
        st.error("❌ Erro ao carregar planilha do Google Sheets.")
        st.code(str(e))
        return {}


# ----------------------------------------------------
# 🔄 CARREGAMENTO INICIAL
# ----------------------------------------------------
sheets = load_all_sheets(EXCEL_URL)
if not sheets:
    st.stop()

abas = list(sheets.keys())
st.title("📊 Painel de Produção & Renovações – Corretora de Seguros")
aba = st.selectbox("Escolha a aba da planilha:", abas)

df = sheets.get(aba, pd.DataFrame()).copy()
df.columns = [str(c).strip() for c in df.columns]


# ----------------------------------------------------
# 🎚️ SIDEBAR – FILTROS
# ----------------------------------------------------
st.sidebar.header("Filtros")

# Colaborador
colab_list = ["Todos"]
if "Colaborador" in df.columns:
    colab_list += sorted(df["Colaborador"].dropna().astype(str).unique().tolist())
colaborador = st.sidebar.selectbox("Colaborador", colab_list)

# Status
status_list = ["Todos"]
if "Status" in df.columns:
    status_list += sorted(df["Status"].dropna().astype(str).str.lower().unique().tolist())
status_filter = st.sidebar.selectbox("Status", status_list)

# Busca
busca = st.sidebar.text_input("Buscar por CPF / Apólice / Segurado")


# ----------------------------------------------------
# 🔍 APLICAR FILTROS
# ----------------------------------------------------
df_filtered = df.copy()

if colaborador != "Todos" and "Colaborador" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Colaborador"] == colaborador]

if status_filter != "Todos" and "Status" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Status"].astype(str).str.lower() == status_filter.lower()]

if busca.strip():
    q = busca.lower()
    mask = pd.Series(False, df_filtered.index)
    for c in ["CPF/CNPJ", "Apólice", "Segurado"]:
        if c in df_filtered.columns:
            mask |= df_filtered[c].astype(str).str.lower().str.contains(q)
    df_filtered = df_filtered[mask]


# ----------------------------------------------------
# 📌 MÉTRICAS
# ----------------------------------------------------
st.subheader("Resumo")
col1, col2, col3 = st.columns(3)

total_premio = 0
if "Prêmio Líquido" in df_filtered.columns:
    temp = df_filtered["Prêmio Líquido"].astype(str)
    temp = temp.str.replace('[^0-9,.-]', '', regex=True).str.replace(',', '.')
    total_premio = pd.to_numeric(temp, errors='coerce').sum()

# contar status
total_pendente = 0
total_renovado = 0
if "Status" in df_filtered.columns:
    s = df_filtered["Status"].astype(str).str.lower()
    total_pendente = (s == "pendente").sum()
    total_renovado = (s == "renovado").sum()

col1.metric("💰 Produção Total (R$)", f"{total_premio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
col2.metric("🔴 Pendentes", total_pendente)
col3.metric("🟢 Renovados", total_renovado)


# ----------------------------------------------------
# 📊 GRÁFICO POR DIA
# ----------------------------------------------------
if "Dia" in df_filtered.columns and "Prêmio Líquido" in df_filtered.columns:
    try:
        df_chart = df_filtered.copy()
        df_chart["Dia_dt"] = pd.to_datetime(df_chart["Dia"], errors="coerce", dayfirst=True)
        df_chart["Prêmio Líquido"] = pd.to_numeric(
            df_chart["Prêmio Líquido"].astype(str)
            .str.replace('[^0-9,.-]', '', regex=True)
            .str.replace(',', '.'),
            errors="coerce"
        )

        df_group = df_chart.dropna(subset=["Dia_dt"]).groupby("Dia_dt", as_index=False)["Prêmio Líquido"].sum()

        fig = px.bar(df_group, x="Dia_dt", y="Prêmio Líquido", title="Produção por Dia")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error("Erro ao gerar gráfico:")
        st.code(str(e))


# ----------------------------------------------------
# 📋 TABELA HTML COM INDICADORES
# ----------------------------------------------------
st.subheader("Tabela de Registros")

preferred = ["Dia","Segurado","Apólice","Prêmio Líquido","Cia","Item","CPF/CNPJ","Franquia","Colaborador","Status"]
show_cols = [c for c in preferred if c in df_filtered.columns]
if not show_cols:
    show_cols = df_filtered.columns.tolist()

display_df = df_filtered[show_cols].copy()

# Ícones de status
def render_indicator(v):
    val = str(v).strip().lower()
    if val == "pendente":
        return '<span class="indicador pendente"></span><b style="color:#b30000">Pendente</b>'
    if val == "renovado":
        return '<span class="indicador renovado"></span><b style="color:#0e7c3a">Renovado</b>'
    return v

if "Status" in display_df.columns:
    display_df["Status"] = display_df["Status"].apply(render_indicator)

# HTML
html = '<div class="table-wrap"><table class="custom">'
html += '<thead><tr>' + ''.join(f'<th>{c}</th>' for c in show_cols) + '</tr></thead><tbody>'

for _, row in display_df.iterrows():
    html += '<tr>'
    for c in show_cols:
        html += f"<td>{row[c]}</td>"
    html += '</tr>'

html += '</tbody></table></div>'

st.markdown(html, unsafe_allow_html=True)

st.caption("Atualize o Google Sheets e recarregue o painel para ver as mudanças.")
