import streamlit as st
import pandas as pd
import requests
from io import BytesIO

st.set_page_config(page_title="Painel de Seguros", layout="wide")

# ============================================================
# URL DO GOOGLE SHEETS (com link de exportação .xlsx)
# ============================================================
EXCEL_URL = "https://docs.google.com/spreadsheets/d/18DKFhsyTjJZcG7FqfB757DkPDDA2YgT0/export?format=xlsx"

# ============================================================
# Função para carregar todas as abas da planilha
# ============================================================
@st.cache_data(ttl=60)
def load_all_sheets(url):
    try:
        # Baixa a planilha do Google Sheets
        resp = requests.get(url)
        resp.raise_for_status()

        # Lê as abas e as coloca em um dicionário
        xls = pd.read_excel(BytesIO(resp.content), sheet_name=None, engine="openpyxl")

        # Limpa os nomes das colunas (removendo espaços extras)
        for k, df in xls.items():
            df.columns = [str(c).strip() for c in df.columns]

        return xls

    except Exception as e:
        st.error("Erro ao carregar planilha do Google Sheets.")
        st.code(str(e))
        return {}

# ============================================================
# Carrega as planilhas
# ============================================================
sheets = load_all_sheets(EXCEL_URL)

if not sheets:
    st.error("❌ Não foi possível carregar nenhuma aba do Google Sheets.")
    st.stop()

# ============================================================
# Seleção de aba
# ============================================================
abas = list(sheets.keys())
aba = st.selectbox("Escolha a aba da planilha:", abas)

df = sheets.get(aba, pd.DataFrame()).copy()

df.columns = df.columns.str.strip().str.lower()

# ============================================================
# Função para normalizar status (tolerante)
# ============================================================
def normalize_status(x):
    s = str(x).lower().strip().replace("\xa0", " ")  # remove NBSP e normaliza
    if "pend" in s:
        return "pendente"
    elif "renov" in s:
        return "renovado"
    return s

if "status" in df.columns:
    df["status"] = df["status"].apply(normalize_status)

# ============================================================
# SIDEBAR – FILTROS
# ============================================================
st.sidebar.header("Filtros")

colab_list = ["Todos"]
if "colaborador" in df.columns:
    colab_list += sorted(df["colaborador"].dropna().astype(str).unique().tolist())
colaborador = st.sidebar.selectbox("Colaborador", colab_list)

status_list = ["Todos", "pendente", "renovado"]
status_filter = st.sidebar.selectbox("Status", status_list)

busca = st.sidebar.text_input("Buscar por CPF / Apólice / Segurado")

df_filtered = df.copy()

if colaborador != "Todos":
    df_filtered = df_filtered[df_filtered["colaborador"] == colaborador]

if status_filter != "Todos":
    df_filtered = df_filtered[df_filtered["status"] == status_filter]

if busca:
    q = busca.lower()
    mask = pd.Series(False, index=df_filtered.index)
    for c in ["cpf/cnpj", "apólice", "segurado"]:
        if c in df_filtered.columns:
            mask |= df_filtered[c].astype(str).str.lower().str.contains(q)
    df_filtered = df_filtered[mask]

# ============================================================
# RESUMO DAS MÉTRICAS
# ============================================================
st.subheader("Resumo")

col1, col2, col3 = st.columns(3)

total_premio = 0
if "prêmio líquido" in df_filtered.columns:
    total_premio = pd.to_numeric(
        df_filtered["prêmio líquido"].astype(str).str.replace('[^0-9,.-]', '', regex=True).str.replace(',', '.'),
        errors="coerce"
    ).sum()

col1.metric("💰 Produção Total (R$)", f"{total_premio:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

col2.metric("🔴 Pendentes", (df_filtered["status"] == "pendente").sum())
col3.metric("🟢 Renovados", (df_filtered["status"] == "renovado").sum())

# ============================================================
# GRÁFICO DE PRODUÇÃO POR DIA
# ============================================================
if "dia" in df_filtered.columns and "prêmio líquido" in df_filtered.columns:
    df_chart = df_filtered.copy()
    df_chart["dia_dt"] = pd.to_datetime(df_chart["dia"], dayfirst=True, errors="coerce")
    df_chart["prêmio líquido"] = pd.to_numeric(
        df_chart["prêmio líquido"].astype(str).str.replace('[^0-9,.-]', '', regex=True).str.replace(',', '.'),
        errors="coerce"
    )

    df_group = df_chart.dropna(subset=["dia_dt"]).groupby("dia_dt", as_index=False)["prêmio líquido"].sum()

    fig = px.bar(df_group, x="dia_dt", y="prêmio líquido", title="Produção por Dia")
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TABELA COM INDICADORES VISUAIS (Pendente / Renovado)
# ============================================================
st.subheader("Tabela de Registros")

def render_indicator(val):
    if val == "pendente":
        return '<span class="indicador pendente"></span><b style="color:#ff4444">Pendente</b>'
    if val == "renovado":
        return '<span class="indicador renovado"></span><b style="color:#16a34a">Renovado</b>'
    return val

df_filtered["status_indicador"] = df_filtered["status"].apply(render_indicator)

show_cols = ["dia", "segurado", "apólice", "prêmio líquido", "cia", "item", "cpf/cnpj", "franquia", "colaborador", "status_indicador"]
show_cols = [c for c in show_cols if c in df_filtered.columns]

# Cria a tabela HTML
html = '<div class="table-wrap"><table class="custom"><thead><tr>'
html += "".join(f"<th>{c}</th>" for c in show_cols)
html += "</tr></thead><tbody>"

for _, row in df_filtered.iterrows():
    html += "<tr>"
    for c in show_cols:
        html += f"<td>{row[c]}</td>"
    html += "</tr>"

html += "</tbody></table></div>"

st.markdown(html, unsafe_allow_html=True)

st.caption("Atualize a planilha no Google Sheets e recarregue o app para ver as mudanças.")
