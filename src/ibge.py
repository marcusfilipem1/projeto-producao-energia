"""Consumo da API pública de serviços de dados do IBGE com Requests.

Duas fontes externas complementam o CSV:
- localidades: nome oficial, código IBGE e região de cada estado;
- malhas: contorno geográfico das UFs (GeoJSON) usado no mapa interativo.

Se a API estiver fora do ar, usamos a última cópia salva em dados/ para que o
dashboard continue funcionando.
"""

from __future__ import annotations

import json

import pandas as pd
import requests

from src.config import CAMINHO_ESTADOS, CAMINHO_MALHA

URL_ESTADOS = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
URL_MALHA = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
PARAMS_MALHA = {"formato": "application/vnd.geo+json", "intrarregiao": "UF", "qualidade": "minima"}
TIMEOUT = 15


def buscar_estados() -> tuple[pd.DataFrame, str]:
    """Retorna a tabela de estados e a origem dos dados ("API IBGE" ou "cache local")."""
    try:
        resposta = requests.get(URL_ESTADOS, timeout=TIMEOUT)
        resposta.raise_for_status()
        registros = [
            {"codigo_ibge": e["id"], "uf": e["sigla"], "nome": e["nome"], "regiao": e["regiao"]["nome"]}
            for e in resposta.json()
        ]
        registros.sort(key=lambda e: e["uf"])
        CAMINHO_ESTADOS.write_text(json.dumps(registros, ensure_ascii=False, indent=1), encoding="utf-8")
        origem = "API IBGE"
    except (requests.RequestException, ValueError, KeyError):
        registros = json.loads(CAMINHO_ESTADOS.read_text(encoding="utf-8"))
        origem = "cache local"
    return pd.DataFrame(registros), origem


def _area_assinada(anel: list) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(anel, anel[1:] + anel[:1])) / 2


def _reorientar(malha: dict) -> dict:
    """Ajusta a orientação dos polígonos para o Plotly.

    A API do IBGE segue a RFC 7946 (contorno externo anti-horário), mas o mapa do Plotly
    espera o contorno externo no sentido horário; sem o ajuste ele pinta o "lado de fora"
    de cada estado e o mapa vira um retângulo preenchido.
    """
    for feicao in malha["features"]:
        geometria = feicao["geometry"]
        poligonos = [geometria["coordinates"]] if geometria["type"] == "Polygon" else geometria["coordinates"]
        for poligono in poligonos:
            for i, anel in enumerate(poligono):
                externo = i == 0
                if (_area_assinada(anel) > 0) == externo:  # externo deve ser horário (área < 0); buracos, anti-horário
                    anel.reverse()
    return malha


def buscar_malha_ufs() -> tuple[dict, str]:
    """Retorna o GeoJSON das UFs (propriedade `codarea` = código IBGE) e a origem."""
    try:
        resposta = requests.get(URL_MALHA, params=PARAMS_MALHA, timeout=TIMEOUT)
        resposta.raise_for_status()
        malha = resposta.json()
        CAMINHO_MALHA.write_text(json.dumps(malha), encoding="utf-8")
        origem = "API IBGE"
    except (requests.RequestException, ValueError):
        malha = json.loads(CAMINHO_MALHA.read_text(encoding="utf-8"))
        origem = "cache local"
    return _reorientar(malha), origem
