import streamlit as st
import pandas as pd
import requests
from io import StringIO

st.set_page_config(page_title="Painel de Seguros", layout="wide")

# ---------------------------------------------------------
# 1) Função para carregar todas as abas do Google Sheets
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def load_all_sheets_from_gsheets(sheet_url):

    # Extrai ID
    try:
        sheet_id = sheet_url.split("/d/")[1].split("/")[0]
    except:
        st.error("URL inválida do Google Sheets.")
        return {}

    gid_list = {
        "Aba 1": 0,
        "Aba 2": 1,
        "Aba 3": 2,
        "Aba 4": 3,
        "Aba 5": 4,
        "Aba 6": 5,
        "Aba 7": 6,
        "Aba 8": 7,
        "Aba 9": 8,
        "Aba 10": 9,
    }

    dfs = {}
    for name, gid in gid_list.items():
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

        try:
            r = requests.get(csv_url, timeout=15)
            if r.status_code == 200 and len(r.text) > 20:
                df = pd.read_csv(StringIO(r.text))

                df.columns = df.columns.str.strip().str.lower()

                dfs[name] = df
        except:
            pass

    return dfs


# ---------------------------------------------------------
# 2) URL do Google Sheets
# ---------------------------------------------------------
SHEET_URL = st.secrets.get("SHEET_URL", "")

if not SHEET_URL:
    st.error("❌ Nenhuma URL configurada em st.secrets.")
    st.stop()

dfs = load_all_sheets_from_gsheets(SHEET_URL)

if not dfs:
    st.error("❌ Não foi possível carregar nenhuma aba do Google Sheets.")
    st.stop()

# ---------------------------------------------------------
# 3) UI – seleção da aba
# ---------------------------------------------------------
st.sidebar.title("📄 Seleção da Aba")
selected_sheet = st.sidebar.selectbox("Escolha a aba", list(dfs.keys()))

df = dfs[selected_sheet].copy()

df.columns = df.columns.str.strip().str.lower()

st.write("🧪 *Colunas encontradas:*", list(df.columns))

# ---------------------------------------------------------
# 4) Área de métricas (indicadores)
# ---------------------------------------------------------
st.title("📊 Painel de Produção & Renovações")

col1, col2, col3 = st.columns(3)

col1.metric("📄 Registros", len(df))

col2.metric("🔴 Pendentes", (df["status"] == "pendente").sum())

col3.metric("🟢 Renovados", (df["status"] == "renovado").sum())

# ---------------------------------------------------------
# 5) Estilo CSS — círculos pulsando
# ---------------------------------------------------------
st.markdown("""
<style>
.pulse-red {
    height: 14px; width: 14px; border-radius: 50%;
    background: red;
    animation: pulseRed 1.5s infinite;
    display: inline-block;
}
@keyframes pulseRed {
    0% { box-shadow: 0 0 0 0 rgba(255,0,0,0.8); }
    70% { box-shadow: 0 0 0 10px rgba(255,0,0,0); }
    100% { box-shadow: 0 0 0 0 rgba(255,0,0,0); }
}
.pulse-green {
    height: 14px; width: 14px; border-radius: 50%;
    background: #00d400;
    animation: pulseGreen 1.5s infinite;
    display: inline-block;
}
@keyframes pulseGreen {
    0% { box-shadow: 0 0 0 0 rgba(0,255,0,0.8); }
    70% { box-shadow: 0 0 0 10px rgba(0,255,0,0); }
    100% { box-shadow: 0 0 0 0 rgba(0,255,0,0); }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6) Tabela com status visual
# ---------------------------------------------------------
def render_status(status):
    if status == "pendente":
        return '<span class="pulse-red"></span> Pendente'
    elif status == "renovado":
        return '<span class="pulse-green"></span> Renovado'
    return status

if "status" in df.columns:
    df["status_indicador"] = df["status"].apply(render_status)
else:
    st.error("❌ A coluna 'Status' não existe na aba selecionada.")

df_display = df.copy()

if "status_indicador" in df_display.columns:
    df_display["status_indicador"] = df_display["status_indicador"].astype(str)

st.subheader("📋 Tabela de Registros")
st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)
