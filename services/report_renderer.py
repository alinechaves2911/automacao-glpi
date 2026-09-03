"""
services/report_renderer.py

Transforma os DataFrames já executados (services/report_runner.py) no
material que vai para o template do e-mail: tabelas HTML, KPIs de card
único e colunas formatadas como "Xh Ymin". Não sabe nada sobre SQL,
Excel, gráficos ou SMTP — só formatação/apresentação de dados.

Extraído do antigo main.py, que fazia isso junto com orquestração,
geração de gráficos, Excel e envio de e-mail no mesmo arquivo.
"""
import pandas as pd

from config.reports import COLUNAS_LABEL
from services.logger import logger

def normalizar_floats_inteiros(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte colunas float que só contêm valores inteiros (ex: 3.0, 4.0)
    para Int64 (tipo pandas que aceita NaN), evitando que números como
    contagens apareçam como "3.0" nas tabelas e no Excel.
    """
    for col in df.select_dtypes(include=["float64"]).columns:
        if df[col].dropna().apply(float.is_integer).all():
            df[col] = df[col].astype("Int64")
    return df


def _horas_para_texto(valor) -> str:
    """Converte horas decimais (ex: 88.5) em texto 'Xh Ymin' (ex: '88h 30min')."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "-"
    h = int(valor)
    m = round((valor - h) * 60)
    if m == 60:  # arredondamento pode estourar pra 60min
        h += 1
        m = 0
    return f"{h}h {m:02d}min"


def formatar_colunas_horas(df: pd.DataFrame, colunas: list) -> pd.DataFrame:
    """
    Aplica _horas_para_texto() nas colunas indicadas de um DataFrame,
    retornando uma cópia (não altera o df original, que ainda pode ser
    usado no Excel com o valor numérico puro).
    """
    df = df.copy()
    for col in colunas:
        if col in df.columns:
            df[col] = df[col].apply(_horas_para_texto)
        else:
            logger.info(f"Coluna de horas '{col}' não encontrada no dataset, formatação pulada.")
    return df


def formatar_colunas_percentual(df: pd.DataFrame, colunas: list) -> pd.DataFrame:
    """
    Aplica sufixo '%' nas colunas de percentual indicadas, retornando uma
    cópia (não altera o df original, que ainda pode ser usado no Excel
    com o valor numérico puro).

    Portado do main.py legado durante a unificação com reporter_runner.py
    (essa função existia em main.py mas não em report_renderer.py, então
    o relatório da diretoria — o único que usa "colunas_percentual" em
    reports.py — quebraria silenciosamente se reporter_runner.py fosse
    usado como está).
    """
    df = df.copy()
    for col in colunas:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: "-" if pd.isna(v) else f"{v}%")
        else:
            logger.info(f"Coluna de percentual '{col}' não encontrada no dataset, formatação pulada.")
    return df


def montar_dados_por_grupo(dfs: dict, nomes_datasets: list) -> dict:
    """
    Converte datasets agrupados por 'grupo' em uma lista de dicts, pronta
    pra iterar no Jinja (ex: {% for linha in resumo_geral %}).

    Portado do main.py legado durante a unificação com reporter_runner.py.
    Hoje só o relatório "atendimento_mensal_diretoria" usa isso (via
    ["resumo_geral", "sla_geral"] fixo em main.py) — se outro relatório
    precisar do mesmo padrão no futuro, considere adicionar uma chave
    "dados_por_grupo": [...] em reports.py em vez de manter a lista fixa
    aqui.
    """
    dados = {}
    for nome in nomes_datasets:
        df = dfs.get(nome)
        if df is not None and not df.empty:
            dados[nome] = df.to_dict("records")
        else:
            dados[nome] = []
    return dados


def extrair_kpis_do_relatorio(dfs: dict, cfg: dict) -> dict:
    """
    Lê a config 'kpis' do relatório (opcional) e extrai valores individuais
    de datasets de 1 linha só, para uso em cards no template
    (ex: {{ situacao_total_ativos }}).

    Formato esperado em reports.py:
        "kpis": {
            "situacao_total_ativos": ("situacao_atual", "total_ativos"),
            "resumo_abertos": ("resumo_semanal", "abertos_na_semana"),
        }
    """
    kpis = {}
    for nome_var, (dataset, coluna) in cfg.get("kpis", {}).items():
        df = dfs.get(dataset)
        if df is None or df.empty or coluna not in df.columns:
            kpis[nome_var] = 0
            continue
        valor = df[coluna].iloc[0]
        if valor is None:
            kpis[nome_var] = 0
        elif isinstance(valor, float) and valor.is_integer():
            kpis[nome_var] = int(valor)
        else:
            kpis[nome_var] = valor
    return kpis


def montar_tabelas_html(dfs: dict, cfg: dict) -> dict:
    """
    Monta o HTML de cada tabela listada em cfg["tabelas"], aplicando:
      - formatação de horas (cfg["colunas_horas"], se houver);
      - rótulos legíveis via COLUNAS_LABEL (ex: 'chamado_id' -> 'Chamado').

    "colunas_horas" (opcional em reports.py) mapeia dataset -> lista de colunas que
    devem sair formatadas como "Xh Ymin" na tabela do e-mail (o Excel continua com o
    valor numérico puro, pois usa 'dfs[nome]' original, não a cópia formatada aqui).

    "colunas_percentual" (opcional em reports.py) mapeia dataset -> lista de colunas
    numéricas que devem sair com sufixo "%" na tabela do e-mail, pelo mesmo motivo
    de "colunas_horas" acima. Usado hoje só pelo relatório da diretoria.
    """
    colunas_horas_cfg = cfg.get("colunas_horas", {})
    colunas_percentual_cfg = cfg.get("colunas_percentual", {})

    tabelas_html = {}
    for nome in cfg.get("tabelas", []):
        if nome not in dfs:
            continue
        df = dfs[nome]
        if df.empty:
            tabelas_html[nome] = None
            continue
        if nome in colunas_horas_cfg:
            df = formatar_colunas_horas(df, colunas_horas_cfg[nome])
        if nome in colunas_percentual_cfg:
            df = formatar_colunas_percentual(df, colunas_percentual_cfg[nome])
        tabelas_html[nome] = df.rename(columns=COLUNAS_LABEL).to_html(index=False, escape=False)
    return tabelas_html



