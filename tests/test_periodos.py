"""
tests/test_periodos.py

Cobre services/periodos.py, especificamente as bordas de calendário que
motivaram avisos no README (virada de ano, ano bissexto, mês com menos
dias) — esse módulo já teve bugs de "corte de data" no passado, então
merece testes que fixem o comportamento esperado e peguem regressão.

Rodar com:
    pip install pytest --break-system-packages   # se ainda não tiver
    pytest tests/ -v
"""
from datetime import date, timedelta

import pytest

from services import periodos


class _DataFixa(date):
    """
    Subclasse de date só para sobrescrever today() com um valor fixo nos
    testes, via monkeypatch. Mantém o resto do comportamento de 'date'
    intacto (é o que services/periodos.py usa internamente para somar/
    subtrair timedelta e construir novas datas).
    """
    _hoje_fixo = date(2026, 1, 1)

    @classmethod
    def today(cls):
        return cls._hoje_fixo


def _fixar_hoje(monkeypatch, ano, mes, dia):
    _DataFixa._hoje_fixo = date(ano, mes, dia)
    monkeypatch.setattr(periodos, "date", _DataFixa)


# ---------------------------------------------------------------------
# semana_anterior()
# ---------------------------------------------------------------------

def test_semana_anterior_caso_simples(monkeypatch):
    # Segunda 2026-08-10 -> semana anterior: 2026-08-03 (seg) a 2026-08-09 (dom)
    _fixar_hoje(monkeypatch, 2026, 8, 10)
    inicio, fim = periodos.semana_anterior()
    assert inicio == date(2026, 8, 3)
    assert fim == date(2026, 8, 9)
    assert inicio.weekday() == 0  # segunda
    assert fim.weekday() == 6  # domingo


def test_semana_anterior_hoje_no_meio_da_semana(monkeypatch):
    # Quarta-feira: a semana "anterior" deve ser a semana completa
    # passada, não incluir nenhum dia da semana atual.
    _fixar_hoje(monkeypatch, 2026, 8, 12)  # quarta
    inicio, fim = periodos.semana_anterior()
    assert inicio == date(2026, 8, 3)
    assert fim == date(2026, 8, 9)


def test_semana_anterior_cruzando_virada_de_mes(monkeypatch):
    # Hoje 2026-09-07 (segunda) -> semana anterior cruza agosto/setembro
    _fixar_hoje(monkeypatch, 2026, 9, 7)
    inicio, fim = periodos.semana_anterior()
    assert inicio == date(2026, 8, 31)
    assert fim == date(2026, 9, 6)


def test_semana_anterior_cruzando_virada_de_ano(monkeypatch):
    # Hoje 2026-01-05 (segunda) -> semana anterior cai em dez/2025
    _fixar_hoje(monkeypatch, 2026, 1, 5)
    inicio, fim = periodos.semana_anterior()
    assert inicio == date(2025, 12, 29)
    assert fim == date(2026, 1, 4)
    assert inicio.year == 2025 and fim.year == 2026


# ---------------------------------------------------------------------
# mes_anterior()
# ---------------------------------------------------------------------

def test_mes_anterior_caso_simples(monkeypatch):
    _fixar_hoje(monkeypatch, 2026, 9, 1)
    inicio, fim = periodos.mes_anterior()
    assert inicio == date(2026, 8, 1)
    assert fim == date(2026, 8, 31)


def test_mes_anterior_virada_de_ano(monkeypatch):
    # Hoje em janeiro -> mês anterior é dezembro do ANO PASSADO, não
    # "mês 0" do ano atual (esse é o off-by-one clássico desse tipo de
    # cálculo).
    _fixar_hoje(monkeypatch, 2026, 1, 15)
    inicio, fim = periodos.mes_anterior()
    assert inicio == date(2025, 12, 1)
    assert fim == date(2025, 12, 31)


def test_mes_anterior_marco_com_fevereiro_bissexto(monkeypatch):
    # 2028 é bissexto -> fevereiro tem 29 dias. Hoje em março deve
    # capturar fevereiro completo, até o dia 29.
    _fixar_hoje(monkeypatch, 2028, 3, 10)
    inicio, fim = periodos.mes_anterior()
    assert inicio == date(2028, 2, 1)
    assert fim == date(2028, 2, 29)


def test_mes_anterior_marco_com_fevereiro_nao_bissexto(monkeypatch):
    # 2026 não é bissexto -> fevereiro tem 28 dias.
    _fixar_hoje(monkeypatch, 2026, 3, 10)
    inicio, fim = periodos.mes_anterior()
    assert inicio == date(2026, 2, 1)
    assert fim == date(2026, 2, 28)


def test_mes_anterior_dia_31_para_mes_de_30(monkeypatch):
    # Hoje 1º de maio (31 dias) -> mês anterior é abril (30 dias); o
    # cálculo não deve "vazar" pra maio nem ficar em 31 de abril
    # inexistente.
    _fixar_hoje(monkeypatch, 2026, 5, 1)
    inicio, fim = periodos.mes_anterior()
    assert inicio == date(2026, 4, 1)
    assert fim == date(2026, 4, 30)


# ---------------------------------------------------------------------
# ano_anterior()
# ---------------------------------------------------------------------

def test_ano_anterior_caso_simples(monkeypatch):
    _fixar_hoje(monkeypatch, 2026, 8, 10)
    inicio, fim = periodos.ano_anterior()
    assert inicio == date(2025, 1, 1)
    assert fim == date(2025, 12, 31)


def test_ano_anterior_em_primeiro_de_janeiro(monkeypatch):
    # Caso limite: hoje é 1º de janeiro, ano anterior ainda deve ser o
    # ano completo que terminou ontem.
    _fixar_hoje(monkeypatch, 2026, 1, 1)
    inicio, fim = periodos.ano_anterior()
    assert inicio == date(2025, 1, 1)
    assert fim == date(2025, 12, 31)


def test_ano_anterior_bissexto(monkeypatch):
    # 2028 é bissexto; o ano anterior a ele (2027) não é — só garante
    # que a função não assume 366 dias por padrão em nenhum lugar.
    _fixar_hoje(monkeypatch, 2028, 6, 1)
    inicio, fim = periodos.ano_anterior()
    assert inicio == date(2027, 1, 1)
    assert fim == date(2027, 12, 31)
    assert (fim - inicio).days == 364  # 2027 tem 365 dias corridos


# ---------------------------------------------------------------------
# resolver_periodo() — fim_exclusivo e nomes inválidos/sem período
# ---------------------------------------------------------------------

@pytest.mark.parametrize("nome_periodo,funcao", [
    ("semana_anterior", periodos.semana_anterior),
    ("mes_anterior", periodos.mes_anterior),
    ("ano_anterior", periodos.ano_anterior),
])
def test_resolver_periodo_fim_exclusivo_e_um_dia_apos_fim(monkeypatch, nome_periodo, funcao):
    _fixar_hoje(monkeypatch, 2026, 8, 10)
    inicio, fim, fim_exclusivo = periodos.resolver_periodo(nome_periodo)
    inicio_esperado, fim_esperado = funcao()
    assert inicio == inicio_esperado
    assert fim == fim_esperado
    # fim_exclusivo precisa ser fim + 1 dia, nunca igual a fim (senão o
    # filtro "data < :fim_exclusivo" corta o último dia de novo — o bug
    # que esse campo existe justamente para evitar).
    assert fim_exclusivo == fim + timedelta(days=1)


def test_resolver_periodo_atual_retorna_none(monkeypatch):
    # "atual" (usado por relatórios sem filtro de data, ex: críticos)
    # não deve calcular nenhum período.
    _fixar_hoje(monkeypatch, 2026, 8, 10)
    inicio, fim, fim_exclusivo = periodos.resolver_periodo("atual")
    assert (inicio, fim, fim_exclusivo) == (None, None, None)


def test_resolver_periodo_nome_desconhecido_nao_quebra(monkeypatch):
    # Nome de período não reconhecido (ex: erro de digitação em
    # config/reports.py) deve cair no mesmo caminho de "sem filtro",
    # não lançar exceção — quem depende disso decide o que fazer com
    # (None, None, None), mas o pipeline não deve cair por isso.
    _fixar_hoje(monkeypatch, 2026, 8, 10)
    inicio, fim, fim_exclusivo = periodos.resolver_periodo("periodo_que_nao_existe")
    assert (inicio, fim, fim_exclusivo) == (None, None, None)


def test_resolver_periodo_fim_exclusivo_vira_virada_de_ano(monkeypatch):
    # Caso específico: mes_anterior() em janeiro devolve dezembro/ano
    # passado — fim_exclusivo precisa virar 1º de janeiro do ANO ATUAL,
    # não "32 de dezembro" nem qualquer outra coisa fora do calendário.
    _fixar_hoje(monkeypatch, 2026, 1, 10)
    inicio, fim, fim_exclusivo = periodos.resolver_periodo("mes_anterior")
    assert fim == date(2025, 12, 31)
    assert fim_exclusivo == date(2026, 1, 1)
