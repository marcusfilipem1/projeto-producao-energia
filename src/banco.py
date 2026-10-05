"""Persistência em SQLite com modelagem relacional via SQLAlchemy ORM.

Esquema (normalizado a partir do CSV + API do IBGE):

    regioes 1──N estados 1──N medicoes N──1 fontes_energia
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from src.config import CAMINHO_BANCO, CLASSE_FONTE, FONTES_RENOVAVEIS, ORDEM_FONTES


class Base(DeclarativeBase):
    pass


class Regiao(Base):
    __tablename__ = "regioes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(20), unique=True)
    estados: Mapped[list["Estado"]] = relationship(back_populates="regiao")


class Estado(Base):
    __tablename__ = "estados"

    uf: Mapped[str] = mapped_column(String(2), primary_key=True)
    nome: Mapped[str] = mapped_column(String(40))
    codigo_ibge: Mapped[int] = mapped_column(Integer, unique=True)
    regiao_id: Mapped[int] = mapped_column(ForeignKey("regioes.id"))
    regiao: Mapped[Regiao] = relationship(back_populates="estados")
    medicoes: Mapped[list["Medicao"]] = relationship(back_populates="estado")


class FonteEnergia(Base):
    __tablename__ = "fontes_energia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(20), unique=True)
    classe: Mapped[str] = mapped_column(String(12))
    renovavel: Mapped[bool] = mapped_column(Boolean)
    fator_emissao: Mapped[float] = mapped_column(Float)
    medicoes: Mapped[list["Medicao"]] = relationship(back_populates="fonte")


class Medicao(Base):
    __tablename__ = "medicoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uf: Mapped[str] = mapped_column(ForeignKey("estados.uf"), index=True)
    fonte_id: Mapped[int] = mapped_column(ForeignKey("fontes_energia.id"), index=True)
    data: Mapped[date] = mapped_column(Date, index=True)
    ano: Mapped[int] = mapped_column(Integer, index=True)
    mes: Mapped[int] = mapped_column(Integer)
    producao_mwh: Mapped[float] = mapped_column(Float)
    consumo_mwh: Mapped[float] = mapped_column(Float)
    capacidade_instalada: Mapped[float] = mapped_column(Float)
    emissao_co2: Mapped[float] = mapped_column(Float)
    custo_medio_mwh: Mapped[float] = mapped_column(Float)
    nivel_demanda: Mapped[str] = mapped_column(String(10))
    estado: Mapped[Estado] = relationship(back_populates="medicoes")
    fonte: Mapped[FonteEnergia] = relationship(back_populates="medicoes")


def construir_banco(df: pd.DataFrame, estados: pd.DataFrame) -> Engine:
    """Recria o banco SQLite a partir da base tratada e da tabela de estados do IBGE."""
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{CAMINHO_BANCO.as_posix()}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    estados = estados[estados["uf"].isin(df["uf"].unique())]
    fatores = (df.groupby("fonte_energia", observed=True)["emissao_co2"].sum()
               / df.groupby("fonte_energia", observed=True)["producao_mwh"].sum())

    with Session(engine) as sessao:
        regioes = {nome: Regiao(nome=nome) for nome in sorted(estados["regiao"].unique())}
        sessao.add_all(regioes.values())
        for linha in estados.itertuples():
            sessao.add(Estado(uf=linha.uf, nome=linha.nome, codigo_ibge=int(linha.codigo_ibge), regiao=regioes[linha.regiao]))

        fontes = {
            nome: FonteEnergia(nome=nome, classe=CLASSE_FONTE[nome], renovavel=nome in FONTES_RENOVAVEIS,
                               fator_emissao=round(float(fatores.get(nome, 0)), 4))
            for nome in ORDEM_FONTES if nome in set(df["fonte_energia"].astype(str))
        }
        sessao.add_all(fontes.values())
        sessao.flush()

        colunas = ["uf", "fonte_energia", "data", "ano", "mes", "producao_mwh", "consumo_mwh",
                   "capacidade_instalada", "emissao_co2", "custo_medio_mwh", "nivel_demanda"]
        registros = df[colunas].copy()
        registros["fonte_id"] = registros["fonte_energia"].astype(str).map({n: f.id for n, f in fontes.items()})
        registros["data"] = registros["data"].dt.date
        registros["nivel_demanda"] = registros["nivel_demanda"].astype(str)
        sessao.execute(Medicao.__table__.insert(), registros.drop(columns="fonte_energia").to_dict("records"))
        sessao.commit()
    return engine


def conectar_somente_leitura() -> Engine:
    """Conexão read-only: consultas livres digitadas no dashboard não conseguem alterar o banco."""
    return create_engine(f"sqlite:///file:{CAMINHO_BANCO.as_posix()}?mode=ro&uri=true")


CONSULTAS = {
    "Produção por região (JOIN entre 3 tabelas)": """
SELECT r.nome AS regiao,
       COUNT(DISTINCT e.uf) AS estados,
       ROUND(SUM(m.producao_mwh) / 1e6, 2) AS producao_twh,
       ROUND(SUM(m.producao_mwh) / 1e6 / COUNT(DISTINCT e.uf), 2) AS producao_media_por_uf_twh
FROM medicoes m
JOIN estados e ON e.uf = m.uf
JOIN regioes r ON r.id = e.regiao_id
GROUP BY r.nome
ORDER BY producao_twh DESC""",
    "Matriz energética por fonte": """
SELECT f.nome AS fonte, f.classe,
       ROUND(SUM(m.producao_mwh) / 1e6, 2) AS producao_twh,
       ROUND(100.0 * SUM(m.producao_mwh) / (SELECT SUM(producao_mwh) FROM medicoes), 2) AS participacao_pct,
       ROUND(SUM(m.emissao_co2) / 1e6, 2) AS emissao_mt
FROM medicoes m
JOIN fontes_energia f ON f.id = m.fonte_id
GROUP BY f.nome, f.classe
ORDER BY producao_twh DESC""",
    "Participação renovável por ano": """
SELECT m.ano,
       ROUND(100.0 * SUM(CASE WHEN f.renovavel THEN m.producao_mwh END) / SUM(m.producao_mwh), 2) AS renovavel_pct,
       ROUND(100.0 * SUM(CASE WHEN f.nome = 'Hidrelétrica' THEN m.producao_mwh END) / SUM(m.producao_mwh), 2) AS hidreletrica_pct
FROM medicoes m
JOIN fontes_energia f ON f.id = m.fonte_id
GROUP BY m.ano
ORDER BY m.ano""",
    "Ranking de estados produtores": """
SELECT e.uf, e.nome AS estado,
       ROUND(SUM(m.producao_mwh) / 1e6, 2) AS producao_twh,
       ROUND(SUM(m.consumo_mwh) / 1e6, 2) AS consumo_twh,
       ROUND(SUM(m.producao_mwh - m.consumo_mwh) / 1e6, 2) AS saldo_twh
FROM medicoes m
JOIN estados e ON e.uf = m.uf
GROUP BY e.uf, e.nome
ORDER BY producao_twh DESC""",
    "Meses com demanda crítica por estado": """
SELECT e.uf, COUNT(*) AS registros_criticos,
       ROUND(AVG(m.consumo_mwh / m.producao_mwh), 3) AS indice_demanda_medio
FROM medicoes m
JOIN estados e ON e.uf = m.uf
WHERE m.nivel_demanda = 'Crítico'
GROUP BY e.uf
ORDER BY registros_criticos DESC
LIMIT 10""",
}


def executar_consulta(engine: Engine, sql: str) -> pd.DataFrame:
    with engine.connect() as conexao:
        return pd.read_sql(text(sql), conexao)
