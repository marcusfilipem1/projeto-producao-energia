import streamlit as st

from src.analise import calcular_kpis, correlacao
from src.dados import formatar_energia, formatar_numero, formatar_pct
from src.graficos import demanda_por_ano, dispersao_producao_consumo, saldo_estado
from src.ui import cabecalho, contexto, grafico, interpretacao, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Produção × consumo", "A produção atende ao consumo? Onde e quando a demanda fica crítica?")
resumo_filtro(len(df_filtrado), len(df))

k = calcular_kpis(df_filtrado)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Produção", formatar_energia(k["producao"]), border=True)
c2.metric("Consumo", formatar_energia(k["consumo"]), border=True)
c3.metric("Saldo (produção − consumo)", formatar_energia(k["saldo"]), border=True)
c4.metric("Demanda crítica", formatar_pct(k["pct_critico"]), border=True,
          help="Percentual de registros com consumo ≥ 112% da produção no mês, estado e fonte.")

grafico(dispersao_producao_consumo(df_filtrado))
mensal = df_filtrado.groupby(["uf", "data"])[["producao_mwh", "consumo_mwh"]].sum()
r = correlacao(mensal["producao_mwh"], mensal["consumo_mwh"])
deficit = (mensal["consumo_mwh"] > mensal["producao_mwh"]).mean() * 100
interpretacao(
    f"Cada ponto é um estado em um mês. Produção e consumo andam juntos (correlação de {formatar_numero(r, 3)}). "
    f"Em {formatar_pct(deficit)} dos estados-mês (pontos acima da linha de equilíbrio) o consumo superou a produção. "
    + (f"No total, a produção cobre {formatar_pct(k['cobertura'])} do consumo, uma folga de {formatar_energia(k['saldo'])}: "
       "os déficits pontuais são compensados pelos meses de sobra."
       if k["saldo"] >= 0 else
       f"No total, a produção cobre só {formatar_pct(k['cobertura'])} do consumo neste recorte, um déficit de "
       f"{formatar_energia(-k['saldo'])}.")
)

col_a, col_b = st.columns([1.2, 1])
with col_a:
    grafico(demanda_por_ano(df_filtrado))
with col_b:
    grafico(saldo_estado(df_filtrado))

por_uf = df_filtrado.groupby("uf")[["producao_mwh", "consumo_mwh"]].sum()
deficitarios = int((por_uf["consumo_mwh"] > por_uf["producao_mwh"]).sum())
criticos_ano = (df_filtrado.assign(critico=df_filtrado["nivel_demanda"] == "Crítico")
                .groupby("ano")["critico"].mean() * 100)
interpretacao(
    "O nível de demanda segue a razão consumo ÷ produção de cada registro: Baixo < 0,85, Médio 0,85–1,00, "
    f"Alto 1,00–1,12 e Crítico ≥ 1,12. A fatia de registros críticos variou entre {formatar_pct(criticos_ano.min())} e "
    f"{formatar_pct(criticos_ano.max())} por ano, sem tendência clara. "
    + ("Como nenhum estado consome mais do que produz no agregado, essas são pressões pontuais em fontes e meses "
       "específicos, e não um déficit estrutural."
       if deficitarios == 0 else
       f"{deficitarios} estado(s) consomem mais do que produzem no recorte selecionado.")
)
