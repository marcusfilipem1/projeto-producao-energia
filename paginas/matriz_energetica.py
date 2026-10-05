import streamlit as st

from src.analise import crescimento_por_fonte, serie_anual
from src.dados import formatar_numero, formatar_pct, participacao, percentual_renovavel
from src.graficos import barras_fonte, linha_renovavel, matriz_100, pizza_matriz
from src.ui import cabecalho, contexto, grafico, interpretacao, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Fontes e matriz energética",
          "Quais fontes predominam? Houve crescimento da renovável? Há redução da dependência hidrelétrica?")
resumo_filtro(len(df_filtrado), len(df))

fontes = participacao(df_filtrado)
c1, c2, c3 = st.columns(3)
c1.metric("Fonte predominante", str(fontes.iloc[0]["fonte_energia"]),
          delta=f"{formatar_pct(fontes.iloc[0]['participacao'])} da produção", delta_color="off", delta_arrow="off",
          border=True)
c2.metric("Participação renovável", formatar_pct(percentual_renovavel(df_filtrado)), border=True)
fossil = fontes.loc[fontes["fonte_energia"] == "Termelétrica", "participacao"]
c3.metric("Participação fóssil (termelétrica)", formatar_pct(fossil.iloc[0]) if len(fossil) else "—", border=True)

col_a, col_b = st.columns([1.2, 1])
with col_a:
    grafico(barras_fonte(df_filtrado))
with col_b:
    visao = st.segmented_control("Agrupar a rosca por", ["Fonte", "Classe"], default="Fonte", key="pizza_por") or "Fonte"
    grafico(pizza_matriz(df_filtrado, "fonte_energia" if visao == "Fonte" else "classe_fonte"))

ranking = ", ".join(f"{r.fonte_energia} ({formatar_pct(r.participacao)})" for r in fontes.itertuples())
interpretacao(
    f"Ranking da matriz no recorte: {ranking}. A hidrelétrica sozinha produz mais que a soma de termelétrica e eólica. "
    "Classificando nuclear corretamente como não renovável, as renováveis ficam um pouco abaixo do que o campo "
    "`percentual_renovavel` do CSV sugere."
)

if df_filtrado["ano"].nunique() < 2:
    st.info("Selecione pelo menos dois anos para ver a evolução da matriz.")
    st.stop()

st.subheader("Como a matriz evoluiu?")
grafico(matriz_100(df_filtrado))

anual = serie_anual(df_filtrado)
col_c, col_d = st.columns([1.2, 1])
with col_c:
    grafico(linha_renovavel(anual))
with col_d:
    ini, fim = anual.iloc[0], anual.iloc[-1]
    st.metric(f"Renovável {int(ini['ano'])} → {int(fim['ano'])}",
              f"{formatar_pct(ini['renovavel_pct'])} → {formatar_pct(fim['renovavel_pct'])}",
              delta=f"{formatar_numero(fim['renovavel_pct'] - ini['renovavel_pct'], 2)} p.p.", border=True)
    st.metric(f"Hidrelétrica {int(ini['ano'])} → {int(fim['ano'])}",
              f"{formatar_pct(ini['hidreletrica_pct'])} → {formatar_pct(fim['hidreletrica_pct'])}",
              delta=f"{formatar_numero(fim['hidreletrica_pct'] - ini['hidreletrica_pct'], 2)} p.p.",
              delta_color="inverse", border=True,
              help="Queda na participação hidrelétrica = menor dependência (por isso a cor invertida).")
    renov_abs = df_filtrado[df_filtrado["renovavel"]].groupby("ano")["producao_mwh"].sum()
    if len(renov_abs) >= 2:
        st.metric("Produção renovável no período",
                  f"{formatar_numero(renov_abs.iloc[0] / 1e6, 1)} → {formatar_numero(renov_abs.iloc[-1] / 1e6, 1)} TWh",
                  delta=formatar_pct((renov_abs.iloc[-1] / renov_abs.iloc[0] - 1) * 100), border=True)

st.markdown("**Crescimento por fonte**")
crescimento = crescimento_por_fonte(df_filtrado)
st.dataframe(
    crescimento, hide_index=True,
    column_config={c: st.column_config.NumberColumn(format="%.2f") for c in crescimento.columns if c != "Fonte"}
    | {"Variação (p.p.)": st.column_config.NumberColumn(format="%+.2f"),
       "Crescimento anual (%)": st.column_config.NumberColumn(format="%.2f%%")},
)

mais_rapida = crescimento.iloc[0]
delta_hidro = fim["hidreletrica_pct"] - ini["hidreletrica_pct"]
delta_renov = fim["renovavel_pct"] - ini["renovavel_pct"]
texto_renov = (
    f"Em volume, a energia renovável **cresceu** {formatar_pct((renov_abs.iloc[-1] / renov_abs.iloc[0] - 1) * 100)} no período. "
    f"Em participação, porém, ficou praticamente estável ({formatar_numero(delta_renov, 2)} p.p.), porque todas as fontes "
    "cresceram em ritmo parecido. "
    if len(renov_abs) >= 2 else "O recorte não inclui fontes renováveis. "
)
interpretacao(
    texto_renov
    + f"A fonte que mais cresceu foi **{mais_rapida['Fonte']}** "
    f"({formatar_pct(mais_rapida['Crescimento anual (%)'], 2)} ao ano). A participação hidrelétrica variou "
    f"{formatar_numero(delta_hidro, 2)} p.p.: "
    + ("**não houve redução relevante da dependência hidrelétrica**." if abs(delta_hidro) < 1
       else "houve redução da dependência hidrelétrica." if delta_hidro < 0 else "a dependência hidrelétrica aumentou.")
)
