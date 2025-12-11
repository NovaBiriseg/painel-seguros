# Painel de Seguros - Streamlit


Este projeto é o painel completo conectado ao seu Google Sheet (download .xlsx). Já vem com:

- seleção de abas da planilha
- tabela com filtros e busca
- cards resumo (produção, pendentes, renovados)
- gráfico de produção por dia
- status com indicador (círculo vermelho pulsando para *pendente*, verde para *renovado*)

## Como usar

1. Descompacte o arquivo `painel-seguros.zip`.
2. (Opcional) Edite `config.py` se quiser alterar a URL da planilha.
3. Crie um ambiente virtual e instale dependências:

```bash
python -m venv venv
source venv/bin/activate  # mac/linux
venv\Scripts\activate     # windows
pip install -r requirements.txt
```

4. Rode o app localmente:

```bash
streamlit run app.py
```

5. Para deploy rápido: suba o repositório no GitHub e faça deploy no Streamlit Cloud (https://streamlit.io/cloud) — apontando para `app.py`.

## Observações
- A planilha precisa estar compartilhada como **Qualquer pessoa com o link - Leitor**.
- A coluna `Status` deve existir com valores `pendente` ou `renovado` (case-insensitive) para exibir os indicadores.
