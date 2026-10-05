import streamlit as st

from src.analise import calcular_kpis, destaques
from src.config import AVALIACAO, TITULO
from src.dados import formatar_co2, formatar_energia, formatar_numero, formatar_pct
from src.graficos import linha_producao_consumo, pizza_matriz
from src.ui import contexto, grafico, identificacao, interpretacao, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

st.title(TITULO)
st.caption(f"{AVALIACAO} · Dashboard interativo de análise e visualização de dados")
identificacao()

st.subheader("O problema")
st.markdown(
    """
A produção de energia é um dos principais indicadores de **desenvolvimento econômico** e de **infraestrutura** de um
país. O Brasil tem uma matriz diversificada (hidrelétricas, termelétricas, solar, eólica, biomassa e nuclear), e
acompanhar sua evolução permite entender o **crescimento da demanda**, a **sustentabilidade** da geração, a
**dependência** de determinadas fontes e os **impactos ambientais**.

Este painel analisa a produção e o consumo de energia entre **2015 e 2024**, a partir de uma base simulada com
14.400 registros mensais de 20 estados e 6 fontes, para identificar quais fontes predominam, como a matriz evoluiu,
onde se produz mais e qual é o custo ambiental da geração.
"""
)

with st.expander("Perguntas orientadoras", icon=":material/help:"):
    st.markdown(
        """
- Quais fontes energéticas predominam no Brasil?
- Quais regiões produzem mais energia?
- Houve crescimento da energia renovável?
- Existe sazonalidade na geração?
- Quais estados possuem maior produção?
- Há redução da dependência hidrelétrica?
- Como a matriz energética evoluiu ao longo do tempo?
"""
    )

st.subheader("Indicadores-chave")
resumo_filtro(len(df_filtrado), len(df))
k = calcular_kpis(df_filtrado)

c1, c2, c3 = st.columns(3)
c1.metric("Produção total de energia", formatar_energia(k["producao"]), border=True,
          help=f"{formatar_numero(k['producao'])} MWh no recorte. 1 TWh = 1 milhão de MWh.")
c2.metric("Fonte predominante", k["fonte"][0], delta=f"{formatar_pct(k['fonte'][1])} da produção",
          delta_color="off", delta_arrow="off", border=True)
c3.metric("Percentual renovável", formatar_pct(k["renovavel"]), border=True,
          help="Produção de hidrelétrica, eólica, solar e biomassa ÷ produção total. Nuclear é classificada "
               "como não renovável (usa urânio), embora o CSV original a marque com 95%.")

c4, c5, c6 = st.columns(3)
c4.metric("Estado com maior produção", f"{k['estado'][1]} ({k['estado'][0]})",
          delta=formatar_energia(k["estado"][2]), delta_color="off", delta_arrow="off", border=True)
c5.metric("Consumo total", formatar_energia(k["consumo"]),
          delta=f"produção cobre {formatar_pct(k['cobertura'])} do consumo", delta_color="off", delta_arrow="off",
          border=True)
c6.metric("Emissão total de CO₂", formatar_co2(k["emissao"]),
          delta=f"{formatar_numero(k['intensidade'] * 1000, 0)} kg CO₂/MWh", delta_color="off", delta_arrow="off",
          border=True, help="Intensidade de carbono: emissão total ÷ produção total.")

st.subheader("Destaques do recorte")
for frase in destaques(df_filtrado):
    st.markdown(f"- {frase}")

col_a, col_b = st.columns([1.5, 1])
with col_a:
    grafico(linha_producao_consumo(df_filtrado, "Anual"))
with col_b:
    grafico(pizza_matriz(df_filtrado))
interpretacao(
    "A produção cresce de forma contínua e se mantém sempre acima do consumo. Na matriz, a hidrelétrica é a principal "
    "fonte e as renováveis somam cerca de quatro quintos da geração; a termelétrica, segunda maior fonte, é a única fóssil."
)

st.subheader("Conclusão executiva (resumo)")
st.markdown(
    """
A produção de energia cresceu cerca de **4,2% ao ano** e a matriz é majoritariamente **renovável (≈ 78%)**, liderada
pela hidrelétrica. Mas a composição da matriz **ficou praticamente estável**: a dependência hidrelétrica não caiu de forma
relevante e a termelétrica cresceu um pouco mais rápido que as renováveis, o que fez as **emissões crescerem 49%** em dez
anos. A termelétrica gera menos de um quinto da energia e responde por quase **79% do CO₂**.
"""
)
st.page_link("paginas/conclusao.py", label="Ler a conclusão executiva completa", icon=":material/arrow_forward:")

with st.expander("Como os dados foram tratados", icon=":material/cleaning_services:"):
    r = ctx["relatorio"]
    st.markdown(
        f"""
Fonte: **{ctx['fonte']}** · Estados e mapa: **{ctx['origens']['estados']}** / **{ctx['origens']['malha']}**

| Etapa | Resultado |
|---|---|
| Registros lidos | {formatar_numero(r['linhas_originais'])} |
| Valores nulos | {r['valores_nulos']} |
| Datas divergentes de ano/mês (corrigidas) | {r['datas_corrigidas']} |
| Duplicados por estado × fonte × mês (removidos) | {r['duplicados_removidos']} |
| Registros inválidos (valores negativos ou produção > capacidade) | {r['registros_invalidos']} |
| Valores no piso artificial de 100 MWh (sinalizados) | {r['valores_piso']} ({r['fonte_piso']}) |
| Registros de nuclear reclassificados como não renováveis | {formatar_numero(r['classificacao_corrigida'])} |
| Nível de demanda divergente da regra consumo ÷ produção | {r['demanda_reclassificada']} |
| Registros finais | {formatar_numero(r['linhas_finais'])} |

Atributos criados: classe da fonte (renovável, nuclear, fóssil), saldo e índice de demanda (consumo ÷ produção), fator de
emissão, fator de capacidade, trimestre, período hidrológico e nome oficial + código IBGE de cada UF (via API do IBGE).
"""
    )
