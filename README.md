# Números que Falam: Descobrindo o Brasil

Painel em Streamlit com dois indicadores do IBGE: Curso Superior (Caio) e População e
Crescimento Demográfico (Davi).

## Como rodar

Dentro da pasta do projeto:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Os dados já estão em `data/processed/`. Para gerar de novo: `python etl.py`
(para baixar tudo do IBGE outra vez, apague antes a pasta `data/raw/`).

## Arquivos

| Arquivo                     | O que faz                                                          |
| --------------------------- | ------------------------------------------------------------------ |
| `app.py`                  | Abre o painel e monta o menu com as telas                          |
| `funcoes.py`              | Estatísticas, upload de CSV/XLSX, boxplot, histograma e notícias |
| `etl.py`                  | Baixa as tabelas do SIDRA e salva as bases limpas                  |
| `telas/inicio.py`         | Nome da startup e da equipe                                        |
| `telas/curso_superior.py` | Indicador Curso Superior                                           |
| `telas/crescimento.py`    | Indicador Crescimento Demográfico                                 |
| `assets/`                 | Fotos com licença livre (créditos em `assets/creditos.json`)   |
| `data/geo/`               | Contornos dos estados e municípios para os mapas                  |

## Fontes (IBGE/SIDRA)

| Tabela | Pesquisa                                              | Usada em                    |
| ------ | ----------------------------------------------------- | --------------------------- |
| 10061  | Censo 2022: nível de instrução por sexo e idade    | Curso Superior              |
| 7267   | PNAD Contínua: nível de instrução, 2016 a 2025    | Curso Superior (evolução) |
| 4709   | Censo 2022: população e crescimento desde 2010      | Crescimento                 |
| 9515   | Censo 2022: índice de envelhecimento e idade mediana | Crescimento                 |
| 9514   | Censo 2022: população por sexo e idade              | Pirâmide etária           |
| 202    | Censos de 1970 a 2010: população por município     | Crescimento                 |

Os contornos dos mapas vêm da **Malha Municipal 2022 do IBGE** (arquivos `BR_UF_2022.zip` e
`BR_Municipios_2022.zip`, em geoftp.ibge.gov.br), convertidos para GeoJSON e com os contornos
simplificados (precisão de uns 200 m nos municípios) para o mapa carregar mais rápido.

## Limitações

1. A divisão por área (Exatas, Humanas, Saúde) está na tabela 10063, que não conseguimos
   baixar pela API. A tela aceita essa tabela por upload. O número de ingressantes não é do
   IBGE, é do INEP.
2. A projeção da população foi calculada por nós (crescimento geométrico), não é a oficial
   do IBGE.
3. A pirâmide etária só existe para 2022.
4. A PNAD conta pessoas de 14 anos ou mais e o Censo conta 25 ou mais, então os percentuais
   das duas pesquisas não podem ser comparados.
