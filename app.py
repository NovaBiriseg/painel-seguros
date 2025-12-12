import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO

st.set_page_config(page_title="Painel de Seguros", layout="wide")

# ----------------------------------------------------------
# 1) URL da planilha vinda do Streamlit Secrets
# ----------------------------------------------------------
SHEET_URL = st.secrets["sheet_url"]

# ----------------------------------------------------------
# 2) CSS global
# ----------------------------------------------------------
st.markdown("""
<style>
.indicador { width: 14px; height: 14px; border-radius: 50%; display: inline-block; margin-right: 8px; }
.pendente { background-color: #ff4444; animation: pulse 1.1s infinite; }
.renovado { background-color: #16a34a; }

@keyframes pulse {
  0% { transform: scale(0.9); opacity: .7; }
  50% { transform: scale(1.25); opacity: 1; }
  100% { transform: scale(0.9); opacity: .7; }
}

.table-wrap { overflow:auto; }
table.custom { width:100%; border-collapse:collapse; font-family: Inter, Arial; }
table.custom th { padding:10px; border-bottom:1px solid #eee; background:#fafafa; font-weight:700; }
table.custom td { padding:10px; border-bottom:1px solid #f6f7fb; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Painel de Seguros — Produção & Renovações")
st.write("Carregando dados diretamente do Google Sheets (.xlsx).")

# ----------------------------------------------------------
# 3) Função para carregar todas as abas da planilha
# ----------------------------------------------------------

@st.cache_data(ttl=60)
def load_all_sheets(url):
    try:
        r = requests.get(url)
        r.raise_for_status()

        # Debug opcional:
        # st.write("Status:", r.status_code, "Bytes:", len(r.content))

        excel = pd.read_excel(BytesIO(r.content), sheet_name=None, engine="openpyxl")
        clean = {}
        for name, df in excel.items():
            df.columns = [str(c).strip() for c in df.columns]
            clean[name] = df
        return clean

    except Exception as e:
        st.error(f"Erro ao carregar Google Sheets: {e}")
        return None

sheets = load_all_sheets(SHEET_URL)
if sheets is None or len(sheets) == 0:
    st.error("❌ Não foi possível carregar nenhuma aba do Google Sheets.")
    st.stop()

# ----------------------------------------------------------
# 4) Selecionar aba
# ----------------------------------------------------------
abas = list(sheets.keys())
aba = st.selectbox("Escolha a aba:", abas)
df = sheets[aba].copy()

# ----------------------------------------------------------
# 5) Filtros
# ----------------------------------------------------------
st.sidebar.header("Filtros")

# Colaborador
colaboradores = ["Todos"]
if "Colaborador" in df.columns:
    colaboradores += sorted(df["Colaborador"].dropna().astype(str).unique())
colaborador = st.sidebar.selectbox("Colaborador:", colaboradores)

# Status
status_list = ["Todos"]
if "Status" in df.columns:
    status_list += sorted(df["Status"].dropna().astype(str).str.lower().unique())
status_sel = st.sidebar.selectbox("Status:", status_list)

# Busca
busca = st.sidebar.text_input("Buscar CPF / Apólice / Nome:")

# ----------------------------------------------------------
# 6) Aplicar filtros
# ----------------------------------------------------------
df_filtered = df.copy()

if colaborador != "Todos" and "Colaborador" in df.columns:
    df_filtered = df_filtered[df_filtered["Colaborador"] == colaborador]

if status_sel != "Todos" and "Status" in df.columns:
    df_filtered = df_filtered[df_filtered["Status"].astype(str).str.lower() == status_sel.lower()]

if busca:
    q = busca.lower()
    mask = pd.Series(False, index=df_filtered.index)
    for col in ["CPF/CNPJ", "Apólice", "Segurado"]:
        if col in df_filtered.columns:
            mask |= df_filtered[col].astype(str).str.lower().str.contains(q)
    df_filtered = df_filtered[mask]

# ----------------------------------------------------------
# 7) Métricas
# ----------------------------------------------------------
st.subheader("Resumo")

col1, col2, col3 = st.columns(3)

# Prêmio total
premio_total = 0
if "Prêmio Líquido" in df_filtered.columns:
    premio_total = (
        df_filtered["Prêmio Líquido"]
        .astype(str)
        .str.replace('[^0-9,.-]', '', regex=True)
        .str.replace(',', '.', regex=False)
        .astype(float)
        .sum()
    )

# Contar status
if "Status" in df_filtered.columns:
    s = df_filtered["Status"].astype(str).str.lower()
    total_pendente = (s == "pendente").sum()
    total_renovado = (s == "renovado").sum()
else:
    total_pendente = total_renovado = 0

col1.metric("💰 Produção Total (R$)", f"{premio_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col2.metric("🔴 Pendentes", total_pendente)
col3.metric("🟢 Renovados", total_renovado)

# ----------------------------------------------------------
# 8) Gráfico diário
# ----------------------------------------------------------
if "Dia" in df_filtered.columns and "Prêmio Líquido" in df_filtered.columns:
    try:
        grp = df_filtered.copy()
        grp["Dia_dt"] = pd.to_datetime(grp["Dia"], dayfirst=True, errors="coerce")
        grp["Prêmio"] = (
            grp["Prêmio Líquido"]
            .astype(str)
            .str.replace('[^0-9,.-]', '', regex=True)
            .str.replace(',', '.', regex=False)
            .astype(float)
        )
        grp = grp.dropna(subset=["Dia_dt"]).groupby("Dia_dt", as_index=False)["Prêmio"].sum()
        fig = px.bar(grp, x="Dia_dt", y="Prêmio", title="Produção por Dia")
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("Não foi possível gerar o gráfico.")

# ----------------------------------------------------------
# 9) Tabela com indicadores
# ----------------------------------------------------------

def render_indicator(v):
    v = str(v).strip().lower()
    if v == "pendente":
        return '<span class="indicador pendente"></span> <b style="color:#d10b0b">Pendente</b>'
    if v == "renovado":
        return '<span class="indicador renovado"></span> <b style="color:#107f3a">Renovado</b>'
    return v

st.subheader("Tabela de Registros")

cols_preferidas = ["Dia", "Segurado", "Apólice", "Prêmio Líquido", "Cia", "Item", "CPF/CNPJ", "Franquia", "Colaborador", "Status"]
cols = [c for c in cols_preferidas if c in df_filtered.columns]

if not cols:
    cols = df_filtered.columns.tolist()

df_display = df_filtered[cols].copy()

if "Status" in df_display.columns:
    df_display["Status"] = df_display["Status"].apply(render_indicator)

html = '<div class="table-wrap"><table class="custom">'
html += '<thead><tr>' + ''.join([f"<th>{c}</th>" for c in cols]) + "</tr></thead><tbody>"

for _, row in df_display.iterrows():
    html += "<tr>"
    for c in cols:
        html += f"<td>{row[c]}</td>"
    html += "</tr>"

html += "</tbody></table></div>"

st.markdown(html, unsafe_allow_html=True)

st.caption("Atualize os dados no Google Sheets e recarregue o app.")
