"""Gráficos do projeto: Plotly para os gráficos interativos e Matplotlib/Seaborn para os mapas de calor."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

from src.analise import indice_sazonal
from src.config import (
    COR_CONSUMO, COR_DESTAQUE, CORES_CLASSE, CORES_DEMANDA, CORES_FONTE, CORES_REGIAO, ESCALA_SEQUENCIAL, GRADE,
    MESES, ORDEM_CLASSES, ORDEM_DEMANDA, ORDEM_FONTES, SUPERFICIE, TINTA_PRIMARIA, TINTA_SECUNDARIA, TINTA_SUAVE,
)
from src.dados import somar

CMAP_SEQUENCIAL = LinearSegmentedColormap.from_list("azul", ESCALA_SEQUENCIAL)
CMAP_DIVERGENTE = LinearSegmentedColormap.from_list("divergente", ["#d03b3b", "#f0efec", "#2a78d6"])
CONFIG_PLOTLY = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _presentes(ordem: list[str], valores) -> list[str]:
    conjunto = set(map(str, valores))
    return [v for v in ordem if v in conjunto]


def layout(fig: go.Figure, altura: int = 420, titulo: str | None = None, legenda: bool = True) -> go.Figure:
    """Estilo único: fundo claro, grade discreta, legenda no topo e números no padrão brasileiro."""
    fig.update_layout(
        title=dict(text=f"<b>{titulo}</b>" if titulo else None, x=0, xanchor="left", y=0.98, yanchor="top",
                   font=dict(size=15, color=TINTA_PRIMARIA)),
        height=altura,
        margin=dict(l=10, r=10, t=(90 if legenda else 60) if titulo else 20, b=10),
        paper_bgcolor=SUPERFICIE,
        plot_bgcolor=SUPERFICIE,
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=TINTA_SECUNDARIA, size=12),
        separators=",.",
        showlegend=legenda,
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, xanchor="left", title=None),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(gridcolor=GRADE, linecolor=GRADE, zeroline=False, tickfont=dict(color=TINTA_SUAVE))
    fig.update_yaxes(gridcolor=GRADE, linecolor=GRADE, zeroline=False, tickfont=dict(color=TINTA_SUAVE))
    return fig


# ---------------------------------------------------------------- Temporal
def linha_producao_consumo(df: pd.DataFrame, granularidade: str = "Mensal") -> go.Figure:
    """Produção e consumo ao longo do tempo (mesma unidade, um único eixo)."""
    chave = "data" if granularidade == "Mensal" else "ano"
    serie = somar(df, chave, ["producao_mwh", "consumo_mwh"]).sort_values(chave)
    fig = go.Figure()
    for coluna, nome, cor, traco in [("producao_mwh", "Produção", COR_DESTAQUE, "solid"),
                                     ("consumo_mwh", "Consumo", COR_CONSUMO, "dash")]:
        fig.add_trace(go.Scatter(
            x=serie[chave], y=serie[coluna] / 1e6, name=nome, mode="lines+markers" if chave == "ano" else "lines",
            line=dict(color=cor, width=2, dash=traco), marker=dict(size=7),
            hovertemplate=f"{nome}: %{{y:,.2f}} TWh<extra></extra>",
        ))
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title="TWh", rangemode="tozero")
    fig.update_xaxes(title=None, dtick=1 if chave == "ano" else None)
    return layout(fig, 420, f"Produção e consumo de energia ({granularidade.lower()})")


def area_fontes(df: pd.DataFrame) -> go.Figure:
    """Produção anual empilhada por fonte: mostra crescimento total e contribuição de cada fonte."""
    agg = somar(df, ["ano", "fonte_energia"], ["producao_mwh"])
    agg["fonte_energia"] = agg["fonte_energia"].astype(str)
    agg["twh"] = agg["producao_mwh"] / 1e6
    fig = px.area(agg, x="ano", y="twh", color="fonte_energia", color_discrete_map=CORES_FONTE,
                  category_orders={"fonte_energia": _presentes(ORDEM_FONTES, agg["fonte_energia"])},
                  labels={"twh": "TWh", "ano": "", "fonte_energia": "Fonte"})
    fig.update_traces(line_width=1, hovertemplate="%{fullData.name}: %{y:,.2f} TWh<extra></extra>")
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(dtick=1)
    return layout(fig, 430, "Produção anual por fonte (TWh)")


def matriz_100(df: pd.DataFrame) -> go.Figure:
    """Participação de cada fonte na produção de cada ano (barras 100% empilhadas)."""
    agg = somar(df, ["ano", "fonte_energia"], ["producao_mwh"])
    agg["fonte_energia"] = agg["fonte_energia"].astype(str)
    agg["pct"] = agg["producao_mwh"] / agg.groupby("ano")["producao_mwh"].transform("sum") * 100
    fig = px.bar(agg, x="ano", y="pct", color="fonte_energia", color_discrete_map=CORES_FONTE,
                 category_orders={"fonte_energia": _presentes(ORDEM_FONTES, agg["fonte_energia"])},
                 text=agg["pct"].map(lambda v: f"{v:.1f}".replace(".", ",") if v >= 4 else ""),
                 labels={"pct": "% da produção", "ano": "", "fonte_energia": "Fonte"})
    fig.update_traces(marker_line_color=SUPERFICIE, marker_line_width=1.5, textfont_size=10, textposition="inside",
                      hovertemplate="%{fullData.name}: %{y:.2f}%<extra></extra>")
    fig.update_layout(barmode="stack", hovermode="x unified", bargap=0.25)
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    fig.update_xaxes(dtick=1)
    return layout(fig, 440, "Evolução da matriz energética (% da produção)")


def linha_renovavel(anual: pd.DataFrame) -> go.Figure:
    """Participação renovável e hidrelétrica por ano."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anual["ano"], y=anual["renovavel_pct"], name="Renováveis", mode="lines+markers",
                             line=dict(color=CORES_CLASSE["Renovável"], width=2), marker=dict(size=7),
                             hovertemplate="Renováveis: %{y:.2f}%<extra></extra>"))
    if "hidreletrica_pct" in anual:
        fig.add_trace(go.Scatter(x=anual["ano"], y=anual["hidreletrica_pct"], name="Hidrelétrica", mode="lines+markers",
                                 line=dict(color=CORES_FONTE["Hidrelétrica"], width=2), marker=dict(size=7),
                                 hovertemplate="Hidrelétrica: %{y:.2f}%<extra></extra>"))
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(range=[0, 100], ticksuffix="%", title="% da produção")
    fig.update_xaxes(dtick=1)
    return layout(fig, 380, "Participação renovável e hidrelétrica na produção")


def heatmap_sazonal(df: pd.DataFrame) -> plt.Figure:
    """Índice sazonal (Seaborn): produção do mês ÷ média mensal do ano. 1,00 = mês típico."""
    mensal = indice_sazonal(df)
    tabela = mensal.pivot(index="ano", columns="mes", values="indice")
    tabela.columns = [MESES[m - 1] for m in tabela.columns]
    fig, ax = plt.subplots(figsize=(12, max(3.2, 0.42 * len(tabela) + 1.4)))
    limite = max(0.03, float((tabela - 1).abs().max().max()))
    sns.heatmap(tabela, cmap=CMAP_DIVERGENTE, center=1, vmin=1 - limite, vmax=1 + limite, annot=True, fmt=".2f",
                annot_kws={"fontsize": 8}, linewidths=1.5, linecolor=SUPERFICIE,
                cbar_kws={"label": "Índice sazonal (1,00 = mês típico)", "shrink": 0.85}, ax=ax)
    ax.set_title("Índice sazonal da produção por mês", loc="left", fontweight="bold", fontsize=13, color=TINTA_PRIMARIA)
    ax.set_xlabel("")
    ax.set_ylabel("Ano")
    ax.tick_params(axis="y", rotation=0)
    ax.tick_params(colors=TINTA_SUAVE, labelsize=9)
    fig.patch.set_facecolor(SUPERFICIE)
    fig.tight_layout()
    return fig


def perfil_sazonal_fontes(df: pd.DataFrame) -> go.Figure:
    """Índice sazonal médio de cada fonte ao longo dos meses."""
    mensal = indice_sazonal(df, "fonte_energia")
    perfil = mensal.groupby(["fonte_energia", "mes"], observed=True)["indice"].mean().reset_index()
    perfil["fonte_energia"] = perfil["fonte_energia"].astype(str)
    perfil["nome_mes"] = perfil["mes"].map(lambda m: MESES[m - 1])
    fig = px.line(perfil, x="nome_mes", y="indice", color="fonte_energia", markers=True, color_discrete_map=CORES_FONTE,
                  category_orders={"fonte_energia": _presentes(ORDEM_FONTES, perfil["fonte_energia"]), "nome_mes": MESES},
                  labels={"indice": "Índice sazonal", "nome_mes": "", "fonte_energia": "Fonte"})
    fig.update_traces(line_width=2, marker_size=6, hovertemplate="%{fullData.name}: %{y:.3f}<extra></extra>")
    fig.add_hline(y=1, line_color=TINTA_SECUNDARIA, line_dash="dot", line_width=1)
    fig.update_layout(hovermode="x unified")
    return layout(fig, 400, "Perfil sazonal médio por fonte (1,00 = mês típico)")


# ---------------------------------------------------------------- Fontes
def barras_fonte(df: pd.DataFrame) -> go.Figure:
    """Produção total por fonte, em ordem decrescente, com rótulo de valor e participação."""
    agg = somar(df, "fonte_energia", ["producao_mwh"]).sort_values("producao_mwh")
    agg["fonte_energia"] = agg["fonte_energia"].astype(str)
    total = agg["producao_mwh"].sum()
    rotulos = [f"{v / 1e6:,.1f} TWh · {v / total * 100:.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")
               for v in agg["producao_mwh"]]
    fig = go.Figure(go.Bar(
        y=agg["fonte_energia"], x=agg["producao_mwh"] / 1e6, orientation="h", text=rotulos, textposition="outside",
        marker=dict(color=[CORES_FONTE[f] for f in agg["fonte_energia"]], line=dict(color=SUPERFICIE, width=1)),
        hovertemplate="%{y}: %{x:,.2f} TWh<extra></extra>", cliponaxis=False,
    ))
    fig.update_xaxes(title="TWh", range=[0, agg["producao_mwh"].max() / 1e6 * 1.3])
    fig.update_yaxes(title=None, showgrid=False)
    return layout(fig, 380, "Produção total por fonte", legenda=False)


def pizza_matriz(df: pd.DataFrame, por: str = "fonte_energia") -> go.Figure:
    """Rosca da matriz energética: participação de cada fonte (ou classe) na produção."""
    agg = somar(df, por, ["producao_mwh"])
    agg[por] = agg[por].astype(str)
    cores, ordem = (CORES_FONTE, ORDEM_FONTES) if por == "fonte_energia" else (CORES_CLASSE, ORDEM_CLASSES)
    agg = agg.set_index(por).reindex(_presentes(ordem, agg[por])).reset_index()
    fig = go.Figure(go.Pie(
        labels=agg[por], values=agg["producao_mwh"] / 1e6, hole=0.55, sort=False, direction="clockwise",
        marker=dict(colors=[cores[c] for c in agg[por]], line=dict(color=SUPERFICIE, width=2)),
        textposition="inside", texttemplate="%{percent:.1%}", insidetextorientation="horizontal",
        hovertemplate="%{label}: %{value:,.1f} TWh (%{percent:.1%})<extra></extra>",
    ))
    total = agg["producao_mwh"].sum() / 1e6
    fig.add_annotation(text=f"<b>{total:,.0f}</b><br>TWh".replace(",", "."), showarrow=False, font=dict(size=16, color=TINTA_PRIMARIA))
    titulo = "Matriz energética (participação na produção)" if por == "fonte_energia" else "Renovável × nuclear × fóssil"
    fig.update_layout(uniformtext=dict(minsize=10, mode="hide"))
    layout(fig, 420, titulo)
    return fig.update_layout(legend=dict(orientation="v", x=1.0, xanchor="left", y=0.5, yanchor="middle"),
                             margin=dict(t=60, r=10))


# ---------------------------------------------------------------- Geografia
def barras_estado(df: pd.DataFrame, empilhar_fontes: bool = False) -> go.Figure:
    """Ranking de estados pela produção, coloridos pela região (ou empilhados por fonte)."""
    total_uf = somar(df, ["uf", "regiao"], ["producao_mwh"]).sort_values("producao_mwh")
    ordem = total_uf["uf"].tolist()
    if empilhar_fontes:
        agg = somar(df, ["uf", "fonte_energia"], ["producao_mwh"])
        agg["fonte_energia"] = agg["fonte_energia"].astype(str)
        fig = px.bar(agg, y="uf", x=agg["producao_mwh"] / 1e6, color="fonte_energia", orientation="h",
                     color_discrete_map=CORES_FONTE, category_orders={"uf": ordem[::-1],
                     "fonte_energia": _presentes(ORDEM_FONTES, agg["fonte_energia"])},
                     labels={"x": "TWh", "uf": "", "fonte_energia": "Fonte"})
        fig.update_traces(marker_line_color=SUPERFICIE, marker_line_width=1, hovertemplate="%{fullData.name}: %{x:,.2f} TWh<extra></extra>")
        fig.update_layout(barmode="stack")
    else:
        total_uf["regiao"] = total_uf["regiao"].astype(str)
        fig = go.Figure()
        for regiao in _presentes(list(CORES_REGIAO), total_uf["regiao"]):
            sub = total_uf[total_uf["regiao"] == regiao]
            fig.add_trace(go.Bar(y=sub["uf"], x=sub["producao_mwh"] / 1e6, orientation="h", name=regiao,
                                 marker_color=CORES_REGIAO[regiao], text=(sub["producao_mwh"] / 1e6).map(lambda v: f"{v:.2f}".replace(".", ",")),
                                 textposition="outside", cliponaxis=False,
                                 hovertemplate="%{y}: %{x:,.2f} TWh<extra>" + regiao + "</extra>"))
        media = total_uf["producao_mwh"].mean() / 1e6
        fig.add_vline(x=media, line_dash="dash", line_color=TINTA_PRIMARIA, line_width=1,
                      annotation_text=f"média {media:.2f} TWh".replace(".", ","), annotation_position="top left")
        fig.update_xaxes(range=[0, total_uf["producao_mwh"].max() / 1e6 * 1.15])
    fig.update_yaxes(categoryorder="array", categoryarray=ordem, title=None, showgrid=False)
    fig.update_xaxes(title="TWh")
    return layout(fig, max(420, 26 * len(ordem) + 120), "Produção por estado (TWh)")


def barras_regiao(df: pd.DataFrame) -> go.Figure:
    """Produção total por região, com a média por estado no rótulo (a base tem nº de UFs diferente por região)."""
    agg = df.groupby("regiao", observed=True).agg(producao=("producao_mwh", "sum"), ufs=("uf", "nunique")).reset_index()
    agg["regiao"] = agg["regiao"].astype(str)
    agg = agg.sort_values("producao", ascending=False)
    rotulos = [f"{p / 1e6:,.1f} TWh · {u} UFs · {p / u / 1e6:,.2f} por UF".replace(",", "X").replace(".", ",").replace("X", ".")
               for p, u in zip(agg["producao"], agg["ufs"])]
    fig = go.Figure(go.Bar(x=agg["regiao"], y=agg["producao"] / 1e6, text=rotulos, textposition="outside",
                           marker_color=[CORES_REGIAO[r] for r in agg["regiao"]], cliponaxis=False,
                           hovertemplate="%{x}: %{y:,.2f} TWh<extra></extra>"))
    fig.update_yaxes(title="TWh", range=[0, agg["producao"].max() / 1e6 * 1.2])
    fig.update_xaxes(title=None, showgrid=False)
    return layout(fig, 400, "Produção por região", legenda=False)


def mapa_ufs(df: pd.DataFrame, malha: dict, metrica: str = "producao_mwh") -> go.Figure:
    """Mapa coroplético interativo com a produção (ou o saldo) de cada UF."""
    agg = df.groupby(["codigo_ibge", "uf", "nome_uf", "regiao"], observed=True)[
        ["producao_mwh", "consumo_mwh", "emissao_co2"]].sum().reset_index()
    agg["saldo_mwh"] = agg["producao_mwh"] - agg["consumo_mwh"]
    agg["valor"] = agg[metrica] / 1e6
    agg["codarea"] = agg["codigo_ibge"].astype(str)
    titulo_barra = {"producao_mwh": "Produção (TWh)", "saldo_mwh": "Saldo (TWh)", "emissao_co2": "CO₂ (Mt)"}[metrica]
    fig = px.choropleth(agg, geojson=malha, locations="codarea", featureidkey="properties.codarea", color="valor",
                        color_continuous_scale=ESCALA_SEQUENCIAL,
                        custom_data=["nome_uf", "uf", "regiao", agg["producao_mwh"] / 1e6, agg["consumo_mwh"] / 1e6,
                                     agg["emissao_co2"] / 1e6])
    fig.update_traces(
        marker_line_color="#ffffff", marker_line_width=0.8,
        hovertemplate="<b>%{customdata[0]} (%{customdata[1]})</b><br>Região: %{customdata[2]}"
                      "<br>Produção: %{customdata[3]:,.2f} TWh<br>Consumo: %{customdata[4]:,.2f} TWh"
                      "<br>CO₂: %{customdata[5]:,.2f} Mt<extra></extra>",
    )
    com_dados = set(agg["codarea"])
    sem_dados = [f["properties"]["codarea"] for f in malha["features"] if f["properties"]["codarea"] not in com_dados]
    if sem_dados:
        fig.add_trace(go.Choropleth(
            geojson=malha, locations=sem_dados, featureidkey="properties.codarea", z=[0] * len(sem_dados),
            colorscale=[[0, GRADE], [1, GRADE]], showscale=False, marker_line_color="#ffffff",
            marker_line_width=0.8, hovertemplate="Sem dados no recorte<extra></extra>",
        ))
    fig.update_geos(fitbounds="geojson", visible=False, bgcolor=SUPERFICIE)
    fig.update_layout(coloraxis_colorbar=dict(title=titulo_barra))
    return layout(fig, 520, None, legenda=False).update_layout(margin=dict(l=0, r=0, t=10, b=0))


# ---------------------------------------------------------------- Produção x consumo
def dispersao_producao_consumo(df: pd.DataFrame) -> go.Figure:
    """Consumo × produção por estado e mês, com a linha de equilíbrio (consumo = produção)."""
    agg = df.groupby(["uf", "data"], observed=True)[["producao_mwh", "consumo_mwh"]].sum().reset_index()
    agg["indice"] = agg["consumo_mwh"] / agg["producao_mwh"]
    fig = px.scatter(agg, x=agg["producao_mwh"] / 1e3, y=agg["consumo_mwh"] / 1e3, color="indice",
                     color_continuous_scale=["#2a78d6", "#f0efec", "#d03b3b"], range_color=[0.85, 1.05],
                     hover_data={"uf": True, "data": "|%m/%Y"}, render_mode="webgl",
                     labels={"x": "Produção (GWh)", "y": "Consumo (GWh)", "indice": "Consumo ÷ produção"})
    limite = max(agg["producao_mwh"].max(), agg["consumo_mwh"].max()) / 1e3
    fig.add_trace(go.Scatter(x=[0, limite], y=[0, limite], mode="lines", name="Equilíbrio (consumo = produção)",
                             line=dict(color=TINTA_PRIMARIA, dash="dash", width=1), hoverinfo="skip"))
    fig.update_traces(selector=dict(mode="markers"), marker=dict(size=6, opacity=0.7))
    return layout(fig, 460, "Consumo × produção por estado e mês")


def demanda_por_ano(df: pd.DataFrame) -> go.Figure:
    """Composição dos níveis de demanda em cada ano (status ordinal, sempre com rótulo)."""
    tabela = pd.crosstab(df["ano"], df["nivel_demanda"], normalize="index") * 100
    fig = go.Figure()
    for nivel in _presentes(ORDEM_DEMANDA, tabela.columns.astype(str)):
        valores = tabela[nivel]
        fig.add_trace(go.Bar(x=tabela.index, y=valores, name=nivel, marker_color=CORES_DEMANDA[nivel],
                             marker_line_color=SUPERFICIE, marker_line_width=1.5,
                             text=valores.map(lambda v: f"{v:.0f}%" if v >= 6 else ""), textposition="inside",
                             textfont=dict(color=TINTA_PRIMARIA, size=10),
                             hovertemplate=nivel + ": %{y:.1f}%<extra></extra>"))
    fig.update_layout(barmode="stack", hovermode="x unified", bargap=0.25)
    fig.update_yaxes(range=[0, 100], ticksuffix="%", title="% dos registros")
    fig.update_xaxes(dtick=1)
    return layout(fig, 400, "Nível de demanda por ano (consumo ÷ produção)")


def saldo_estado(df: pd.DataFrame) -> go.Figure:
    """Saldo (produção − consumo) por estado."""
    agg = somar(df, "uf", ["producao_mwh", "consumo_mwh"])
    agg["saldo"] = (agg["producao_mwh"] - agg["consumo_mwh"]) / 1e6
    agg = agg.sort_values("saldo")
    cores = [COR_DESTAQUE if v >= 0 else "#d03b3b" for v in agg["saldo"]]
    fig = go.Figure(go.Bar(y=agg["uf"], x=agg["saldo"], orientation="h", marker_color=cores,
                           text=agg["saldo"].map(lambda v: f"{v:+.2f}".replace(".", ",")), textposition="outside",
                           cliponaxis=False, hovertemplate="%{y}: %{x:+,.2f} TWh<extra></extra>"))
    fig.update_yaxes(title=None, showgrid=False)
    fig.update_xaxes(title="Saldo (TWh)", zeroline=True, zerolinecolor=TINTA_SECUNDARIA)
    return layout(fig, max(420, 26 * len(agg) + 120), "Saldo energético por estado (produção − consumo)", legenda=False)


# ---------------------------------------------------------------- Ambiental
def dispersao_emissao(df: pd.DataFrame) -> go.Figure:
    """Emissão × produção por registro, colorida pela fonte: cada fonte forma uma reta com inclinação = fator de emissão."""
    base = df.copy()
    base["fonte_energia"] = base["fonte_energia"].astype(str)
    fig = px.scatter(base, x=base["producao_mwh"] / 1e3, y=base["emissao_co2"] / 1e3, color="fonte_energia",
                     color_discrete_map=CORES_FONTE, render_mode="webgl",
                     category_orders={"fonte_energia": _presentes(ORDEM_FONTES, base["fonte_energia"])},
                     hover_data={"uf": True, "ano_mes": True},
                     labels={"x": "Produção (GWh)", "y": "Emissão (mil t CO₂)", "fonte_energia": "Fonte"})
    fig.update_traces(marker=dict(size=5, opacity=0.6))
    return layout(fig, 460, "Emissão de CO₂ × produção por registro")


def participacao_emissoes(df: pd.DataFrame) -> go.Figure:
    """Participação de cada fonte na produção versus nas emissões."""
    agg = somar(df, "fonte_energia", ["producao_mwh", "emissao_co2"])
    agg["fonte_energia"] = agg["fonte_energia"].astype(str)
    agg["Produção"] = agg["producao_mwh"] / agg["producao_mwh"].sum() * 100
    agg["Emissões de CO₂"] = agg["emissao_co2"] / agg["emissao_co2"].sum() * 100
    longo = agg.melt(id_vars="fonte_energia", value_vars=["Produção", "Emissões de CO₂"], var_name="medida", value_name="pct")
    fig = px.bar(longo, x="fonte_energia", y="pct", color="medida", barmode="group",
                 color_discrete_map={"Produção": COR_DESTAQUE, "Emissões de CO₂": "#d03b3b"},
                 category_orders={"fonte_energia": _presentes(ORDEM_FONTES, longo["fonte_energia"])},
                 text=longo["pct"].map(lambda v: f"{v:.1f}%".replace(".", ",")),
                 labels={"pct": "% do total", "fonte_energia": "", "medida": ""})
    fig.update_traces(textposition="outside", cliponaxis=False, marker_line_color=SUPERFICIE, marker_line_width=1.5,
                      hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>")
    fig.update_yaxes(ticksuffix="%", range=[0, longo["pct"].max() * 1.15])
    return layout(fig, 420, "Participação na produção × participação nas emissões")


def emissoes_anuais(df: pd.DataFrame) -> go.Figure:
    """Emissões anuais por classe de fonte (empilhadas)."""
    agg = somar(df, ["ano", "classe_fonte"], ["emissao_co2"])
    agg["classe_fonte"] = agg["classe_fonte"].astype(str)
    fig = px.bar(agg, x="ano", y=agg["emissao_co2"] / 1e6, color="classe_fonte", color_discrete_map=CORES_CLASSE,
                 category_orders={"classe_fonte": _presentes(ORDEM_CLASSES, agg["classe_fonte"])},
                 labels={"y": "Mt CO₂", "ano": "", "classe_fonte": "Classe"})
    fig.update_traces(marker_line_color=SUPERFICIE, marker_line_width=1.5, hovertemplate="%{fullData.name}: %{y:,.2f} Mt<extra></extra>")
    fig.update_layout(barmode="stack", hovermode="x unified", bargap=0.25)
    fig.update_xaxes(dtick=1)
    return layout(fig, 400, "Emissões anuais de CO₂ por classe de fonte (Mt)")


def matriz_correlacao(df: pd.DataFrame, metodo: str = "pearson") -> plt.Figure:
    """Matriz de correlação (Seaborn) entre as variáveis numéricas."""
    rotulos = {
        "producao_mwh": "Produção", "consumo_mwh": "Consumo", "capacidade_instalada": "Capacidade",
        "emissao_co2": "Emissão CO$_2$", "custo_medio_mwh": "Custo/MWh", "indice_demanda": "Consumo ÷ produção",
    }
    base = df[list(rotulos)].rename(columns=rotulos)
    if metodo == "spearman":
        base = base.rank()
    corr = base.corr()
    mascara = np.triu(np.ones_like(corr, dtype=bool), k=1)
    fig, ax = plt.subplots(figsize=(7.5, 6))
    sns.heatmap(corr, mask=mascara, cmap=CMAP_DIVERGENTE, vmin=-1, vmax=1, center=0, annot=True, fmt=".2f", square=True,
                linewidths=2, linecolor=SUPERFICIE, cbar_kws={"label": f"Correlação ({metodo.title()})", "shrink": 0.75}, ax=ax)
    ax.set_title("Matriz de correlação", loc="left", fontweight="bold", fontsize=13, color=TINTA_PRIMARIA)
    ax.tick_params(colors=TINTA_SECUNDARIA, labelsize=9)
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    fig.patch.set_facecolor(SUPERFICIE)
    fig.tight_layout()
    return fig
