import streamlit as st

from src.analise import resumo_sazonalidade, serie_anual, taxa_crescimento
from src.config import MESES
from src.dados import formatar_energia, formatar_numero, formatar_pct
from src.graficos import area_fontes, heatmap_sazonal, linha_producao_consumo, perfil_sazonal_fontes
from src.ui import cabecalho, contexto, grafico, interpretacao, mostrar, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Evolução e sazonalidade", "Como a produção evoluiu ao longo do tempo? Existe sazonalidade na geração?")
resumo_filtro(len(df_filtrado), len(df))

granularidade = st.segmented_control("Granularidade", ["Mensal", "Anual"], default="Mensal", key="granularidade") or "Mensal"
grafico(linha_producao_consumo(df_filtrado, granularidade))

if df_filtrado["ano"].nunique() >= 2:
    anual = serie_anual(df_filtrado)
    anos = int(anual["ano"].iloc[-1] - anual["ano"].iloc[0])
    cagr = taxa_crescimento(anual["producao_mwh"].iloc[0], anual["producao_mwh"].iloc[-1], anos)
    cagr_consumo = taxa_crescimento(anual["consumo_mwh"].iloc[0], anual["consumo_mwh"].iloc[-1], anos)
    variacao = (anual["producao_mwh"].iloc[-1] / anual["producao_mwh"].iloc[0] - 1) * 100
    maior = anual.loc[anual["crescimento_pct"].idxmax()]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Crescimento anual da produção", formatar_pct(cagr, 2), border=True,
              help="Taxa composta de crescimento anual (CAGR) entre o primeiro e o último ano do recorte.")
    c2.metric("Crescimento anual do consumo", formatar_pct(cagr_consumo, 2), border=True)
    c3.metric(f"Variação {anual['ano'].iloc[0]}–{anual['ano'].iloc[-1]}", formatar_pct(variacao), border=True)
    c4.metric("Maior salto anual", int(maior["ano"]), delta=formatar_pct(maior["crescimento_pct"]),
              delta_color="off", delta_arrow="off", border=True)

    interpretacao(
        f"A produção passou de {formatar_energia(anual['producao_mwh'].iloc[0])} para "
        f"{formatar_energia(anual['producao_mwh'].iloc[-1])}, um crescimento de {formatar_pct(cagr, 2)} ao ano, "
        f"enquanto o consumo cresceu {formatar_pct(cagr_consumo, 2)} ao ano. A expansão é regular, sem anos de queda: "
        "o sistema acompanha uma demanda que cresce de forma contínua."
    )

    grafico(area_fontes(df_filtrado))

    st.markdown("**Tabela anual**")
    tabela = anual[["ano", "producao_mwh", "consumo_mwh", "crescimento_pct", "media_movel_3a", "renovavel_pct"]].copy()
    for col in ["producao_mwh", "consumo_mwh", "media_movel_3a"]:
        tabela[col] = tabela[col] / 1e6
    st.dataframe(
        tabela, hide_index=True,
        column_config={
            "ano": st.column_config.NumberColumn("Ano", format="%d"),
            "producao_mwh": st.column_config.NumberColumn("Produção (TWh)", format="%.2f"),
            "consumo_mwh": st.column_config.NumberColumn("Consumo (TWh)", format="%.2f"),
            "crescimento_pct": st.column_config.NumberColumn("Crescimento (%)", format="%+.2f"),
            "media_movel_3a": st.column_config.NumberColumn("Média móvel 3 anos (TWh)", format="%.2f"),
            "renovavel_pct": st.column_config.NumberColumn("Renovável (%)", format="%.2f"),
        },
    )
else:
    st.info("Selecione pelo menos dois anos para ver crescimento e tendência.")

st.subheader("Existe sazonalidade?")
if df_filtrado["mes"].nunique() < 12:
    st.warning("A análise de sazonalidade precisa dos 12 meses. Selecione todos os meses no filtro.")
    st.stop()

s = resumo_sazonalidade(df_filtrado)
c1, c2, c3 = st.columns(3)
c1.metric("Amplitude sazonal", f"{formatar_numero(s['amplitude'], 1)}%", border=True,
          help="Diferença entre o mês mais forte e o mais fraco no índice sazonal médio.")
c2.metric("Mês mais forte / mais fraco", f"{MESES[s['mes_max'] - 1]} / {MESES[s['mes_min'] - 1]}", border=True)
c3.metric("Consistência entre anos", formatar_numero(s["consistencia"], 2), border=True,
          help="Correlação média entre o padrão mensal de cada ano e o dos demais. Perto de 1 = padrão que se repete; "
               "perto de 0 = oscilações aleatórias.")

mostrar(heatmap_sazonal(df_filtrado))
grafico(perfil_sazonal_fontes(df_filtrado))

texto = (
    f"O índice sazonal divide a produção de cada mês pela média mensal do mesmo ano, removendo o efeito do crescimento. "
    f"Os meses variam só {formatar_numero(s['amplitude'], 1)}% entre o mais forte e o mais fraco, e a consistência entre "
    f"anos é {formatar_numero(s['consistencia'], 2)}"
)
if s["consistencia"] < 0.3 and s["amplitude"] < 5:
    texto += (
        ": **não há sazonalidade relevante**. As oscilações mudam de mês para mês e não se repetem entre os anos. "
        "Em dados reais, hidrelétricas e eólicas costumam ter padrão sazonal forte (chuvas e ventos); esta base "
        "simulada não reproduz esse comportamento. A nuclear oscila mais que as outras fontes porque tem volumes "
        "pequenos e vários meses no piso de 100 MWh, o que amplia o ruído relativo."
    )
else:
    texto += ": há um padrão sazonal que se repete entre os anos."
interpretacao(texto)
