# Tela do indicador Crescimento Demográfico
# Dados: Censos de 1970 a 2022 (tabelas 202, 4709, 9514 e 9515)
import json

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from funcoes import (achar_outliers, formatar, ler_base, mostrar_estatisticas, mostrar_noticias,
                     upload_ou_base_padrao)

# Cidades dos prefeitos do cenário (código IBGE: nome)
CIDADES_DAS_PERSONAS = {"4106902": "Curitiba", "4314902": "Porto Alegre",
                        "3106200": "Belo Horizonte", "2927408": "Salvador",
                        "4205407": "Florianópolis"}
REGIOES = ["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"]

# Código IBGE de cada estado, usado para abrir o mapa dos municípios
CODIGO_DO_ESTADO = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
    "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}

st.title("População e Crescimento Demográfico")
st.markdown("**Clientes:** Carlos (prefeito de Curitiba), Eduardo (Porto Alegre), "
            "Elisa (Belo Horizonte), Jorge (Salvador) e Roberto (Florianópolis). Eles estão "
            "revisando os Planos Diretores e o orçamento de saúde e infraestrutura.")
st.markdown("**Perguntas:**  \n"
            "1. Qual é a taxa média de crescimento acumulada por cidade?  \n"
            "2. Quais cidades são outliers: cresceram demais ou encolheram?")

# Dados
st.sidebar.header("Crescimento Demográfico")
censos = upload_ou_base_padrao(
    "Enviar população dos censos (CSV ou XLSX)", "populacao_censos.csv",
    ["cod_municipio", "municipio", "uf", "regiao", "ano", "populacao"], "upload_censos")
if "capital" not in censos.columns:
    censos["capital"] = False
envelhecimento = ler_base("crescimento_municipios.csv")
piramide = ler_base("piramide_uf.csv")

# Filtros da barra lateral
regioes = st.sidebar.multiselect("Região", REGIOES, default=REGIOES)
lista_ufs = sorted(censos[censos["regiao"].isin(regioes)]["uf"].unique())
ufs = st.sidebar.multiselect("UF", lista_ufs, default=lista_ufs)
anos = sorted(censos["ano"].unique())
ano_inicio, ano_fim = st.sidebar.select_slider("Anos de Censo", options=anos, value=(2010, 2022))
lista_faixas = piramide.sort_values("idade_inicial")["faixa_etaria"].unique()
faixas = st.sidebar.multiselect("Faixa etária (pirâmide)", lista_faixas, default=lista_faixas)

if ano_inicio == ano_fim:
    st.warning("Escolha dois anos diferentes.")
    st.stop()

# Cálculo do crescimento de cada município entre os dois anos escolhidos
censos_filtrados = censos[censos["uf"].isin(ufs)]
inicio = censos_filtrados[censos_filtrados["ano"] == ano_inicio]
fim = censos_filtrados[censos_filtrados["ano"] == ano_fim]

# O merge só mantém municípios que existiam nos dois anos
cidades = inicio.merge(fim[["cod_municipio", "populacao"]], on="cod_municipio",
                       suffixes=("_inicio", "_fim"))
anos_passados = ano_fim - ano_inicio

# Crescimento acumulado (%) = (população final / população inicial - 1) x 100
cidades["crescimento"] = 100 * (cidades["populacao_fim"] / cidades["populacao_inicio"] - 1)
# Taxa anual (%) = (população final / população inicial) ^ (1 / anos) - 1
cidades["taxa_anual"] = 100 * ((cidades["populacao_fim"] / cidades["populacao_inicio"])
                               ** (1 / anos_passados) - 1)
cidades = cidades.merge(envelhecimento[["cod_municipio", "indice_envelhecimento",
                                        "idade_mediana"]], on="cod_municipio", how="left")

if cidades.empty:
    st.warning("Não há municípios para esses filtros.")
    st.stop()

st.caption(f"De {ano_inicio} a {ano_fim} ({anos_passados} anos). Entram só os municípios que "
           f"já existiam em {ano_inicio}: {len(cidades)} municípios.")

# Indicadores principais (pergunta 1)
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"População em {ano_fim}", formatar(cidades["populacao_fim"].sum(), 0))
c2.metric("Crescimento médio por cidade", formatar(cidades["crescimento"].mean()) + "%")
c3.metric("Mediana por cidade", formatar(cidades["crescimento"].median()) + "%")
c4.metric("Cidades que perderam população",
          formatar(100 * (cidades["crescimento"] < 0).mean()) + "%")

aba1, aba2, aba3, aba4 = st.tabs(["Capitais e projeção", "Outliers e estatística", "Mapa",
                                  "Pirâmide etária"])

# Capitais e projeção
with aba1:
    capitais = cidades[cidades["capital"]].sort_values("crescimento", ascending=False)
    capitais["grupo"] = np.where(capitais["cod_municipio"].isin(CIDADES_DAS_PERSONAS),
                                 "Cidades dos clientes", "Outras capitais")
    grafico = px.bar(capitais, x="municipio", y="crescimento", color="grupo", text_auto=".1f",
                     color_discrete_map={"Cidades dos clientes": "#e76f51",
                                         "Outras capitais": "#c9ccd1"},
                     labels={"crescimento": "Crescimento acumulado (%)", "municipio": "",
                             "grupo": ""},
                     title=f"Crescimento das capitais de {ano_inicio} a {ano_fim}")
    grafico.update_xaxes(categoryorder="array", categoryarray=capitais["municipio"],
                         tickangle=-45)
    st.plotly_chart(grafico, width="stretch")

    # Projeção: supõe que a cidade continue crescendo na mesma taxa anual
    # População(ano) = População(ano_fim) x (1 + taxa) ^ (ano - ano_fim)
    linhas = []
    for codigo, nome in CIDADES_DAS_PERSONAS.items():
        historia = censos[censos["cod_municipio"] == codigo]
        for _, linha in historia.iterrows():
            linhas.append({"cidade": nome, "ano": linha["ano"], "populacao": linha["populacao"],
                           "tipo": "Censo"})

        cidade = cidades[cidades["cod_municipio"] == codigo]
        if cidade.empty:
            continue
        populacao_final = cidade["populacao_fim"].iloc[0]
        taxa = cidade["taxa_anual"].iloc[0] / 100
        for ano in [ano_fim, 2025, 2030, 2035, 2040]:
            if ano >= ano_fim:
                linhas.append({"cidade": nome, "ano": ano, "tipo": "Projeção",
                               "populacao": populacao_final * (1 + taxa) ** (ano - ano_fim)})

    grafico = px.line(pd.DataFrame(linhas), x="ano", y="populacao", color="cidade",
                      line_dash="tipo", markers=True,
                      labels={"populacao": "População", "ano": "Ano", "cidade": "Cidade",
                              "tipo": "Dado"},
                      title="População nos censos e projeção até 2040")
    grafico.update_layout(height=520, legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(grafico, width="stretch")
    st.caption("A projeção foi calculada por nós, não é um dado do IBGE. Ela usa a taxa anual "
               f"de {ano_inicio} a {ano_fim} e supõe que esse ritmo continue igual.")

    tabela = cidades[cidades["cod_municipio"].isin(CIDADES_DAS_PERSONAS)]
    tabela = tabela[["municipio", "populacao_inicio", "populacao_fim", "crescimento",
                     "taxa_anual", "indice_envelhecimento", "idade_mediana"]]
    tabela.columns = ["Cidade", f"População {ano_inicio}", f"População {ano_fim}",
                      "Crescimento (%)", "Taxa anual (%)", "Índice de envelhecimento",
                      "Idade mediana"]
    st.dataframe(tabela.round(2), hide_index=True, width="stretch")
    st.caption("Índice de envelhecimento: quantos idosos (65+) existem para cada 100 jovens "
               "(0 a 14 anos), no Censo 2022.")

# Outliers (pergunta 2)
with aba2:
    st.write(f"Cada ponto é um município. A medida é o crescimento de {ano_inicio} a {ano_fim}.")
    est = mostrar_estatisticas(cidades, "crescimento", "Crescimento acumulado (%)", "regiao")
    if est:
        encolheram, cresceram = achar_outliers(cidades, "crescimento", est)
        colunas = ["municipio", "uf", "populacao_inicio", "populacao_fim", "crescimento"]
        esquerda, direita = st.columns(2)
        esquerda.markdown("**Cresceram demais (acima do limite)**")
        esquerda.dataframe(cresceram[colunas].head(15).round(1), hide_index=True)
        direita.markdown("**Encolheram demais (abaixo do limite)**")
        direita.dataframe(encolheram[colunas].head(15).round(1), hide_index=True)

# Mapa
with aba3:
    with open("data/geo/uf.json", encoding="utf-8") as f:
        mapa_estados = json.load(f)

    por_estado = cidades.groupby("uf", as_index=False)[["populacao_inicio", "populacao_fim"]].sum()
    por_estado["crescimento"] = 100 * (por_estado["populacao_fim"] /
                                       por_estado["populacao_inicio"] - 1)
    mapa = px.choropleth(por_estado, geojson=mapa_estados, locations="uf",
                         featureidkey="properties.sigla", color="crescimento",
                         color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                         labels={"crescimento": "Crescimento (%)"},
                         title=f"Crescimento por estado, {ano_inicio} a {ano_fim}")
    mapa.update_geos(fitbounds="locations", visible=False)
    mapa.update_layout(height=520)
    st.plotly_chart(mapa, width="stretch")

    estado_mapa = st.selectbox("Ver os municípios de um estado", sorted(cidades["uf"].unique()),
                               index=sorted(cidades["uf"].unique()).index("PR")
                               if "PR" in cidades["uf"].values else 0)
    with open(f"data/geo/mun_{CODIGO_DO_ESTADO[estado_mapa]}.json", encoding="utf-8") as f:
        mapa_municipios = json.load(f)

    do_estado = cidades[cidades["uf"] == estado_mapa]
    mapa = px.choropleth(do_estado, geojson=mapa_municipios, locations="cod_municipio",
                         featureidkey="properties.id", color="crescimento",
                         hover_name="municipio", range_color=(-30, 60),
                         color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                         labels={"crescimento": "Crescimento (%)"},
                         title=f"Crescimento dos municípios de {estado_mapa}")
    mapa.update_geos(fitbounds="locations", visible=False)
    mapa.update_layout(height=560)
    st.plotly_chart(mapa, width="stretch")
    st.caption("A escala de cor vai de -30% a +60% para os outliers não apagarem as outras "
               "cores. O valor certo aparece ao passar o mouse.")

# Pirâmide etária
with aba4:
    pessoas = piramide[piramide["uf"].isin(ufs)]
    pessoas = pessoas.groupby(["faixa_etaria", "idade_inicial", "sexo"],
                              as_index=False)["populacao"].sum()
    pessoas["pct"] = 100 * pessoas["populacao"] / pessoas["populacao"].sum()
    pessoas = pessoas[pessoas["faixa_etaria"].isin(faixas)].sort_values("idade_inicial")

    # Homens ficam com valor negativo para aparecerem do lado esquerdo
    pessoas["lado"] = np.where(pessoas["sexo"] == "Homens", -pessoas["pct"], pessoas["pct"])
    grafico = px.bar(pessoas, x="lado", y="faixa_etaria", color="sexo", orientation="h",
                     color_discrete_map={"Homens": "#1565c0", "Mulheres": "#c2185b"},
                     hover_data={"lado": False, "pct": ":.2f"},
                     labels={"lado": "% da população", "faixa_etaria": "Faixa etária",
                             "pct": "% da população", "sexo": ""},
                     title="Pirâmide etária, Censo 2022")
    grafico.update_layout(barmode="relative", height=560)
    grafico.update_xaxes(tickvals=[-6, -4, -2, 0, 2, 4, 6],
                         ticktext=["6", "4", "2", "0", "2", "4", "6"])
    st.plotly_chart(grafico, width="stretch")
    st.caption("A pirâmide só existe para 2022 (tabela 9514).")

mostrar_noticias(
    [
        ("De 2010 a 2022, população brasileira cresce 6,5% e chega a 203,1 milhões",
         "Agência IBGE",
         "https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/"
         "noticias/37237-de-2010-a-2022-populacao-brasileira-cresce-6-5-e-chega-a-203-1-milhoes"),
        ("Censo 2022: número de pessoas com 65 anos ou mais de idade cresceu 57,4% em 12 anos",
         "Agência IBGE",
         "https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/"
         "noticias/38186-censo-2022-numero-de-pessoas-com-65-anos-ou-mais-de-idade-cresceu-57-4-"
         "em-12-anos"),
        ("População do país vai parar de crescer em 2041", "Agência IBGE",
         "https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/"
         "noticias/41056-populacao-do-pais-vai-parar-de-crescer-em-2041"),
    ],
    [("curitiba.jpg", "Curitiba (PR)"),
     ("sao_paulo_aerea.jpg", "Expansão urbana: vista aérea de São Paulo")],
)
