import streamlit as st

from src.analise import calcular_kpis, classificar_correlacao, correlacao, taxa_crescimento
from src.dados import formatar_co2, formatar_numero, formatar_pct, somar
from src.graficos import dispersao_emissao, emissoes_anuais, matriz_correlacao, participacao_emissoes
from src.ui import cabecalho, contexto, grafico, interpretacao, mostrar, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Impacto ambiental", "Quanto CO₂ a geração emite e quais fontes concentram as emissões?")
resumo_filtro(len(df_filtrado), len(df))

k = calcular_kpis(df_filtrado)
por_fonte = somar(df_filtrado, "fonte_energia", ["producao_mwh", "emissao_co2"])
por_fonte["fonte_energia"] = por_fonte["fonte_energia"].astype(str)
por_fonte["fator_kg_mwh"] = por_fonte["emissao_co2"] / por_fonte["producao_mwh"] * 1000
por_fonte["pct_producao"] = por_fonte["producao_mwh"] / por_fonte["producao_mwh"].sum() * 100
por_fonte["pct_emissao"] = por_fonte["emissao_co2"] / por_fonte["emissao_co2"].sum() * 100
termica = por_fonte[por_fonte["fonte_energia"] == "Termelétrica"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Emissão total de CO₂", formatar_co2(k["emissao"]), border=True)
c2.metric("Intensidade de carbono", f"{formatar_numero(k['intensidade'] * 1000, 0)} kg/MWh", border=True,
          help="Emissão total ÷ produção total do recorte.")
c3.metric("CO₂ vindo da termelétrica", formatar_pct(termica["pct_emissao"].iloc[0]) if len(termica) else "—",
          delta=f"com {formatar_pct(termica['pct_producao'].iloc[0])} da produção" if len(termica) else None,
          delta_color="off", delta_arrow="off", border=True)
if df_filtrado["ano"].nunique() >= 2:
    anual = df_filtrado.groupby("ano")["emissao_co2"].sum()
    c4.metric("Crescimento anual das emissões",
              formatar_pct(taxa_crescimento(anual.iloc[0], anual.iloc[-1], int(anual.index[-1] - anual.index[0])), 2),
              border=True)

grafico(dispersao_emissao(df_filtrado))
interpretacao(
    "Cada ponto é um registro (estado, fonte e mês). Os pontos formam retas: a emissão é proporcional à produção, e a "
    "inclinação de cada reta é o fator de emissão da fonte. A termelétrica forma uma reta muito mais inclinada, enquanto "
    "as demais fontes ficam quase coladas ao eixo horizontal."
)

col_a, col_b = st.columns(2)
with col_a:
    grafico(participacao_emissoes(df_filtrado))
with col_b:
    if df_filtrado["ano"].nunique() >= 2:
        grafico(emissoes_anuais(df_filtrado))

st.markdown("**Fator de emissão por fonte**")
st.dataframe(
    por_fonte[["fonte_energia", "producao_mwh", "emissao_co2", "fator_kg_mwh", "pct_producao", "pct_emissao"]]
    .assign(producao_mwh=lambda d: d["producao_mwh"] / 1e6, emissao_co2=lambda d: d["emissao_co2"] / 1e6),
    hide_index=True,
    column_config={
        "fonte_energia": "Fonte",
        "producao_mwh": st.column_config.NumberColumn("Produção (TWh)", format="%.2f"),
        "emissao_co2": st.column_config.NumberColumn("CO₂ (Mt)", format="%.2f"),
        "fator_kg_mwh": st.column_config.NumberColumn("kg CO₂ por MWh", format="%.0f"),
        "pct_producao": st.column_config.NumberColumn("% da produção", format="%.2f"),
        "pct_emissao": st.column_config.NumberColumn("% das emissões", format="%.2f"),
    },
)
if len(termica):
    razao = termica["fator_kg_mwh"].iloc[0] / por_fonte.loc[por_fonte["fonte_energia"] != "Termelétrica", "fator_kg_mwh"].mean()
    interpretacao(
        f"A termelétrica emite {formatar_numero(termica['fator_kg_mwh'].iloc[0], 0)} kg de CO₂ por MWh, cerca de "
        f"**{formatar_numero(razao, 0)} vezes** o fator das demais fontes. Por isso, gerando "
        f"{formatar_pct(termica['pct_producao'].iloc[0])} da energia, ela responde por "
        f"**{formatar_pct(termica['pct_emissao'].iloc[0])} das emissões**. Reduzir a geração térmica é a alavanca mais "
        "eficaz para descarbonizar a matriz; expandir outras fontes sem reduzir a térmica não diminui as emissões totais."
    )

st.subheader("Correlações entre as variáveis")
metodo = (st.segmented_control("Método", ["Pearson", "Spearman"], default="Pearson", key="metodo_corr") or "Pearson").lower()
col_c, col_d = st.columns([1.1, 1])
with col_c:
    mostrar(matriz_correlacao(df_filtrado, metodo))
with col_d:
    r_custo = correlacao(df_filtrado["custo_medio_mwh"], df_filtrado["producao_mwh"], metodo)
    r_emissao = correlacao(df_filtrado["emissao_co2"], df_filtrado["producao_mwh"], metodo)
    custo = df_filtrado.groupby("fonte_energia", observed=True)["custo_medio_mwh"].mean()
    st.markdown(
        f"""
- **Emissão × produção:** r = {formatar_numero(r_emissao, 2)} ({classificar_correlacao(r_emissao)}). A relação existe, mas
  depende da fonte: dentro de cada fonte ela é perfeitamente proporcional.
- **Custo médio × produção:** r = {formatar_numero(r_custo, 3)} ({classificar_correlacao(r_custo)}). O custo por MWh não
  acompanha o volume produzido.
- **Custo médio por fonte:** de R\\$ {formatar_numero(custo.min(), 0)} a R\\$ {formatar_numero(custo.max(), 0)} por MWh.
  Na base simulada, o custo não diferencia as fontes (em dados reais, térmicas costumam ser mais caras).
- **Capacidade × produção:** correlação 1,00, porque a produção é sempre 71,4% da capacidade instalada (fator de
  capacidade constante na simulação).
"""
    )
