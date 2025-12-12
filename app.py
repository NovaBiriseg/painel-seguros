import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Painel de Seguros", layout="wide")

st.title("📊 Painel de Produção & Renovações")

###############################
# CONFIGURAÇÃO DAS ABAS
###############################

SHEET_ID = "18DKFhsyTjJZcG7FqfB757DkPDDA2YgT0"

ABAS = {
    "2026": "987523559",
    "2027": "1167663822"
}

###############################
# FUNÇÃO PARA CARREGAR UMA ABA
###############################

@st.cache_data(ttl=30)
def carregar_aba(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url, dtype=str)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar aba (gid={gid}): {e}")
        return None


###############################
# SELETOR DE ABA
###############################

aba_escolhida = st.selectbox("Selecione a Aba da Planilha:", list(ABAS.keys()))

df = carregar_aba(SHEET_ID, ABAS[aba_escolhida])

if df is None or df.empty:
    st.error("❌ Não foi possível carregar os dados da aba selecionada.")
    st.stop()

###############################
# NORMALIZAR COLUNA STATUS
###############################

if "Status" not in df.columns:
    st.error("A planilha precisa ter uma coluna chamada 'Status'.")
    st.stop()

df["Status"] = df["Status"].str.lower().fillna("")

###############################
# INDICADORES
###############################

st.subheader("Indicadores")

col1, col2 = st.columns(2)

pendentes = (df["Status"] == "pendente").sum()
renovados = (df["Status"] == "renovado").sum()

with col1:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:12px;">
            <div class="pulse-red"></div>
            <h3 style="margin:0;">Pendentes: {pendentes}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:12px;">
            <div class="green-dot"></div>
            <h3 style="margin:0;">Renovados: {renovados}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

###############################
# CSS DOS INDICADORES
###############################

st.markdown("""
<style>
.pulse-red {
  width: 16px;
  height: 16px;
  background-color: red;
  border-radius: 50%;
  animation: pulse 1.2s infinite;
}
@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.7; }
  50% { transform: scale(1.4); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.7; }
}

.green-dot {
  width: 16px;
  height: 16px;
  background-color: #00cc66;
  border-radius: 50%;
}
</style>
""", unsafe_allow_html=True)


###############################
# MOSTRAR TABELA
###############################

st.subheader("📄 Registros da Aba Selecionada")
st.dataframe(df, use_container_width=True)
