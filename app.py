# Arquivo principal do painel
# Para rodar: streamlit run app.py
import streamlit as st

st.set_page_config(page_title="Números que Falam", layout="wide")

paginas = [
    st.Page("telas/inicio.py", title="Início", default=True),
    st.Page("telas/curso_superior.py", title="Curso Superior"),
    st.Page("telas/crescimento.py", title="Crescimento Demográfico"),
]
st.navigation(paginas).run()
