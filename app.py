import streamlit as st
import pandas as pd
import plotly.express as px
from config import EXCEL_URL
from io import BytesIO
import requests

st.set_page_config(page_title="Painel de Seguros", layout="wide")

# ---- CSS GLOBAL ----
st.markdown("""
<style>
.indicador { 
    width: 14px; height: 14px; border-radius: 50%; 
    display: inline-block; margin-right: 8px; 
    vertical-align: middle;
}
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

st.title("📊 Painel de Produção & Renovações – Corretora de Seguros")
st.write("Leia a planilha (export .xlsx) e selecione a aba desejada.")


# ---- CARREGAR TODAS AS ABAS ----
@st.cache_data(ttl=60)
def load_all_sheets(url):
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        xls = pd.read_excel(BytesIO(resp.content), sheet_name=None, engine="openpyxl")
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

df = sheets.get(aba).copy()


# ---- NORMALIZAÇÃO DO STATUS ----
def normalize_status(val):
    x = str(val)
    x = x.replace("\xa0", " ")        # remove NBSP
    x = " ".join(x.split())           # remove múltiplos espaços
    return x.strip().lower()


if "Status" in df.columns:
    df["Status_norm"] = df["Status"].apply(normalize_status)
else:
    df["Status_norm"] = ""


# ---- FILTROS ----
st.sidebar.header("Filtros")

colaborador_list = ["Todos"]
if "Colaborador" in df.columns:
    colaborador_list += sorted(df["Colaborador"].dropna().astype(str).unique().tolist())
colaborador = st.sidebar.selectbox("Colaborador", colaborador_list)

status_list = ["Todos"]
status_unique = sorted(df["Status_norm"].unique().tolist())
status_list += status_unique
status_filter = st.sidebar.selectbox("Status", status_list)

busca = st.sidebar.text_input("Buscar por CPF / Apólice / Segurado")

df_filtered = df.copy()

if colaborador != "Todos":
    df_filtered = df_filtered[df_filtered["Colaborador"] == colaborador]

if status_filter != "Todos":
    df_filtered = df_filtered[df_filtered["Status_norm"] == status_filter]

if busca.strip():
    q = busca.lower()
    mask = pd.Series(False, index=df_filtered.index)
    for c in ["CPF/CNPJ", "Apólice", "Segurado"]:
        if c in df_filtered.columns:
            mask |= df_filtered[c].astype(str).str.lower().str.contains(q)
    df_filtered = df_filtered[mask]


# ---- MÉTRICAS ----
st.subheader("Resumo")
col1, col2, col3 = st.columns(3)

total_premio = 0
if "Prêmio Líquido" in df_filtered.columns:
    total_premio = pd.to_numeric(
        df_filtered["Prêmio Líquido"].astype(str)
        .str.replace('[^0-9,.-]', '', regex=True)
        .str.replace(',', '.'),
        errors="coerce"
    ).sum()

total_pendente = (df_filtered["Status_norm"] == "pendente").sum()
total_renovado = (df_filtered["Status_norm"] == "renovado").sum()

col1.metric("💰 Produção Total (R$)", f"{total_premio:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
col2.metric("🔴 Pendentes", total_pendente)
col3.metric("🟢 Renovados", total_renovado)


# ---- GRÁFICO ----
if "Dia" in df_filtered.columns and "Prêmio Líquido" in df_filtered.columns:
    try:
        df_chart = df_filtered.copy()
        df_chart["Dia_dt"] = pd.to_datetime(df_chart["Dia"], dayfirst=True, errors="coerce")
        df_chart["Prêmio Líquido"] = pd.to_numeric(
            df_chart["Prêmio Líquido"].astype(str)
            .str.replace('[^0-9,.-]', '', regex=True)
            .str.replace(',', '.'),
            errors="coerce"
        )
        df_group = df_chart.dropna(subset=["Dia_dt"]).groupby("Dia_dt", as_index=False)["Prêmio Líquido"].sum()
        fig = px.bar(df_group, x="Dia_dt", y="Prêmio Líquido", title="Produção por Dia")
        st.plotly_chart(fig, use_container_width=True)
    except:
        pass


# ---- INDICADORES (HTML) ----
def render_indicator(val):
    raw = str(val)
    v = normalize_status(val)

    if "pend" in v:
        return '<span class="indicador pendente"></span><b style="color:#c10000">Pendente</b>'
    if "renov" in v or v == "ok":
        return '<span class="indicador renovado"></span><b style="color:#0a7f3a">Renovado</b>'

    return raw


# ---- TABELA ----
st.subheader("Tabela de Registros")

preferred = ["Dia", "Segurado", "Apólice", "Prêmio Líquido", "Cia", "Item", "CPF/CNPJ", "Franquia", "Colaborador", "Status"]
show_cols = [c for c in preferred if c in df_filtered.columns]

display_df = df_filtered[show_cols].copy()

if "Status" in display_df.columns:
    display_df["Status"] = display_df["Status"].apply(render_indicator)


html = '<div class="table-wrap"><table class="custom">'
html += '<thead><tr>' + ''.join(f'<th>{c}</th>' for c in show_cols) + '</tr></thead><tbody>'

for _, row in display_df.iterrows():
    html += '<tr>'
    for c in show_cols:
        html += f'<td>{row[c]}</td>'
    html += '</tr>'

html += '</tbody></table></div>'

st.markdown(html, unsafe_allow_html=True)

st.caption("Atualize a planilha e recarregue o app.")


