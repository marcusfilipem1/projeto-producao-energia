import pandas as pd
import streamlit as st

from src.banco import CONSULTAS, executar_consulta
from src.graficos import CMAP_SEQUENCIAL
from src.ui import cabecalho, contexto, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Explorar dados e SQL", "Tabela dinâmica, consultas SQL no banco SQLite e a base filtrada para download.")
resumo_filtro(len(df_filtrado), len(df))

aba_pivot, aba_sql, aba_base = st.tabs(["Tabela dinâmica", "Consulta SQL", "Base filtrada"])

# ---------------------------------------------------------------- Tabela dinâmica
DIMENSOES = {
    "Ano": "ano", "Mês": "nome_mes", "Trimestre": "trimestre", "Período hidrológico": "periodo_hidrologico",
    "Região": "regiao", "Estado": "uf", "Fonte de energia": "fonte_energia", "Classe da fonte": "classe_fonte",
    "Nível de demanda": "nivel_demanda",
}
METRICAS = {
    "Produção (TWh)": ("producao_mwh", "sum", 1e6),
    "Consumo (TWh)": ("consumo_mwh", "sum", 1e6),
    "Saldo (TWh)": ("saldo_mwh", "sum", 1e6),
    "Emissão de CO₂ (Mt)": ("emissao_co2", "sum", 1e6),
    "Participação na produção (%)": None,
    "Custo médio (R$/MWh)": ("custo_medio_mwh", "mean", 1),
    "Consumo ÷ produção (média)": ("indice_demanda", "mean", 1),
    "Número de registros": ("producao_mwh", "size", 1),
}

with aba_pivot:
    c1, c2, c3 = st.columns(3)
    linhas = c1.selectbox("Linhas", list(DIMENSOES), index=6)
    colunas = c2.selectbox("Colunas", ["(nenhuma)"] + list(DIMENSOES), index=1)
    metrica = c3.selectbox("Métrica", list(METRICAS))

    indices = [DIMENSOES[linhas]]
    if colunas != "(nenhuma)" and DIMENSOES[colunas] != DIMENSOES[linhas]:
        indices.append(DIMENSOES[colunas])

    if METRICAS[metrica] is None:
        soma = df_filtrado.groupby(indices, observed=True)["producao_mwh"].sum()
        total = soma.groupby(level=1, observed=True).transform("sum") if len(indices) == 2 else soma.sum()
        valores = soma / total * 100
    else:
        coluna, funcao, escala = METRICAS[metrica]
        valores = df_filtrado.groupby(indices, observed=True)[coluna].agg(funcao) / escala

    pivot = valores.unstack() if len(indices) == 2 else valores.to_frame(metrica)
    pivot.index = pivot.index.astype(str)
    pivot.columns = pivot.columns.astype(str)
    casas = 0 if metrica.startswith("Número") else 3 if "÷" in metrica else 2
    st.dataframe(
        pivot.style.format(lambda v: "" if pd.isna(v) else f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", "."))
        .background_gradient(cmap=CMAP_SEQUENCIAL, axis=None),
        height=min(38 * (len(pivot) + 1), 600),
    )
    st.caption(
        "Com duas dimensões, a participação (%) é calculada dentro de cada coluna (cada coluna soma 100%). "
        "Tons mais escuros indicam valores maiores."
    )
    st.download_button("Baixar tabela dinâmica (CSV)", pivot.to_csv(sep=";", decimal=",").encode("utf-8-sig"),
                       file_name="tabela_dinamica_energia.csv", mime="text/csv", icon=":material/download:")

# ---------------------------------------------------------------- SQL
with aba_sql:
    st.markdown(
        """
O tratamento gera um banco **SQLite** normalizado com **SQLAlchemy ORM** (`database/producao_energia.sqlite`),
combinando o CSV com a tabela de estados obtida da API do IBGE:

`regioes (1) ── (N) estados (1) ── (N) medicoes (N) ── (1) fontes_energia`

O banco contém a **base completa tratada** (os filtros da barra lateral não se aplicam aqui) e é aberto em
modo somente leitura: experimente editar a consulta.
"""
    )
    escolha = st.selectbox("Consulta pronta", list(CONSULTAS))
    sql = st.text_area("SQL", CONSULTAS[escolha].strip(), height=230, key=f"sql_{escolha}")
    try:
        resultado = executar_consulta(ctx["engine"], sql)
        st.dataframe(resultado, hide_index=True)
        st.caption(f"{len(resultado)} linha(s) retornada(s).")
    except Exception as erro:  # erro de sintaxe ou tentativa de escrita no banco somente leitura
        st.error(f"Não foi possível executar a consulta: {erro.__class__.__name__}. {str(erro).splitlines()[0]}")

# ---------------------------------------------------------------- Base filtrada
with aba_base:
    colunas_base = [
        "data", "regiao", "uf", "fonte_energia", "classe_fonte", "producao_mwh", "consumo_mwh", "saldo_mwh",
        "capacidade_instalada", "emissao_co2", "custo_medio_mwh", "nivel_demanda",
    ]
    st.dataframe(
        df_filtrado[colunas_base], hide_index=True, height=520,
        column_config={
            "data": st.column_config.DateColumn("Mês", format="MM/YYYY"),
            "producao_mwh": st.column_config.NumberColumn("Produção (MWh)", format="localized"),
            "consumo_mwh": st.column_config.NumberColumn("Consumo (MWh)", format="localized"),
            "saldo_mwh": st.column_config.NumberColumn("Saldo (MWh)", format="localized"),
            "capacidade_instalada": st.column_config.NumberColumn("Capacidade", format="localized"),
            "emissao_co2": st.column_config.NumberColumn("CO₂ (t)", format="localized"),
            "custo_medio_mwh": st.column_config.NumberColumn("Custo (R$/MWh)", format="%.2f"),
        },
    )
    st.download_button(
        "Baixar base filtrada (CSV)", df_filtrado[colunas_base].to_csv(index=False).encode("utf-8-sig"),
        file_name="producao_energia_filtrada.csv", mime="text/csv", icon=":material/download:",
    )
