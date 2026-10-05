"""KPIs, estatísticas e textos interpretativos gerados a partir do recorte filtrado."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.dados import (
    formatar_co2, formatar_energia, formatar_numero, formatar_pct, participacao, percentual_renovavel, somar,
)


def calcular_kpis(df: pd.DataFrame) -> dict:
    """Os seis KPIs exigidos pelo tema + indicadores de apoio."""
    fontes = participacao(df, "fonte_energia")
    estados = somar(df, ["uf", "nome_uf"], ["producao_mwh"]).sort_values("producao_mwh", ascending=False)
    regioes = somar(df, "regiao", ["producao_mwh"]).sort_values("producao_mwh", ascending=False)
    producao = float(df["producao_mwh"].sum())
    consumo = float(df["consumo_mwh"].sum())
    emissao = float(df["emissao_co2"].sum())
    return {
        "producao": producao,
        "consumo": consumo,
        "emissao": emissao,
        "saldo": producao - consumo,
        "cobertura": producao / consumo * 100 if consumo else float("nan"),
        "intensidade": emissao / producao if producao else float("nan"),
        "renovavel": percentual_renovavel(df),
        "fonte": (str(fontes.iloc[0]["fonte_energia"]), float(fontes.iloc[0]["participacao"])),
        "estado": (str(estados.iloc[0]["uf"]), str(estados.iloc[0]["nome_uf"]), float(estados.iloc[0]["producao_mwh"])),
        "regiao": (str(regioes.iloc[0]["regiao"]), float(regioes.iloc[0]["producao_mwh"])),
        "pct_critico": float((df["nivel_demanda"] == "Crítico").mean() * 100),
    }


def serie_anual(df: pd.DataFrame) -> pd.DataFrame:
    anual = somar(df, "ano").sort_values("ano")
    renov = df[df["renovavel"]].groupby("ano")["producao_mwh"].sum()
    anual["renovavel_pct"] = anual["ano"].map(renov).fillna(0) / anual["producao_mwh"] * 100
    hidro = df[df["fonte_energia"] == "Hidrelétrica"].groupby("ano")["producao_mwh"].sum()
    anual["hidreletrica_pct"] = anual["ano"].map(hidro).fillna(0) / anual["producao_mwh"] * 100
    anual["crescimento_pct"] = anual["producao_mwh"].pct_change() * 100
    anual["media_movel_3a"] = anual["producao_mwh"].rolling(3, min_periods=1).mean()
    return anual


def taxa_crescimento(inicial: float, final: float, anos: int) -> float:
    """Taxa composta de crescimento anual (CAGR), em %."""
    if anos <= 0 or inicial <= 0:
        return float("nan")
    return ((final / inicial) ** (1 / anos) - 1) * 100


def crescimento_por_fonte(df: pd.DataFrame) -> pd.DataFrame:
    """CAGR da produção de cada fonte entre o primeiro e o último ano do recorte."""
    tabela = df.pivot_table(index="ano", columns="fonte_energia", values="producao_mwh", aggfunc="sum", observed=True)
    anos = int(tabela.index.max() - tabela.index.min())
    linhas = []
    for fonte in tabela.columns:
        ini, fim = tabela[fonte].iloc[0], tabela[fonte].iloc[-1]
        participacao_ini = ini / tabela.iloc[0].sum() * 100
        participacao_fim = fim / tabela.iloc[-1].sum() * 100
        linhas.append({
            "Fonte": str(fonte),
            "Produção inicial (TWh)": ini / 1e6,
            "Produção final (TWh)": fim / 1e6,
            "Crescimento anual (%)": taxa_crescimento(ini, fim, anos),
            "Participação inicial (%)": participacao_ini,
            "Participação final (%)": participacao_fim,
            "Variação (p.p.)": participacao_fim - participacao_ini,
        })
    return pd.DataFrame(linhas).sort_values("Crescimento anual (%)", ascending=False)


def tendencia(serie: pd.Series, eixo: pd.Series) -> float:
    """Inclinação da reta de mínimos quadrados (NumPy)."""
    return float(np.polyfit(eixo, serie, 1)[0]) if len(serie) >= 2 else float("nan")


def indice_sazonal(df: pd.DataFrame, por: str | None = None) -> pd.DataFrame:
    """Índice sazonal de cada mês: produção do mês ÷ média mensal do mesmo ano (1,00 = mês típico).

    Dividir pelo ano remove a tendência de crescimento, isolando o efeito do calendário.
    """
    chaves = ["ano", "mes"] + ([por] if por else [])
    mensal = df.groupby(chaves, observed=True)["producao_mwh"].sum().reset_index()
    grupo_ano = ["ano"] + ([por] if por else [])
    mensal["indice"] = mensal["producao_mwh"] / mensal.groupby(grupo_ano, observed=True)["producao_mwh"].transform("mean")
    return mensal


def resumo_sazonalidade(df: pd.DataFrame) -> dict:
    """Média do índice por mês e se o padrão se repete entre os anos."""
    mensal = indice_sazonal(df)
    perfil = mensal.groupby("mes")["indice"].mean()
    # Consistência: correlação média do perfil de cada ano com o perfil dos demais anos.
    tabela = mensal.pivot(index="ano", columns="mes", values="indice")
    correlacoes = []
    for ano in tabela.index:
        outros = tabela.drop(index=ano).mean()
        correlacoes.append(tabela.loc[ano].corr(outros))
    return {
        "perfil": perfil,
        "amplitude": float((perfil.max() - perfil.min()) * 100),
        "mes_max": int(perfil.idxmax()),
        "mes_min": int(perfil.idxmin()),
        "consistencia": float(np.nanmean(correlacoes)) if correlacoes else float("nan"),
    }


def correlacao(x: pd.Series, y: pd.Series, metodo: str = "pearson") -> float:
    """Pearson ou Spearman. Spearman = Pearson sobre os postos, o que dispensa a dependência do SciPy."""
    if metodo == "spearman":
        x, y = x.rank(), y.rank()
    return float(x.corr(y))


def destaques(df: pd.DataFrame) -> list[str]:
    """Frases interpretativas que se ajustam ao recorte selecionado."""
    k = calcular_kpis(df)
    frases = [
        f"O recorte soma **{formatar_energia(k['producao'])}** produzidos e **{formatar_energia(k['consumo'])}** consumidos: "
        f"a produção cobre **{formatar_pct(k['cobertura'])}** do consumo.",
        f"**{k['fonte'][0]}** é a fonte predominante, com **{formatar_pct(k['fonte'][1])}** da produção, e as fontes "
        f"renováveis respondem por **{formatar_pct(k['renovavel'])}** do total.",
        f"**{k['estado'][1]} ({k['estado'][0]})** lidera o ranking estadual com {formatar_energia(k['estado'][2])}; "
        f"**{k['regiao'][0]}** é a região que mais produz.",
        f"As emissões somam **{formatar_co2(k['emissao'])} de CO₂**, uma intensidade média de "
        f"{formatar_numero(k['intensidade'] * 1000, 0)} kg por MWh.",
    ]
    if df["ano"].nunique() >= 2:
        anual = serie_anual(df)
        anos = int(anual["ano"].iloc[-1] - anual["ano"].iloc[0])
        cagr = taxa_crescimento(anual["producao_mwh"].iloc[0], anual["producao_mwh"].iloc[-1], anos)
        frases.append(
            f"A produção cresceu em média **{formatar_pct(cagr, 2)} ao ano** entre {anual['ano'].iloc[0]} e "
            f"{anual['ano'].iloc[-1]}."
        )
    return frases


def classificar_correlacao(r: float) -> str:
    if math.isnan(r):
        return "indefinida"
    forca = abs(r)
    if forca < 0.1:
        return "desprezível"
    if forca < 0.3:
        return "fraca"
    if forca < 0.5:
        return "moderada"
    return "forte"
