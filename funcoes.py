# Funções que as duas telas usam: estatística, upload, gráficos e notícias
import json

import pandas as pd
import plotly.express as px
import streamlit as st

PASTA_DADOS = "data/processed/"
PASTA_IMAGENS = "assets/"

CORES_REGIOES = {"Norte": "#2a9d8f", "Nordeste": "#e9c46a", "Sudeste": "#e76f51",
                 "Sul": "#457b9d", "Centro-Oeste": "#8d6cab"}


# ---------------- Estatística ----------------

def calcular_estatisticas(valores):
    valores = valores.dropna()
    q1 = valores.quantile(0.25)
    q3 = valores.quantile(0.75)
    iqr = q3 - q1

    # Arredondo para 1 casa na moda porque com decimais quase nenhum valor se repete
    moda = valores.round(1).mode()[0]

    return {
        "quantidade": len(valores),
        "media": valores.mean(),
        "mediana": valores.median(),
        "moda": moda,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "minimo": valores.min(),
        "maximo": valores.max(),
        "amplitude": valores.max() - valores.min(),
        "variancia": valores.var(),
        "desvio_padrao": valores.std(),
        # Regra do 1,5 x IQR para achar outliers
        "limite_inferior": q1 - 1.5 * iqr,
        "limite_superior": q3 + 1.5 * iqr,
    }


def achar_outliers(tabela, coluna, est):
    abaixo = tabela[tabela[coluna] < est["limite_inferior"]]
    acima = tabela[tabela[coluna] > est["limite_superior"]]
    return abaixo.sort_values(coluna), acima.sort_values(coluna, ascending=False)


def formatar(numero, casas=1):
    # Formato brasileiro: 1.234,5
    texto = f"{numero:,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


# ---------------- Leitura dos dados ----------------

@st.cache_data
def ler_base(nome):
    return pd.read_csv(PASTA_DADOS + nome, dtype={"cod_municipio": str})


def ler_arquivo_enviado(arquivo):
    if arquivo.name.endswith(".xlsx"):
        return pd.read_excel(arquivo)

    # CSV do Excel brasileiro usa ; para separar e vírgula nos decimais
    primeira_linha = arquivo.getvalue().decode("latin-1").splitlines()[0]
    if ";" in primeira_linha:
        separador, decimal = ";", ","
    else:
        separador, decimal = ",", "."

    try:
        return pd.read_csv(arquivo, sep=separador, decimal=decimal, encoding="utf-8-sig")
    except UnicodeDecodeError:
        # CSV salvo pelo Excel no Windows usa outra codificação
        arquivo.seek(0)
        return pd.read_csv(arquivo, sep=separador, decimal=decimal, encoding="latin-1")


def upload_ou_base_padrao(texto, base_padrao, colunas_necessarias, chave):
    arquivo = st.sidebar.file_uploader(texto, type=["csv", "xlsx"], key=chave)

    # Sem arquivo enviado, usa a base do IBGE que já está tratada
    if arquivo is None:
        return ler_base(base_padrao)

    try:
        tabela = ler_arquivo_enviado(arquivo)
    except Exception:
        st.sidebar.error("Não foi possível ler o arquivo. Usando a base do IBGE.")
        return ler_base(base_padrao)

    faltando = [c for c in colunas_necessarias if c not in tabela.columns]
    if faltando:
        st.sidebar.error("Faltam as colunas: " + ", ".join(faltando) + ". Usando a base do IBGE.")
        return ler_base(base_padrao)

    if "cod_municipio" in tabela.columns:
        tabela["cod_municipio"] = tabela["cod_municipio"].astype(str)
    st.sidebar.success(f"Arquivo carregado com {len(tabela)} linhas")
    return tabela


# ---------------- Painel de estatística ----------------

def mostrar_estatisticas(tabela, coluna, nome_da_medida, coluna_grupo):
    if tabela[coluna].dropna().empty:
        st.warning("Não há dados para esses filtros.")
        return

    est = calcular_estatisticas(tabela[coluna])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Média", formatar(est["media"], 2) + "%")
    c2.metric("Mediana", formatar(est["mediana"], 2) + "%")
    c3.metric("IQR (Q3 - Q1)", formatar(est["iqr"], 2))
    c4.metric("Desvio padrão", formatar(est["desvio_padrao"], 2))

    esquerda, direita = st.columns([1, 1.4])

    with esquerda:
        medidas = pd.DataFrame({
            "Medida": ["Quantidade", "Média", "Mediana", "Moda", "Q1", "Q3", "IQR",
                       "Mínimo", "Máximo", "Amplitude", "Variância", "Desvio padrão",
                       "Limite inferior (outlier)", "Limite superior (outlier)"],
            "Valor": [est["quantidade"], est["media"], est["mediana"], est["moda"], est["q1"],
                      est["q3"], est["iqr"], est["minimo"], est["maximo"], est["amplitude"],
                      est["variancia"], est["desvio_padrao"], est["limite_inferior"],
                      est["limite_superior"]],
        })
        medidas["Valor"] = medidas["Valor"].apply(lambda v: formatar(v, 2))
        st.dataframe(medidas, hide_index=True, width="stretch")

    with direita:
        boxplot = px.box(tabela, x=coluna_grupo, y=coluna, color=coluna_grupo,
                         hover_name="municipio", color_discrete_map=CORES_REGIOES,
                         title="Boxplot", labels={coluna: nome_da_medida})
        boxplot.update_layout(showlegend=False, height=430)
        st.plotly_chart(boxplot, width="stretch")

    histograma = px.histogram(tabela, x=coluna, nbins=40, title="Histograma",
                              labels={coluna: nome_da_medida})
    histograma.add_vline(x=est["media"], line_dash="dash", line_color="red",
                         annotation_text="média")
    histograma.add_vline(x=est["mediana"], line_color="green", annotation_text="mediana",
                         annotation_position="top left")
    histograma.update_layout(yaxis_title="Quantidade de municípios", height=330)
    st.plotly_chart(histograma, width="stretch")

    # Interpretação: compara média e mediana e explica os outliers
    abaixo, acima = achar_outliers(tabela, coluna, est)
    media = formatar(est["media"], 2) + "%"
    mediana = formatar(est["mediana"], 2) + "%"

    st.markdown("**O que os números mostram**")
    if est["media"] > est["mediana"]:
        st.write(f"- A média ({media}) é maior que a mediana ({mediana}). Alguns municípios "
                 "com valores muito altos puxam a média para cima, então a mediana representa "
                 "melhor o município típico.")
    elif est["media"] < est["mediana"]:
        st.write(f"- A média ({media}) é menor que a mediana ({mediana}). Alguns municípios "
                 "com valores muito baixos puxam a média para baixo.")
    else:
        st.write(f"- A média e a mediana são iguais ({media}).")

    st.write(f"- Metade dos municípios fica entre {formatar(est['q1'], 2)}% e "
             f"{formatar(est['q3'], 2)}%.")
    st.write(f"- Pela regra do 1,5 × IQR, é outlier quem fica abaixo de "
             f"{formatar(est['limite_inferior'], 2)}% ou acima de "
             f"{formatar(est['limite_superior'], 2)}%. São {len(abaixo)} abaixo e "
             f"{len(acima)} acima, de {est['quantidade']} municípios.")
    return est


# ---------------- Notícias ----------------

def mostrar_noticias(noticias, imagens):
    st.divider()
    st.subheader("Notícias")

    with open(PASTA_IMAGENS + "creditos.json", encoding="utf-8") as f:
        creditos = json.load(f)

    colunas = st.columns(len(imagens))
    for coluna, (arquivo, legenda) in zip(colunas, imagens):
        credito = creditos[arquivo]
        coluna.image(PASTA_IMAGENS + arquivo, caption=legenda, width="stretch")
        coluna.caption(f"Foto: {credito['autor']} ({credito['licenca']}) - "
                       f"[Wikimedia Commons]({credito['pagina']})")

    for titulo, fonte, link in noticias:
        st.markdown(f"- [{titulo}]({link}) ({fonte})")
