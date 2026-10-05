"""Leitura, limpeza, engenharia de atributos e agregações da base de produção de energia."""

from __future__ import annotations

import pandas as pd

from src.config import CLASSE_FONTE, FONTES_RENOVAVEIS, MESES, ORDEM_CLASSES, ORDEM_DEMANDA, ORDEM_FONTES, ORDEM_REGIOES

COLUNAS_OBRIGATORIAS = [
    "ano", "mes", "data", "regiao", "uf", "fonte_energia", "producao_mwh", "consumo_mwh",
    "capacidade_instalada", "emissao_co2", "custo_medio_mwh", "percentual_renovavel", "nivel_demanda",
]
COLUNAS_NUMERICAS = [
    "ano", "mes", "producao_mwh", "consumo_mwh", "capacidade_instalada", "emissao_co2",
    "custo_medio_mwh", "percentual_renovavel",
]
COLUNAS_TEXTO = ["regiao", "uf", "fonte_energia", "nivel_demanda"]
CHAVE = ["data", "uf", "fonte_energia"]

# Valor mínimo que a simulação usa como "piso" de produção (aparece com capacidade 140 e emissão 4).
PISO_PRODUCAO = 100.0

# Faixas do nível de demanda, deduzidas da base: razão consumo ÷ produção.
FAIXAS_DEMANDA = [(0.85, "Baixo"), (1.00, "Médio"), (1.12, "Alto"), (float("inf"), "Crítico")]


def ler_csv(origem) -> pd.DataFrame:
    """Lê o CSV (caminho ou arquivo enviado) tratando o BOM do UTF-8."""
    df = pd.read_csv(origem, encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.lower()
    return df


def validar_colunas(df: pd.DataFrame) -> list[str]:
    """Retorna as colunas obrigatórias ausentes (lista vazia = base válida)."""
    return [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]


def classificar_demanda(indice: pd.Series) -> pd.Series:
    def classe(valor):
        for limite, nome in FAIXAS_DEMANDA:
            if valor < limite:
                return nome
        return "Crítico"

    return indice.map(classe)


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica a limpeza e devolve a base tratada junto com um relatório de cada etapa."""
    df = df.copy()
    relatorio = {"linhas_originais": len(df)}

    for col in COLUNAS_TEXTO:
        df[col] = df[col].astype("string").str.strip()
    df["uf"] = df["uf"].str.upper()
    for col in COLUNAS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    relatorio["valores_nulos"] = int(df[COLUNAS_OBRIGATORIAS].isna().sum().sum())
    df = df.dropna(subset=["ano", "mes", "uf", "fonte_energia", "producao_mwh"])

    # A data de referência deve corresponder ao ano e mês informados.
    divergente = (df["data"].dt.year != df["ano"]) | (df["data"].dt.month != df["mes"])
    relatorio["datas_corrigidas"] = int(divergente.sum())
    df.loc[divergente, "data"] = pd.to_datetime(dict(year=df["ano"], month=df["mes"], day=1))

    relatorio["duplicados_removidos"] = int(df.duplicated(subset=CHAVE).sum())
    df = df.drop_duplicates(subset=CHAVE, keep="first")

    numericas = ["producao_mwh", "consumo_mwh", "capacidade_instalada", "emissao_co2", "custo_medio_mwh"]
    invalidos = (df[numericas] < 0).any(axis=1) | (df["producao_mwh"] > df["capacidade_instalada"])
    relatorio["registros_invalidos"] = int(invalidos.sum())
    df = df[~invalidos]

    # Valores no piso artificial da simulação: mantidos (impacto desprezível), mas sinalizados.
    df["valor_piso"] = df["producao_mwh"] <= PISO_PRODUCAO
    relatorio["valores_piso"] = int(df["valor_piso"].sum())
    relatorio["fonte_piso"] = ", ".join(sorted(df.loc[df["valor_piso"], "fonte_energia"].unique()))

    # O CSV marca nuclear com 95% renovável; tecnicamente ela é não renovável (de baixa emissão).
    relatorio["classificacao_corrigida"] = int(
        ((df["fonte_energia"] == "Nuclear") & (df["percentual_renovavel"] > 50)).sum()
    )

    # Conferência: o nível de demanda segue as faixas de consumo ÷ produção.
    esperado = classificar_demanda(df["consumo_mwh"] / df["producao_mwh"])
    relatorio["demanda_reclassificada"] = int((esperado != df["nivel_demanda"]).sum())
    df["nivel_demanda"] = esperado

    for col in ["ano", "mes"]:
        df[col] = df[col].astype(int)

    relatorio["linhas_finais"] = len(df)
    return df.reset_index(drop=True), relatorio


def criar_atributos(df: pd.DataFrame, estados: pd.DataFrame | None = None) -> pd.DataFrame:
    """Engenharia de atributos: classe da fonte, indicadores de eficiência, calendário e dados do IBGE."""
    df = df.copy()

    for col in COLUNAS_TEXTO:
        df[col] = df[col].astype(str)

    df["renovavel"] = df["fonte_energia"].isin(FONTES_RENOVAVEIS)
    df["classe_fonte"] = pd.Categorical(df["fonte_energia"].map(CLASSE_FONTE), categories=ORDEM_CLASSES, ordered=True)
    df["saldo_mwh"] = df["producao_mwh"] - df["consumo_mwh"]
    df["indice_demanda"] = df["consumo_mwh"] / df["producao_mwh"]
    df["fator_emissao"] = df["emissao_co2"] / df["producao_mwh"]
    df["fator_capacidade"] = df["producao_mwh"] / df["capacidade_instalada"]

    df["ano_mes"] = df["data"].dt.strftime("%Y-%m")
    df["trimestre"] = df["data"].dt.quarter
    df["nome_mes"] = pd.Categorical(df["mes"].map(lambda m: MESES[m - 1]), categories=MESES, ordered=True)
    # Regime de chuvas predominante no Sudeste/Centro-Oeste, onde ficam os grandes reservatórios.
    df["periodo_hidrologico"] = df["mes"].map(lambda m: "Chuvoso (nov–abr)" if m in (11, 12, 1, 2, 3, 4) else "Seco (mai–out)")

    df["regiao"] = pd.Categorical(df["regiao"], categories=ORDEM_REGIOES, ordered=True)
    df["fonte_energia"] = pd.Categorical(df["fonte_energia"], categories=ORDEM_FONTES, ordered=True)
    df["nivel_demanda"] = pd.Categorical(df["nivel_demanda"], categories=ORDEM_DEMANDA, ordered=True)

    if estados is not None:
        df = df.merge(estados[["uf", "nome", "codigo_ibge"]].rename(columns={"nome": "nome_uf"}), on="uf", how="left")

    return df


def aplicar_filtros(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    """Aplica os filtros escolhidos na barra lateral."""
    ano_ini, ano_fim = filtros["anos"]
    mascara = (
        df["ano"].between(ano_ini, ano_fim)
        & df["mes"].isin(filtros["meses"])
        & df["regiao"].isin(filtros["regioes"])
        & df["uf"].isin(filtros["ufs"])
        & df["fonte_energia"].isin(filtros["fontes"])
        & df["nivel_demanda"].isin(filtros["demandas"])
    )
    return df[mascara]


def somar(df: pd.DataFrame, por, colunas=("producao_mwh", "consumo_mwh", "emissao_co2")) -> pd.DataFrame:
    return df.groupby(por, observed=True)[list(colunas)].sum().reset_index()


def participacao(df: pd.DataFrame, por: str = "fonte_energia") -> pd.DataFrame:
    """Participação de cada categoria na produção total (%)."""
    agg = somar(df, por, ["producao_mwh"])
    agg["participacao"] = agg["producao_mwh"] / agg["producao_mwh"].sum() * 100
    return agg.sort_values("producao_mwh", ascending=False)


def percentual_renovavel(df: pd.DataFrame) -> float:
    total = df["producao_mwh"].sum()
    return float(df.loc[df["renovavel"], "producao_mwh"].sum() / total * 100) if total else float("nan")


def formatar_numero(valor: float, casas: int = 0) -> str:
    """Formata números no padrão brasileiro (1.234,5)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_pct(valor: float, casas: int = 1) -> str:
    return f"{formatar_numero(valor, casas)}%"


def formatar_energia(mwh: float) -> str:
    """Escolhe a unidade mais legível: MWh, GWh ou TWh."""
    if abs(mwh) >= 1e6:
        return f"{formatar_numero(mwh / 1e6, 1)} TWh"
    if abs(mwh) >= 1e3:
        return f"{formatar_numero(mwh / 1e3, 1)} GWh"
    return f"{formatar_numero(mwh, 0)} MWh"


def formatar_co2(toneladas: float) -> str:
    if abs(toneladas) >= 1e6:
        return f"{formatar_numero(toneladas / 1e6, 2)} Mt"
    if abs(toneladas) >= 1e3:
        return f"{formatar_numero(toneladas / 1e3, 1)} mil t"
    return f"{formatar_numero(toneladas, 0)} t"
