# Baixa as tabelas do IBGE (SIDRA) e salva as bases limpas em data/processed

import json
import os
import urllib.request

import pandas as pd

PASTA_BRUTOS = "data/raw/"
PASTA_TRATADOS = "data/processed/"
SIDRA = "https://apisidra.ibge.gov.br/values"

# O primeiro dígito do código IBGE diz a região e os dois primeiros dizem o estado
REGIOES = {"1": "Norte", "2": "Nordeste", "3": "Sudeste", "4": "Sul", "5": "Centro-Oeste"}
ESTADOS = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
# Códigos IBGE das 27 capitais
CAPITAIS = [
    "1100205", "1200401", "1302603", "1400100", "1501402", "1600303", "1721000",
    "2111300", "2211001", "2304400", "2408102", "2507507", "2611606", "2704302",
    "2800308", "2927408", "3106200", "3205309", "3304557", "3550308", "4106902",
    "4205407", "4314902", "5002704", "5103403", "5208707", "5300108",
]


def baixar_tabela(nome, consulta):
    arquivo = PASTA_BRUTOS + nome + ".json"

    # Só baixa se ainda não tiver baixado antes
    if not os.path.exists(arquivo):
        print("Baixando", nome)
        pedido = urllib.request.Request(SIDRA + consulta, headers={"User-Agent": "Mozilla/5.0"})
        resposta = urllib.request.urlopen(pedido, timeout=180).read()
        with open(arquivo, "wb") as f:
            f.write(resposta)

    with open(arquivo, encoding="utf-8") as f:
        dados = json.load(f)

    # A primeira linha do SIDRA é o cabeçalho com os nomes das colunas
    tabela = pd.DataFrame(dados[1:]).rename(columns=dados[0])

    # Quando não tem dado o IBGE coloca "-", ".." ou "X"; isso vira vazio
    tabela["Valor"] = pd.to_numeric(tabela["Valor"], errors="coerce")
    return tabela


def colocar_estado_e_regiao(tabela, coluna_codigo):
    codigo = tabela[coluna_codigo].astype(str)
    tabela["uf"] = codigo.str[:2].map(ESTADOS)
    tabela["regiao"] = codigo.str[0].map(REGIOES)
    return tabela


def limpar_nome_municipio(nomes):
    # "Curitiba - PR" vira "Curitiba"
    return nomes.str.replace(r" - [A-Z]{2}$", "", regex=True)


def salvar(tabela, nome):
    tabela.to_csv(PASTA_TRATADOS + nome, index=False, encoding="utf-8-sig")
    print("Salvo", nome, "-", len(tabela), "linhas")


def gerar_curso_superior():
    # Tabela 10061 (Censo 2022): pessoas por nível de instrução
    # Pego só "Total" e "Superior completo" para calcular a porcentagem

    # Por estado, separando sexo e faixa etária
    faixas = "2793,1144,1145,1146,1147,1148,1149,1150,1151,1152,1153,1154,1155,2503,95253"
    estados = baixar_tabela(
        "10061_uf",
        "/t/10061/n3/all/v/2667/p/last%201/c2/all/c58/" + faixas + "/c86/all/c1568/120704,99713")
    estados = estados.rename(columns={
        "Unidade da Federação (Código)": "codigo", "Sexo": "sexo",
        "Grupo de idade": "faixa_etaria", "Cor ou raça": "cor_raca",
        "Nível de instrução": "nivel"})
    estados = colocar_estado_e_regiao(estados, "codigo")

    # Cada nível vira uma coluna
    estados = estados.pivot_table(index=["uf", "regiao", "sexo", "faixa_etaria", "cor_raca"],
                                  columns="nivel", values="Valor", aggfunc="sum").reset_index()
    estados = estados.rename(columns={"Total": "pop_18_mais",
                                      "Superior completo": "superior_completo"})
    salvar(estados, "curso_superior_uf.csv")

    # Por município, só pessoas de 25 anos ou mais
    municipios = baixar_tabela(
        "10061_mun",
        "/t/10061/n6/all/v/2667/p/last%201/c2/all/c58/108866/c86/95251/c1568/120704,99713")
    municipios = municipios.rename(columns={"Município (Código)": "cod_municipio",
                                            "Município": "nome", "Sexo": "sexo",
                                            "Nível de instrução": "nivel"})
    municipios = colocar_estado_e_regiao(municipios, "cod_municipio")
    municipios = municipios.pivot_table(index=["cod_municipio", "nome", "uf", "regiao", "sexo"],
                                        columns="nivel", values="Valor",
                                        aggfunc="sum").reset_index()
    municipios = municipios.rename(columns={"Total": "pop_25_mais",
                                            "Superior completo": "superior_completo"})
    municipios["municipio"] = limpar_nome_municipio(municipios["nome"])
    municipios["pct_superior"] = 100 * municipios["superior_completo"] / municipios["pop_25_mais"]
    salvar(municipios.drop(columns="nome"), "curso_superior_municipios.csv")

    # Tabela 7267 (PNAD Contínua): % com superior completo de 2016 em diante
    pnad = baixar_tabela("7267_uf", "/t/7267/n1/all/n3/all/v/all/p/all/c2/all/c1568/all")
    pnad = pnad[pnad["Variável"].str.startswith("Distribuição percentual")]
    pnad = pnad[pnad["Nível de instrução"] == "Superior completo"]
    pnad = pnad.rename(columns={"Brasil e Unidade da Federação (Código)": "codigo",
                                "Ano": "ano", "Sexo": "sexo", "Valor": "pct_superior"})
    pnad = colocar_estado_e_regiao(pnad, "codigo")
    pnad.loc[pnad["codigo"] == "1", "uf"] = "BR"  # código 1 é o Brasil inteiro
    pnad["ano"] = pnad["ano"].astype(int)
    salvar(pnad[["ano", "uf", "sexo", "pct_superior"]], "superior_historico_pnad.csv")


def gerar_crescimento():
    # Tabela 4709: população 2022 e variação desde 2010
    # Tabela 9515: índice de envelhecimento e idade mediana
    populacao = baixar_tabela("4709_mun", "/t/4709/n6/all/v/93,5936,10605/p/last%201")
    envelhecimento = baixar_tabela("9515_mun", "/t/9515/n6/all/v/10612,10613/p/last%201")
    juntas = pd.concat([populacao, envelhecimento])
    juntas = juntas.rename(columns={"Município (Código)": "cod_municipio", "Município": "nome"})

    # Cada variável vira uma coluna
    municipios = juntas.pivot_table(index=["cod_municipio", "nome"], columns="Variável",
                                    values="Valor", aggfunc="first").reset_index()
    municipios = municipios.rename(columns={
        "População residente": "pop_2022",
        "Variação absoluta da população residente 2010 compatibilizada": "variacao",
        "Taxa de crescimento geométrico": "taxa_crescimento",
        "Índice de envelhecimento": "indice_envelhecimento",
        "Idade mediana": "idade_mediana"})
    municipios = colocar_estado_e_regiao(municipios, "cod_municipio")
    municipios["municipio"] = limpar_nome_municipio(municipios["nome"])
    municipios["capital"] = municipios["cod_municipio"].isin(CAPITAIS)
    municipios["pop_2010"] = municipios["pop_2022"] - municipios["variacao"]
    salvar(municipios[["cod_municipio", "municipio", "uf", "regiao", "capital", "pop_2010",
                       "pop_2022", "taxa_crescimento", "indice_envelhecimento",
                       "idade_mediana"]], "crescimento_municipios.csv")

    # Tabela 202: população de cada município nos censos de 1970 a 2010
    censos = baixar_tabela("202_mun", "/t/202/n6/all/v/93/p/all")
    censos = censos.rename(columns={"Município (Código)": "cod_municipio", "Ano": "ano",
                                    "Valor": "populacao"})
    censos = censos[["cod_municipio", "ano", "populacao"]]

    # Junto o Censo 2022, que veio da tabela 4709
    censo_2022 = municipios[["cod_municipio", "pop_2022"]].rename(columns={"pop_2022": "populacao"})
    censo_2022["ano"] = 2022
    censos = pd.concat([censos, censo_2022])
    censos["ano"] = censos["ano"].astype(int)
    censos = censos.merge(municipios[["cod_municipio", "municipio", "uf", "regiao", "capital"]],
                          on="cod_municipio")
    censos = censos.dropna(subset=["populacao"])
    salvar(censos, "populacao_censos.csv")

    # Tabela 9514: população por sexo e faixa de idade (pirâmide etária)
    faixas = ("93070,93084,93085,93086,93087,93088,93089,93090,93091,93092,93093,"
              "93094,93095,93096,93097,93098,49108,49109,60040,60041,6653")
    piramide = baixar_tabela("9514_uf",
                             "/t/9514/n3/all/v/93/p/last%201/c2/4,5/c286/113635/c287/" + faixas)
    piramide = piramide.rename(columns={"Unidade da Federação (Código)": "codigo",
                                        "Sexo": "sexo", "Idade": "faixa_etaria",
                                        "Valor": "populacao"})
    piramide = colocar_estado_e_regiao(piramide, "codigo")

    # Junto todo mundo com 80 anos ou mais em uma faixa só
    mais_de_80 = ["80 a 84 anos", "85 a 89 anos", "90 a 94 anos", "95 a 99 anos",
                  "100 anos ou mais"]
    piramide.loc[piramide["faixa_etaria"].isin(mais_de_80), "faixa_etaria"] = "80 anos ou mais"
    piramide = piramide.groupby(["uf", "regiao", "sexo", "faixa_etaria"],
                                as_index=False)["populacao"].sum()

    # Número do começo da faixa, para colocar as faixas em ordem
    piramide["idade_inicial"] = piramide["faixa_etaria"].str.extract(r"^(\d+)").astype(int)
    salvar(piramide.sort_values(["uf", "sexo", "idade_inicial"]), "piramide_uf.csv")


os.makedirs(PASTA_BRUTOS, exist_ok=True)
os.makedirs(PASTA_TRATADOS, exist_ok=True)
gerar_curso_superior()
gerar_crescimento()
print("Pronto!")
