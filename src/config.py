"""Constantes compartilhadas pelo dashboard: identificação, caminhos, classificação das fontes e paleta."""

from pathlib import Path

# ---------------- Identificação acadêmica ----------------
TITULO = "Produção de Energia no Brasil (2015–2024)"
DISCIPLINA = "Linguagem de Programação — Análise e Visualização de Dados com Python"
PROFESSOR = "Alexandre Neves Louzada"
ALUNO = "Enzo Ribas Torres"
AVALIACAO = "Projeto G1 — Tema 6"

# ---------------- Caminhos ----------------
BASE_DIR = Path(__file__).resolve().parent.parent
DIR_DADOS = BASE_DIR / "dados"
CAMINHO_CSV = DIR_DADOS / "simulacao_producao_energia_brasil.csv"
CAMINHO_ESTADOS = DIR_DADOS / "ibge_estados.json"
CAMINHO_MALHA = DIR_DADOS / "malha_ufs_brasil.geojson"
CAMINHO_BANCO = BASE_DIR / "database" / "producao_energia.sqlite"

# ---------------- Fontes de energia ----------------
ORDEM_FONTES = ["Hidrelétrica", "Eólica", "Solar", "Biomassa", "Nuclear", "Termelétrica"]
# Classificação técnica: nuclear não é renovável (usa urânio, um recurso finito), embora tenha baixa emissão.
FONTES_RENOVAVEIS = {"Hidrelétrica", "Eólica", "Solar", "Biomassa"}
ORDEM_CLASSES = ["Renovável", "Nuclear", "Fóssil"]
CLASSE_FONTE = {f: "Renovável" for f in FONTES_RENOVAVEIS} | {"Nuclear": "Nuclear", "Termelétrica": "Fóssil"}

ORDEM_REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
ORDEM_DEMANDA = ["Baixo", "Médio", "Alto", "Crítico"]
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# ---------------- Paleta ----------------
# Cores categóricas fixas por fonte (validadas para daltonismo na ordem acima): a cor acompanha a fonte, nunca o ranking.
CORES_FONTE = {
    "Hidrelétrica": "#2a78d6",
    "Eólica": "#1baf7a",
    "Solar": "#eda100",
    "Biomassa": "#008300",
    "Nuclear": "#4a3aa7",
    "Termelétrica": "#eb6834",
}
CORES_CLASSE = {"Renovável": "#1baf7a", "Nuclear": "#4a3aa7", "Fóssil": "#eb6834"}
CORES_REGIAO = {
    "Norte": "#2a78d6",
    "Nordeste": "#eb6834",
    "Centro-Oeste": "#1baf7a",
    "Sudeste": "#eda100",
    "Sul": "#e87ba4",
}
# Nível de demanda é um status ordinal: sempre acompanhado do rótulo, nunca só pela cor.
CORES_DEMANDA = {"Baixo": "#0ca30c", "Médio": "#fab219", "Alto": "#ec835a", "Crítico": "#d03b3b"}
COR_DESTAQUE = "#2a78d6"
COR_CONSUMO = "#eb6834"
ESCALA_SEQUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

TINTA_PRIMARIA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_SUAVE = "#898781"
GRADE = "#e1e0d9"
COR_NEUTRA = "#c3c2b7"
SUPERFICIE = "#fcfcfb"
