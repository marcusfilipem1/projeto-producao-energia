import streamlit as st

from src.dados import formatar_energia, formatar_numero, formatar_pct, somar
from src.graficos import barras_estado, barras_regiao, mapa_ufs
from src.ui import cabecalho, contexto, grafico, interpretacao, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Regiões e estados", "Quais regiões produzem mais energia? Quais estados possuem maior produção?")
resumo_filtro(len(df_filtrado), len(df))

st.subheader("Mapa interativo")
metrica = st.segmented_control("Colorir o mapa por", ["Produção", "Saldo", "Emissão de CO₂"], default="Produção",
                               key="metrica_mapa") or "Produção"
coluna = {"Produção": "producao_mwh", "Saldo": "saldo_mwh", "Emissão de CO₂": "emissao_co2"}[metrica]
grafico(mapa_ufs(df_filtrado, ctx["malha"], coluna))
st.caption(
    f"Contorno dos estados obtido da API de malhas do IBGE ({ctx['origens']['malha']}). "
    "Estados em cinza não fazem parte da base ou do recorte filtrado. Passe o mouse para ver produção, consumo e CO₂."
)

st.subheader("Ranking de estados produtores")
empilhar = st.toggle("Detalhar por fonte", value=False)
grafico(barras_estado(df_filtrado, empilhar_fontes=empilhar))

ranking = (
    somar(df_filtrado, ["uf", "nome_uf", "regiao"], ["producao_mwh", "consumo_mwh", "emissao_co2"])
    .sort_values("producao_mwh", ascending=False).reset_index(drop=True)
)
ranking["participacao"] = ranking["producao_mwh"] / ranking["producao_mwh"].sum() * 100
if len(ranking) >= 2:
    topo, base = ranking.iloc[0], ranking.iloc[-1]
    diferenca = (topo["producao_mwh"] / base["producao_mwh"] - 1) * 100
    interpretacao(
        f"**{topo['nome_uf']} ({topo['uf']})** lidera com {formatar_energia(topo['producao_mwh'])} e "
        f"**{base['nome_uf']} ({base['uf']})** fecha o ranking com {formatar_energia(base['producao_mwh'])}. "
        f"A diferença entre o primeiro e o último é de apenas {formatar_pct(diferenca)}: "
        + ("**os estados produzem volumes praticamente iguais**, e o ranking muda com pequenas oscilações."
           if diferenca < 5 else "há diferenças relevantes de produção entre os estados.")
    )

with st.expander("Tabela do ranking estadual", icon=":material/table:"):
    tabela = ranking.copy()
    for col in ["producao_mwh", "consumo_mwh"]:
        tabela[col] = tabela[col] / 1e6
    tabela["emissao_co2"] = tabela["emissao_co2"] / 1e6
    st.dataframe(
        tabela, hide_index=True,
        column_config={
            "uf": "UF", "nome_uf": "Estado", "regiao": "Região",
            "producao_mwh": st.column_config.NumberColumn("Produção (TWh)", format="%.2f"),
            "consumo_mwh": st.column_config.NumberColumn("Consumo (TWh)", format="%.2f"),
            "emissao_co2": st.column_config.NumberColumn("CO₂ (Mt)", format="%.2f"),
            "participacao": st.column_config.ProgressColumn("Participação", format="%.2f%%", min_value=0,
                                                            max_value=float(tabela["participacao"].max()) * 1.1),
        },
    )

st.subheader("Comparação entre regiões")
grafico(barras_regiao(df_filtrado))

regioes = df_filtrado.groupby("regiao", observed=True).agg(producao=("producao_mwh", "sum"), ufs=("uf", "nunique"))
regioes["por_uf"] = regioes["producao"] / regioes["ufs"]
regioes = regioes.sort_values("producao", ascending=False)
if len(regioes) >= 2:
    lider = regioes.index[0]
    interpretacao(
        f"**{lider}** é a região que mais produz ({formatar_energia(regioes.iloc[0]['producao'])}), mas isso reflete "
        f"principalmente o número de estados na base ({int(regioes.iloc[0]['ufs'])} UFs). A produção média por estado varia "
        f"só entre {formatar_numero(regioes['por_uf'].min() / 1e6, 2)} e {formatar_numero(regioes['por_uf'].max() / 1e6, 2)} TWh: "
        "nesta base simulada, nenhuma região é mais produtiva por estado que as outras."
    )
