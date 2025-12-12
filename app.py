import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO

st.set_page_config(page_title="Painel de Seguros", layout="wide")

# ============================================================
# CONFIG — LINK DIRETO PARA EXPORTAR XLSX DO GOOGLE SHEETS
# ============================================================
EXCEL_URL = "https://docs.google.com/spreadsheets/d/18DKFhsyTjJZcG7FqfB757DkPDDA2YgT0/export?format=xlsx"

# ============================================================
# CSS GLOBAL (INDICADORES PULSANDO + TABELA)
# ============================================================
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
table.custom td { padding:10px; border-bottom:1px solid #f6f7fb; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# FUNÇÃO PARA BAIXAR TODAS AS ABAS DA PLANILHA
# ============================================================
@st.cache_data(ttl=60)
def load_all_sheets(url):
    resp = requests.get(url)
    resp.raise_for_status()
    xls = pd.read_excel(BytesIO(resp.content), sheet_name=None, engine="openpyxl")

    # Normaliza colunas
    for k, df in xls.items():
        df.columns = [str(c).strip() for c in df.columns]
    return xls

sheets = load_all_sheets(EXCEL_URL)

abas = list(sheets.keys())
aba = st.selectbox("Escolha a aba da planilha:", abas)

df = sheets.get(aba, pd.DataFrame()).copy()

# ============================================================
# NORMALIZAÇÃO DO STATUS (CORRIGE QUALQUER TEXTO)
# ============================================================
def normalize_status(x):
    if pd.isna(x):
        return ""
    s = str(x)

    # Remove espaços invisíveis
    s = s.replace("\xa0", " ")

    # Remove múltiplos espaços
    s = " ".join(s.split())

    # Lowercase
    s = s.strip().lower()

    # Regras flexíveis
    if "pend" in s:
        return "pendente"
    if "renov" in s or s == "ok":
        return "renovado"

    return s

if "Status" in df.columns:
    df["Status"] = df["Status"].apply(normalize_status)

# ============================================================
# SIDEBAR — FILTROS
# ============================================================
st.sidebar.header("Filtros")

colab_list = ["Todos"]
if "Colaborador" in df.columns:
    colab_list += sorted(df["Colaborador"].dropna().astype(str).unique().tolist())
colaborador = st.sidebar.selectbox("Colaborador", colab_list)

status_list = ["Todos", "pendente", "renovado"]
status_filter = st.sidebar.selectbox("Status", status_list)

busca = st.sidebar.text_input("Buscar por CPF / Apólice / Segurado")

df_filtered = df.copy()

if colaborador != "Todos":
    df_filtered = df_filtered[df_filtered["Colaborador"] == colaborador]

if status_filter != "Todos":
    df_filtered = df_filtered[df_filtered["Status"] == status_filter]

if busca:
    q = busca.lower()
    mask = pd.Series(False, index=df_filtered.index)
    for c in ["CPF/CNPJ", "Apólice", "Segurado"]:
        if c in df_filtered.columns:
            mask |= df_filtered[c].astype(str).str.lower().str.contains(q)
    df_filtered = df_filtered[mask]

# ============================================================
# RESUMO
# ============================================================
st.subheader("Resumo")

col1, col2, col3 = st.columns(3)

total_premio = 0
if "Prêmio Líquido" in df_filtered.columns:
    total_premio = pd.to_numeric(
        df_filtered["Prêmio Líquido"].astype(str).str.replace('[^0-9,.-]', '', regex=True).str.replace(',', '.'),
        errors="coerce"
    ).sum()

col1.metric("💰 Produção Total (R$)", f"{total_premio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

col2.metric("🔴 Pendentes", (df_filtered["Status"] == "pendente").sum())
col3.metric("🟢 Renovados", (df_filtered["Status"] == "renovado").sum())

# ============================================================
# GRÁFICO
# ============================================================
if "Dia" in df_filtered.columns and "Prêmio Líquido" in df_filtered.columns:
    df_chart = df_filtered.copy()
    df_chart["Dia_dt"] = pd.to_datetime(df_chart["Dia"], dayfirst=True, errors="coerce")
    df_chart["Prêmio Líquido"] = pd.to_numeric(
        df_chart["Prêmio Líquido"].astype(str).str.replace('[^0-9,.-]', '', regex=True).str.replace(',', '.'),
        errors="coerce"
    )

    grp = df_chart.dropna(subset=["Dia_dt"]).groupby("Dia_dt", as_index=False)["Prêmio Líquido"].sum()

    fig = px.bar(grp, x="Dia_dt", y="Prêmio Líquido", title="Produção por Dia")
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TABELA HTML COM INDICADORES
# ============================================================
def render_indicator(v):
    if v == "pendente":
        return '<span class="indicador pendente"></span><b style="color:#b30000">Pendente</b>'
    if v == "renovado":
        return '<span class="indicador renovado"></span><b style="color:#0f7d3a">Renovado</b>'
    return v

show_cols = ["Dia", "Segurado", "Apólice", "Prêmio Líquido", "Cia", "Item", "CPF/CNPJ", "Franquia", "Colaborador", "Status"]
show_cols = [c for c in show_cols if c in df_filtered.columns]

display_df = df_filtered[show_cols].copy()

if "Status" in display_df.columns:
    display_df["Status"] = display_df["Status"].apply(render_indicator)

# Monta HTML
html = '<div class="table-wrap"><table class="custom"><thead><tr>'
html += "".join(f"<th>{c}</th>" for c in show_cols)
html += "</tr></thead><tbody>"

for _, row in display_df.iterrows():
    html += "<tr>"
    for c in show_cols:
        html += f"<td>{row[c]}</td>"
    html += "</tr>"

html += "</tbody></table></div>"

st.markdown(html, unsafe_allow_html=True)

st.caption("Atualize a planilha no Google Sheets e recarregue o app para ver mudanças.")
