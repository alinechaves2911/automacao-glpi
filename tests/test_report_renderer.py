"""
tests/test_report_renderer.py

Cobre services/report_renderer.py: formatação de horas/percentual,
normalização de floats inteiros, extração de KPIs e o comportamento
com DataFrame vazio (item do checklist do README: "Validar
comportamento quando uma query retorna DataFrame vazio").
"""
import pandas as pd
import pytest

from services import report_renderer as rr


def test_normalizar_floats_inteiros_converte_coluna_toda_inteira():
    df = pd.DataFrame({"qtd": [1.0, 2.0, 3.0], "media": [1.5, 2.0, 3.25]})
    resultado = rr.normalizar_floats_inteiros(df.copy())
    assert str(resultado["qtd"].dtype) == "Int64"
    # coluna com valor não-inteiro não deve ser convertida
    assert str(resultado["media"].dtype) == "float64"


def test_normalizar_floats_inteiros_com_nan_no_meio():
    df = pd.DataFrame({"qtd": [1.0, None, 3.0]})
    resultado = rr.normalizar_floats_inteiros(df.copy())
    assert str(resultado["qtd"].dtype) == "Int64"
    assert pd.isna(resultado["qtd"].iloc[1])


@pytest.mark.parametrize("valor,esperado", [
    (0, "0h 00min"),
    (1.5, "1h 30min"),
    (88.5, "88h 30min"),
    (2.999, "3h 00min"),  # arredondamento de minutos não pode estourar pra 60min
    (None, "-"),
])
def test_horas_para_texto(valor, esperado):
    assert rr._horas_para_texto(valor) == esperado


def test_formatar_colunas_horas_nao_altera_df_original():
    df = pd.DataFrame({"tempo_medio": [1.5, 2.0]})
    resultado = rr.formatar_colunas_horas(df, ["tempo_medio"])
    assert resultado["tempo_medio"].tolist() == ["1h 30min", "2h 00min"]
    # df original preserva o valor numérico puro (usado depois no Excel)
    assert df["tempo_medio"].tolist() == [1.5, 2.0]


def test_formatar_colunas_horas_coluna_ausente_nao_quebra():
    df = pd.DataFrame({"outra_coluna": [1, 2]})
    resultado = rr.formatar_colunas_horas(df, ["tempo_medio_inexistente"])
    assert list(resultado.columns) == ["outra_coluna"]


def test_formatar_colunas_percentual():
    df = pd.DataFrame({"percentual_sla": [95.5, None]})
    resultado = rr.formatar_colunas_percentual(df, ["percentual_sla"])
    assert resultado["percentual_sla"].tolist() == ["95.5%", "-"]


def test_extrair_kpis_dataset_vazio_retorna_zero():
    dfs = {"situacao_atual": pd.DataFrame(columns=["total_ativos"])}
    cfg = {"kpis": {"total_ativos_kpi": ("situacao_atual", "total_ativos")}}
    kpis = rr.extrair_kpis_do_relatorio(dfs, cfg)
    assert kpis == {"total_ativos_kpi": 0}


def test_extrair_kpis_dataset_ausente_retorna_zero():
    dfs = {}
    cfg = {"kpis": {"total_ativos_kpi": ("nao_existe", "total_ativos")}}
    kpis = rr.extrair_kpis_do_relatorio(dfs, cfg)
    assert kpis == {"total_ativos_kpi": 0}


def test_extrair_kpis_valor_float_inteiro_vira_int():
    dfs = {"situacao_atual": pd.DataFrame({"total_ativos": [24.0]})}
    cfg = {"kpis": {"total_ativos_kpi": ("situacao_atual", "total_ativos")}}
    kpis = rr.extrair_kpis_do_relatorio(dfs, cfg)
    assert kpis == {"total_ativos_kpi": 24}
    assert isinstance(kpis["total_ativos_kpi"], int)


def test_montar_tabelas_html_dataset_vazio_vira_none():
    """
    Documenta o comportamento atual para DataFrame vazio: a tabela HTML
    fica None (o template Jinja decide o que mostrar, ex: "sem chamados
    no período" — ver templates/*.html), em vez de gerar um <table>
    vazio ou quebrar a geração do relatório inteiro.
    """
    dfs = {"chamados": pd.DataFrame(columns=["chamado_id", "titulo"])}
    cfg = {"tabelas": ["chamados"]}
    tabelas = rr.montar_tabelas_html(dfs, cfg)
    assert tabelas == {"chamados": None}


def test_montar_tabelas_html_dataset_nao_listado_e_ignorado():
    dfs = {"chamados": pd.DataFrame({"chamado_id": [1]})}
    cfg = {"tabelas": ["outro_dataset_nao_presente"]}
    tabelas = rr.montar_tabelas_html(dfs, cfg)
    assert tabelas == {}


def test_montar_tabelas_html_aplica_rotulo_de_coluna():
    dfs = {"chamados": pd.DataFrame({"chamado_id": [1], "tecnico": ["Fulano"]})}
    cfg = {"tabelas": ["chamados"]}
    tabelas = rr.montar_tabelas_html(dfs, cfg)
    assert "Chamado" in tabelas["chamados"]  # COLUNAS_LABEL["chamado_id"]
    assert "Técnico" in tabelas["chamados"]  # COLUNAS_LABEL["tecnico"]


def test_montar_dados_por_grupo_dataset_vazio_vira_lista_vazia():
    dfs = {"resumo_geral": pd.DataFrame(columns=["grupo", "total"])}
    dados = rr.montar_dados_por_grupo(dfs, ["resumo_geral"])
    assert dados == {"resumo_geral": []}


def test_montar_dados_por_grupo_converte_para_lista_de_dicts():
    dfs = {"resumo_geral": pd.DataFrame({"grupo": ["Infra"], "total": [10]})}
    dados = rr.montar_dados_por_grupo(dfs, ["resumo_geral"])
    assert dados == {"resumo_geral": [{"grupo": "Infra", "total": 10}]}
