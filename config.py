import pandas as pd
import streamlit as st

def load_sheet():
    """
    Carrega a planilha do Google Sheets usando a URL definida em st.secrets.
    """
    try:
        sheet_url = st.secrets["sheet_url"]
    except KeyError:
        raise Exception("Nenhuma URL configurada em st.secrets")

    if not sheet_url.startswith("https://docs.google.com/spreadsheets"):
        raise Exception("URL inválida de Google Sheets")

    csv_url = sheet_url.replace("/edit#gid=", "/export?format=csv&gid=")

    return pd.read_csv(csv_url)
