import streamlit as st

from src.analise import calcular_kpis, crescimento_por_fonte, resumo_sazonalidade, serie_anual, taxa_crescimento
from src.config import ALUNO, DISCIPLINA, PROFESSOR
from src.dados import formatar_co2, formatar_energia, formatar_numero, formatar_pct, participacao, somar
from src.ui import cabecalho, contexto

ctx = contexto()
df = ctx["df"]

cabecalho("Conclusão executiva", "Respostas às perguntas orientadoras com base na série completa 2015–2024 (independe dos filtros).")

k = calcular_kpis(df)
fontes = participacao(df)
anual = serie_anual(df)
anos = int(anual["ano"].iloc[-1] - anual["ano"].iloc[0])
cagr = taxa_crescimento(anual["producao_mwh"].iloc[0], anual["producao_mwh"].iloc[-1], anos)
crescimento = crescimento_por_fonte(df).set_index("Fonte")
s = resumo_sazonalidade(df)
ufs = somar(df, ["uf", "nome_uf"], ["producao_mwh"]).sort_values("producao_mwh", ascending=False)
regioes = df.groupby("regiao", observed=True).agg(producao=("producao_mwh", "sum"), ufs=("uf", "nunique"))
regioes = regioes.sort_values("producao", ascending=False)
renov_abs = df[df["renovavel"]].groupby("ano")["producao_mwh"].sum()
emissao_anual = df.groupby("ano")["emissao_co2"].sum()
termica = df[df["fonte_energia"] == "Termelétrica"]
ini, fim = anual.iloc[0], anual.iloc[-1]

st.subheader("Respostas às perguntas orientadoras")
respostas = [
    ("Quais fontes energéticas predominam no Brasil?",
     "A **hidrelétrica** domina, com " + formatar_pct(fontes.iloc[0]["participacao"]) + " da produção, seguida por "
     + ", ".join(f"{r.fonte_energia} ({formatar_pct(r.participacao)})" for r in fontes.iloc[1:].itertuples()) + "."),
    ("Quais regiões produzem mais energia?",
     f"O **{regioes.index[0]}** lidera ({formatar_energia(regioes.iloc[0]['producao'])}), mas porque tem mais estados na base "
     f"({int(regioes.iloc[0]['ufs'])} UFs). Por estado, todas as regiões produzem cerca de "
     f"{formatar_numero(regioes['producao'].sum() / regioes['ufs'].sum() / 1e6, 1)} TWh."),
    ("Houve crescimento da energia renovável?",
     f"**Em volume, sim**: de {formatar_energia(renov_abs.iloc[0])} para {formatar_energia(renov_abs.iloc[-1])} "
     f"(+{formatar_pct((renov_abs.iloc[-1] / renov_abs.iloc[0] - 1) * 100)}). **Em participação, não**: "
     f"{formatar_pct(ini['renovavel_pct'])} em {int(ini['ano'])} e {formatar_pct(fim['renovavel_pct'])} em {int(fim['ano'])}, "
     "porque a termelétrica cresceu no mesmo ritmo."),
    ("Existe sazonalidade na geração?",
     f"**Não de forma relevante.** A diferença entre o mês mais forte e o mais fraco é de {formatar_numero(s['amplitude'], 1)}% "
     f"e o padrão não se repete entre os anos (consistência {formatar_numero(s['consistencia'], 2)})."),
    ("Quais estados possuem maior produção?",
     ", ".join(f"{r.nome_uf} ({formatar_energia(r.producao_mwh)})" for r in ufs.head(3).itertuples())
     + f". A diferença entre o 1º e o último ({ufs.iloc[-1]['nome_uf']}) é de só "
     f"{formatar_pct((ufs.iloc[0]['producao_mwh'] / ufs.iloc[-1]['producao_mwh'] - 1) * 100)}: os estados produzem volumes quase iguais."),
    ("Há redução da dependência hidrelétrica?",
     f"**Não.** A participação hidrelétrica foi de {formatar_pct(ini['hidreletrica_pct'])} para "
     f"{formatar_pct(fim['hidreletrica_pct'])} ({formatar_numero(fim['hidreletrica_pct'] - ini['hidreletrica_pct'], 2)} p.p.), "
     "uma variação dentro da oscilação normal entre anos."),
    ("Como a matriz energética evoluiu ao longo do tempo?",
     f"A produção total cresceu {formatar_pct(cagr, 2)} ao ano, mas a **composição ficou estável**. A termelétrica foi a que "
     f"mais cresceu ({formatar_pct(crescimento.loc['Termelétrica', 'Crescimento anual (%)'], 2)} ao ano) e a nuclear a que "
     f"menos cresceu ({formatar_pct(crescimento.loc['Nuclear', 'Crescimento anual (%)'], 2)} ao ano)."),
]
for pergunta, resposta in respostas:
    with st.container(border=True):
        st.markdown(f"**{pergunta}**  \n{resposta}")

st.subheader("Síntese")
st.markdown(
    f"""
Entre 2015 e 2024 foram produzidos **{formatar_energia(k['producao'])}** e consumidos **{formatar_energia(k['consumo'])}**:
a produção cobre o consumo com folga ({formatar_pct(k['cobertura'])}) e cresce **{formatar_pct(cagr, 2)} ao ano**. A matriz
é **{formatar_pct(k['renovavel'])} renovável** e liderada pela hidrelétrica, mas **não está se transformando**: as
participações das fontes praticamente não mudaram em dez anos.

O ponto de atenção é o **impacto ambiental**. As emissões passaram de {formatar_co2(emissao_anual.iloc[0])} para
{formatar_co2(emissao_anual.iloc[-1])} por ano (+{formatar_pct((emissao_anual.iloc[-1] / emissao_anual.iloc[0] - 1) * 100)}).
A termelétrica gera {formatar_pct(termica['producao_mwh'].sum() / k['producao'] * 100)} da energia e responde por
**{formatar_pct(termica['emissao_co2'].sum() / k['emissao'] * 100)} do CO₂**.

**Recomendações**

1. **Substituir geração térmica**: novas usinas eólicas e solares só reduzem emissões se deslocarem a geração fóssil; hoje
   a térmica cresce no mesmo ritmo que as renováveis.
2. **Diversificar além da hidrelétrica**: com mais de um terço da matriz em uma única fonte, o sistema segue exposto a
   crises hídricas. Eólica e solar são as alternativas renováveis de maior escala.
3. **Monitorar a demanda crítica**: 6% a 8% dos registros têm consumo acima de 112% da produção; acompanhar esses casos
   por estado e fonte evita gargalos locais.
4. **Planejar a expansão**: com crescimento de cerca de 4% ao ano, a produção precisa crescer cerca de 50% a cada década
   para acompanhar o consumo.

**Limitações**

- A base é **simulada**: fator de emissão, fator de capacidade e participação por fonte são praticamente constantes, e a
  produção por estado é quase igual, o que não ocorre no sistema elétrico real.
- O CSV classifica nuclear como 95% renovável; neste projeto ela foi tratada como não renovável (de baixa emissão).
- A análise é descritiva: correlação não implica causalidade.
"""
)

st.divider()
st.caption(f"{DISCIPLINA} · Professor: {PROFESSOR} · Aluno: {ALUNO}")
