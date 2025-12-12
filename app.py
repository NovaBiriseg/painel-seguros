import streamlit as st
import pandas as pd
from config import load_sheet

st.set_page_config(
    page_title="Painel de Seguros",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
    <style>
        .blink {
            animation: blinker 1.2s linear infinite;
            color: red;
            font-weight: bold;
        }
        @keyframes blinker {
            50% { opacity: 0; }
        }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Painel de Seguros")

# --------- Carregar Sheets ---------
try:
    df = load_sheet()
except Exception as e:
    st.error("❌ Não foi possível carregar os dados da planilha. Verifique a URL e o ID no st.secrets.")
    st.stop()

# --------- Ajustes de Colunas ---------
df.columns = df.columns.str.strip().str.lower()

required_cols = ["status", "cliente", "produto", "telefone"]

for col in required_cols:
    if col not in df.columns:
        st.warning(f"⚠️ A coluna obrigatória **'{col}'** não existe na planilha.")
        st.stop()

# --------- Filtro ---------
status_filter = st.sidebar.selectbox("Filtrar por Status:", ["todos", "concluído", "pendente"])

if status_filter == "todos":
    df_filtered = df
else:
    df_filtered = df[df["status"] == status_filter]

# --------- Métricas ---------
col1, col2 = st.columns(2)

col1.metric("🟢 Concluídos", (df_filtered["status"] == "concluído").sum())

pendentes = (df_filtered["status"] == "pendente").sum()

col2.markdown(
    f"<div class='blink'>🔴 Pendentes: {pendentes}</div>",
    unsafe_allow_html=True
)

# --------- Tabela ---------
st.subheader("📄 Registros")
st.dataframe(df_filtered, use_container_width=True)
