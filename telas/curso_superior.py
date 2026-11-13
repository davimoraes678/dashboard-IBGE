# Tela do indicador Curso Superior
# Dados: Censo 2022 (tabela 10061) e PNAD Contínua (tabela 7267)
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from funcoes import (achar_outliers, formatar, ler_base, mostrar_estatisticas, mostrar_noticias,
                     upload_ou_base_padrao)

ESTADOS_DAS_PERSONAS = ["MG", "ES", "SP", "PR", "MS"]
CORES_SEXO = {"Mulheres": "#c2185b", "Homens": "#1565c0"}

st.title("Curso Superior")
st.markdown("**Clientes:** Antônio (governador de MG), Ademir (ES), Claudinete (SP), "
            "Joana (PR) e Ana (MS). Eles querem atrair profissionais de alta qualificação.")
st.markdown("**Perguntas:**  \n"
            "1. Como a população com nível superior está distribuída nos estados?  \n"
            "2. Como essa taxa evoluiu ao longo dos anos?  \n"
            "3. Qual o percentual de mulheres diplomadas em Exatas e em Humanas?")

# Dados
st.sidebar.header("Curso Superior")
municipios = upload_ou_base_padrao(
    "Enviar base dos municípios (CSV ou XLSX)", "curso_superior_municipios.csv",
    ["municipio", "uf", "sexo", "superior_completo", "pop_25_mais"], "upload_curso")
municipios["pct_superior"] = 100 * municipios["superior_completo"] / municipios["pop_25_mais"]
por_estado = ler_base("curso_superior_uf.csv")
historico = ler_base("superior_historico_pnad.csv")

# Filtros da barra lateral
estados = st.sidebar.multiselect("Estados", sorted(municipios["uf"].unique()),
                                 default=ESTADOS_DAS_PERSONAS)
anos = sorted(historico["ano"].unique())
ano_inicio, ano_fim = st.sidebar.select_slider("Ano", options=anos, value=(anos[0], anos[-1]))
sexo = st.sidebar.radio("Sexo", ["Total", "Mulheres", "Homens"], horizontal=True)
area = st.sidebar.selectbox("Área do conhecimento", ["Todas", "Exatas", "Humanas", "Saúde"])

if not estados:
    st.warning("Escolha pelo menos um estado.")
    st.stop()

municipios_dos_estados = municipios[municipios["uf"].isin(estados)]
municipios_filtrados = municipios_dos_estados[municipios_dos_estados["sexo"] == sexo]


def porcentagem_com_superior(tabela):
    return 100 * tabela["superior_completo"].sum() / tabela["pop_25_mais"].sum()


# Indicadores principais
pct_estados = porcentagem_com_superior(municipios_filtrados)
pct_brasil = porcentagem_com_superior(municipios[municipios["sexo"] == sexo])

historico_estados = historico[historico["uf"].isin(estados) & (historico["sexo"] == sexo)]
pct_ano_inicio = historico_estados[historico_estados["ano"] == ano_inicio]["pct_superior"].mean()
pct_ano_fim = historico_estados[historico_estados["ano"] == ano_fim]["pct_superior"].mean()

diplomadas = municipios_dos_estados[municipios_dos_estados["sexo"] == "Mulheres"]["superior_completo"].sum()
diplomados = municipios_dos_estados[municipios_dos_estados["sexo"] == "Homens"]["superior_completo"].sum()
pct_mulheres = 100 * diplomadas / (diplomadas + diplomados)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Com superior completo (25+ anos)", formatar(pct_estados) + "%",
          formatar(pct_estados - pct_brasil) + " p.p. em relação ao Brasil")
c2.metric("Pessoas com diploma", formatar(municipios_filtrados["superior_completo"].sum(), 0))
c3.metric(f"Taxa em {ano_fim} (PNAD)", formatar(pct_ano_fim) + "%",
          formatar(pct_ano_fim - pct_ano_inicio) + f" p.p. desde {ano_inicio}")
c4.metric("Mulheres entre os diplomados", formatar(pct_mulheres) + "%")

aba1, aba2, aba3, aba4 = st.tabs(["Distribuição por estado", "Evolução", "Mulheres e áreas",
                                  "Estatística dos municípios"])

# Pergunta 1: ranking dos estados
with aba1:
    ranking = por_estado[(por_estado["sexo"] == sexo) & (por_estado["faixa_etaria"] == "Total")
                         & (por_estado["cor_raca"] == "Total")].copy()
    ranking["pct"] = 100 * ranking["superior_completo"] / ranking["pop_18_mais"]
    ranking["grupo"] = np.where(ranking["uf"].isin(estados), "Estados escolhidos", "Outros")
    ranking = ranking.sort_values("pct", ascending=False)
    media_brasil = 100 * ranking["superior_completo"].sum() / ranking["pop_18_mais"].sum()

    grafico = px.bar(ranking, x="uf", y="pct", color="grupo", text_auto=".1f",
                     color_discrete_map={"Estados escolhidos": "#e76f51", "Outros": "#c9ccd1"},
                     labels={"pct": "% com superior completo", "uf": "Estado", "grupo": ""},
                     title=f"% de pessoas com 18+ anos com superior completo ({sexo}), Censo 2022")
    grafico.add_hline(y=media_brasil, line_dash="dash",
                      annotation_text=f"Brasil: {formatar(media_brasil)}%")
    grafico.update_xaxes(categoryorder="array", categoryarray=ranking["uf"])
    st.plotly_chart(grafico, width="stretch")

# Pergunta 2: evolução ao longo dos anos
with aba2:
    periodo = historico[(historico["sexo"] == sexo) & (historico["ano"] >= ano_inicio)
                        & (historico["ano"] <= ano_fim)]
    linhas = periodo[periodo["uf"].isin(estados + ["BR"])].copy()
    linhas["uf"] = linhas["uf"].replace("BR", "Brasil")

    media_escolhidos = (periodo[periodo["uf"].isin(estados)]
                        .groupby("ano", as_index=False)["pct_superior"].mean())
    media_escolhidos["uf"] = "Média dos estados escolhidos"
    linhas = pd.concat([linhas, media_escolhidos])

    grafico = px.line(linhas, x="ano", y="pct_superior", color="uf", markers=True,
                      labels={"pct_superior": "% com superior completo (14+ anos)",
                              "ano": "Ano", "uf": ""},
                      title=f"Evolução da taxa de graduação ({sexo}), PNAD Contínua")
    st.plotly_chart(grafico, width="stretch")
    st.caption("A PNAD não tem dados de 2020 e 2021 nessa tabela. Ela conta pessoas de 14 anos "
               "ou mais, e o Censo conta 25 ou mais, por isso os números são diferentes.")

# Pergunta 3: mulheres entre os diplomados
with aba3:
    por_sexo = (municipios_dos_estados[municipios_dos_estados["sexo"] != "Total"]
                .groupby(["uf", "sexo"], as_index=False)["superior_completo"].sum())
    total = por_sexo.groupby("sexo", as_index=False)["superior_completo"].sum()
    total["uf"] = "TOTAL"
    por_sexo = pd.concat([por_sexo, total])
    soma_do_estado = por_sexo.groupby("uf")["superior_completo"].transform("sum")
    por_sexo["pct"] = 100 * por_sexo["superior_completo"] / soma_do_estado

    grafico = px.bar(por_sexo, x="uf", y="pct", color="sexo", text_auto=".1f",
                     color_discrete_map=CORES_SEXO,
                     labels={"pct": "% dos diplomados", "uf": "Estado", "sexo": ""},
                     title="Proporção de mulheres e homens entre os diplomados (25+ anos)")
    st.plotly_chart(grafico, width="stretch")

    st.markdown("**Mulheres por área do conhecimento**")
    arquivo_areas = st.file_uploader("Enviar tabela 10063 do SIDRA (colunas: uf, sexo, area, "
                                     "pessoas)", type=["csv", "xlsx"])
    if arquivo_areas is None:
        st.info("A divisão por área (Exatas, Humanas, Saúde) está na tabela 10063 do Censo "
                "2022: https://sidra.ibge.gov.br/tabela/10063. O IBGE só mede quem já se "
                "formou; o número de ingressantes é do INEP.")
    else:
        if arquivo_areas.name.endswith(".xlsx"):
            areas = pd.read_excel(arquivo_areas)
        else:
            areas = pd.read_csv(arquivo_areas, sep=None, engine="python")
        areas = areas[areas["uf"].isin(estados)]
        if area != "Todas":
            areas = areas[areas["area"] == area]
        areas = areas.groupby(["area", "sexo"], as_index=False)["pessoas"].sum()
        areas["pct"] = 100 * areas["pessoas"] / areas.groupby("area")["pessoas"].transform("sum")
        grafico = px.bar(areas, x="area", y="pct", color="sexo", text_auto=".1f",
                         color_discrete_map=CORES_SEXO,
                         labels={"pct": "% dos diplomados", "area": "Área", "sexo": ""},
                         title="Proporção de mulheres e homens por área")
        st.plotly_chart(grafico, width="stretch")

# Estatística dos municípios
with aba4:
    st.write(f"Cada ponto é um município. A medida é o % de pessoas com 25 anos ou mais que "
             f"têm superior completo ({sexo.lower()}).")
    est = mostrar_estatisticas(municipios_filtrados, "pct_superior", "% com superior completo",
                               "uf")
    if est:
        abaixo, acima = achar_outliers(municipios_filtrados, "pct_superior", est)
        st.markdown("**Municípios acima do limite (outliers)**")
        st.dataframe(acima[["municipio", "uf", "pct_superior"]].head(10).round(1),
                     hide_index=True, width="stretch")

mostrar_noticias(
    [
        ("Fuga de cérebros, a diáspora de cientistas brasileiros", "Agência Brasil, abr/2023",
         "https://agenciabrasil.ebc.com.br/geral/noticia/2023-04/"
         "fuga-de-cerebros-diaspora-de-cientistas-brasileiros"),
        ("Brasil tem baixa fuga de cérebro, com apenas 1,2% de doutores vivendo fora do país",
         "Ipea",
         "https://www.ipea.gov.br/portal/categorias/45-todas-as-noticias/noticias/16357-brasil-"
         "tem-baixa-fuga-de-cerebro-com-apenas-1-2-de-doutores-vivendo-fora-do-pais-aponta-estudo"),
        ("Déficit de profissionais de TI deve chegar a quase 800 mil em 2025",
         "Prefeitura de Salvador",
         "https://salvadortechreserva.salvador.ba.gov.br/deficit-de-profissionais-de-ti-deve-"
         "chegar-a-quase-800-mil-em-2025-apenas-no-brasil/"),
        ("Mulheres na TI: oportunidades e desafios", "Governo do Espírito Santo (Prodest)",
         "https://prodest.es.gov.br/mulheres-na-ti-oportunidades-e-desafios"),
        ("Brasil é o terceiro colocado na participação feminina na ciência",
         "Agência Brasil, mar/2024",
         "https://agenciabrasil.ebc.com.br/educacao/noticia/2024-03/"
         "brasil-e-o-terceiro-colocado-na-participacao-feminina-na-ciencia"),
        ("Mulheres são maioria na formação científica brasileira", "MEC, fev/2026",
         "https://www.gov.br/mec/pt-br/assuntos/noticias/2026/fevereiro/"
         "mulheres-sao-maioria-na-formacao-cientifica-brasileira"),
    ],
    [("laboratorio.jpg", "Pesquisadora em laboratório"),
     ("mulheres_ciencia.jpg", "Prêmio Mulheres na Ciência")],
)
