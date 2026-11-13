# Página inicial: nome da startup e quem fez cada indicador
import streamlit as st

st.title("Números que Falam - Consultoria de Dados")
st.write("Painel com dados do IBGE sobre ensino superior e crescimento da população.")

st.subheader("Equipe")
coluna1, coluna2 = st.columns(2)
coluna1.markdown("**Caio Antunes Guedes Alves Da Silva**  \nIndicador: Curso Superior")
coluna2.markdown("**Davi Pimentel de Moraes**  \nIndicador: População e Crescimento Demográfico")
