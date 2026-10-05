"""Componentes visuais reaproveitados pelas páginas do dashboard."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from src.config import ALUNO, AVALIACAO, DISCIPLINA, PROFESSOR
from src.graficos import CONFIG_PLOTLY


def contexto() -> dict:
    """Dados e filtros preparados pelo app.py (entrypoint) antes de cada página rodar."""
    return st.session_state["ctx"]


def mostrar(fig: plt.Figure) -> None:
    """Renderiza uma figura Matplotlib/Seaborn e libera a memória em seguida."""
    st.pyplot(fig, width="stretch")
    plt.close(fig)


def grafico(fig) -> None:
    """Renderiza uma figura Plotly com a barra de ferramentas enxuta."""
    st.plotly_chart(fig, config=CONFIG_PLOTLY)


def cabecalho(titulo: str, subtitulo: str) -> None:
    st.title(titulo)
    st.caption(subtitulo)


def identificacao() -> None:
    with st.container(border=True):
        c1, c2, c3 = st.columns([2.2, 1.2, 1.2])
        c1.markdown(f"**Disciplina**  \n{DISCIPLINA}")
        c2.markdown(f"**Professor**  \n{PROFESSOR}")
        c3.markdown(f"**Aluno**  \n{ALUNO}")


def credito_sidebar() -> None:
    st.sidebar.divider()
    st.sidebar.caption(
        f"**{AVALIACAO}**  \n{DISCIPLINA}  \n\n**Professor:** {PROFESSOR}  \n**Aluno:** {ALUNO}"
    )


def resumo_filtro(n_registros: int, total: int) -> None:
    st.caption(f"Recorte atual: **{n_registros:,}** de {total:,} registros. Ajuste os filtros na barra lateral.".replace(",", "."))


def interpretacao(texto: str) -> None:
    st.info(texto, icon=":material/lightbulb:")
