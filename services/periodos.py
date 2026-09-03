"""
services/periodos.py

Calcula os intervalos de data para os relatórios que dependem de
"semana anterior" ou "mês anterior" — evita fazer essa conta na mão
toda vez e reduz erro de off-by-one.
"""
from datetime import date, timedelta


def semana_anterior():
    """
    Retorna (data_inicio, data_fim) da semana anterior (segunda a domingo).
    Ex: se hoje é segunda 2026-08-10, retorna 2026-08-03 (seg) a 2026-08-09 (dom).
    """
    hoje = date.today()
    segunda_atual = hoje - timedelta(days=hoje.weekday())  # weekday(): segunda=0
    segunda_anterior = segunda_atual - timedelta(days=7)
    domingo_anterior = segunda_atual - timedelta(days=1)
    return segunda_anterior, domingo_anterior


def mes_anterior():
    """
    Retorna (data_inicio, data_fim) do mês anterior por completo.
    Ex: se hoje é 2026-09-01, retorna 2026-08-01 a 2026-08-31.
    """
    hoje = date.today()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
    primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
    return primeiro_dia_mes_anterior, ultimo_dia_mes_anterior

def ano_anterior():
    """
    Retorna (data_inicio, data_fim) do ano anterior por completo.
    Ex: se hoje é 2026-08-10, retorna 2025-01-01 a 2025-12-31.
    """
    hoje = date.today()
    ano_passado = hoje.year - 1
    inicio = date(ano_passado, 1, 1)
    fim = date(ano_passado, 12, 31)
    return inicio, fim

def resolver_periodo(nome_periodo):
    """
    Dado o nome do período configurado em config/reports.py, retorna
    (data_inicio, data_fim, data_fim_exclusivo) ou (None, None, None)
    se não precisar de filtro de data.

    data_fim_exclusivo = dia seguinte ao último dia do período, para
    uso em filtros "data >= :inicio AND data < :fim_exclusivo", que
    evitam o bug clássico de BETWEEN cortar registros do último dia
    quando a coluna é DATETIME (não DATE).
    """
    if nome_periodo == "semana_anterior":
        inicio, fim = semana_anterior()
    elif nome_periodo == "mes_anterior":
        inicio, fim = mes_anterior()
    elif nome_periodo == "ano_anterior":
        inicio, fim = ano_anterior()
    else:
        return None, None, None

    fim_exclusivo = fim + timedelta(days=1)
    return inicio, fim, fim_exclusivo

