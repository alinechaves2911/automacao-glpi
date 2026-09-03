"""
services/reporter_runner.py

Orquestra a execução de UM relatório: queries -> Excel -> gráficos ->
KPIs/tabelas -> e-mail -> limpeza.

Suporta dois tipos de relatório:

1. Normal — uma execução, um conjunto de datasets, um Excel, um e-mail.
2. Por grupo — executa as queries uma vez por grupo (injetando :grupo
   automaticamente) e gera gráficos/Excel/e-mail separados por grupo.
   Cada grupo recebe SOMENTE seus próprios dados; grupo sem destinatário
   configurado simplesmente não recebe e-mail.
"""

import os
import re
import subprocess

from config import settings
from config.reports import REPORTS
from config.groups import GRUPOS

from services.logger import logger
from services.database import executar_query
from services.periodos import resolver_periodo
from services.mailer import conectar, enviar_relatorio_email
from services.charts import gerar_grafico_pizza, gerar_grafico_barras
from services.excel_service import gerar_arquivo_excel_multi_aba

from services.report_renderer import (
    normalizar_floats_inteiros,
    extrair_kpis_do_relatorio,
    montar_tabelas_html,
    montar_dados_por_grupo,
)


GERADORES_GRAFICO = {
    "pizza": gerar_grafico_pizza,
    "barras": gerar_grafico_barras,
}

VERSAO_PIPELINE = "2.2.0"


def obter_versao_completa() -> str:
    """Retorna 'VERSAO_PIPELINE (hash curto do commit)', ou só a versão se o Git não estiver disponível."""
    try:
        resultado = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        if resultado.returncode == 0 and resultado.stdout.strip():
            return f"{VERSAO_PIPELINE} ({resultado.stdout.strip()})"
    except Exception:
        pass
    return f"{VERSAO_PIPELINE} (commit desconhecido)"


# ============================================================
# UTILITÁRIOS
# ============================================================

def normalizar_nome_arquivo(valor: str) -> str:
    """Converte um nome de grupo em nome seguro para arquivo (ex: 'SUPORTE SANTANA' -> 'suporte_santana')."""
    valor = re.sub(r"[^a-z0-9]+", "_", str(valor).strip().lower()).strip("_")
    return valor or "grupo"


def obter_destinatarios_por_grupo(cfg: dict, grupo: str):
    """
    Obtém os destinatários de um grupo de acordo com o tipo de relatório
    (cfg["tipo_relatorio"]: mensal/semanal/anual/criticos), usando o
    mapeamento centralizado em config/groups.py (GRUPOS[x]["destinatarios"]),
    cujos valores são nomes de variável lidos de config/settings.py.

    Retorna None quando o grupo não existe em config/groups.py, o tipo de
    relatório não tem destinatário configurado para aquele grupo, ou a
    variável de ambiente correspondente está vazia/ausente.
    """
    tipo_relatorio = cfg.get("tipo_relatorio")

    if not tipo_relatorio:
        # Fallback para configurações antigas que só têm "titulo"/"nome".
        nome_relatorio = (cfg.get("nome") or cfg.get("titulo") or "").lower()
        if "critico" in nome_relatorio:
            tipo_relatorio = "criticos"
        elif "semanal" in nome_relatorio:
            tipo_relatorio = "semanal"
        elif "mensal" in nome_relatorio:
            tipo_relatorio = "mensal"
        elif "anual" in nome_relatorio:
            tipo_relatorio = "anual"
        else:
            logger.warning(f"Não foi possível identificar o tipo do relatório para o grupo '{grupo}'.")
            return None

    grupo_config = next(
        (dados for dados in GRUPOS.values() if dados.get("nome", "").strip().upper() == grupo.strip().upper()),
        None,
    )
    if not grupo_config:
        logger.warning(f"Grupo '{grupo}' não encontrado em config/groups.py.")
        return None

    nome_variavel = grupo_config.get("destinatarios", {}).get(tipo_relatorio)
    if not nome_variavel:
        logger.warning(f"Grupo '{grupo}' não possui destinatário configurado para o tipo '{tipo_relatorio}'.")
        return None

    destinatarios = getattr(settings, nome_variavel, None)
    if not destinatarios:
        logger.warning(
            f"Grupo '{grupo}' possui a variável '{nome_variavel}', porém ela está vazia ou não foi configurada."
        )
        return None

    if isinstance(destinatarios, str):
        destinatarios = [email.strip() for email in destinatarios.split(",") if email.strip()]
    elif isinstance(destinatarios, (list, tuple)):
        destinatarios = [str(email).strip() for email in destinatarios if str(email).strip()]
    else:
        logger.warning(f"Formato inválido de destinatários para o grupo '{grupo}': {type(destinatarios).__name__}")
        return None

    if not destinatarios:
        logger.warning(f"Grupo '{grupo}' não possui destinatários válidos para o tipo '{tipo_relatorio}'.")
        return None

    logger.info(
        f"Grupo '{grupo}' | Tipo '{tipo_relatorio}' | Variável '{nome_variavel}' | Destinatários: {destinatarios}"
    )
    return destinatarios


def obter_nome_excel_do_grupo(cfg: dict, grupo: str) -> str:
    """'Atendimento_Mensal_Grupo.xlsx' + 'SUPORTE SANTANA' -> 'Atendimento_Mensal_Grupo_suporte_santana.xlsx'."""
    nome_base = cfg["nome_arquivo_excel"]
    if nome_base.lower().endswith(".xlsx"):
        nome_base = nome_base[:-5]
    return f"{nome_base}_{normalizar_nome_arquivo(grupo)}.xlsx"


# ============================================================
# EXECUÇÃO DE QUERIES
# ============================================================

_PARAMS_PERIODO = (":inicio", ":fim", ":fim_exclusivo", ":ano", ":mes")


def executar_queries_do_relatorio(cfg: dict, params: dict | None) -> dict:
    """Executa todas as queries de um relatório normal. Retorna {nome_dataset: DataFrame}."""
    dfs = {}
    for nome_dataset, query in cfg.get("queries", {}).items():
        if not query:
            logger.warning(f"Dataset '{nome_dataset}' possui query vazia.")
            continue

        usa_periodo = any(parametro in query for parametro in _PARAMS_PERIODO)
        df = normalizar_floats_inteiros(executar_query(query, params=params if usa_periodo else None))
        dfs[nome_dataset] = df
        logger.info(f"Dataset '{nome_dataset}': {len(df)} linhas retornadas.")

    return dfs


def executar_queries_por_grupo(cfg: dict, params: dict | None, grupos: list[str]) -> dict:
    """
    Executa as queries uma vez por grupo, injetando automaticamente :grupo
    além dos parâmetros de período. Retorna {grupo: {nome_dataset: DataFrame}}.
    """
    resultados = {}
    queries = cfg.get("queries", {})
    if not queries:
        logger.warning("Relatório por grupo não possui queries configuradas.")
        return resultados

    for grupo in grupos:
        logger.info("=" * 50)
        logger.info(f"Executando relatório para grupo: {grupo}")
        logger.info("=" * 50)

        resultados[grupo] = {}
        params_grupo = {**(params or {}), "grupo": grupo}

        for nome_dataset, query in queries.items():
            if not query:
                logger.warning(f"Grupo '{grupo}' | Dataset '{nome_dataset}' possui query vazia.")
                continue

            try:
                usa_parametros = any(parametro in query for parametro in (":grupo", *_PARAMS_PERIODO))
                df = normalizar_floats_inteiros(
                    executar_query(query, params=params_grupo if usa_parametros else None)
                )
                resultados[grupo][nome_dataset] = df
                logger.info(f"Grupo '{grupo}' | Dataset '{nome_dataset}': {len(df)} linhas retornadas.")
            except Exception:
                logger.exception(f"Erro executando dataset '{nome_dataset}' para o grupo '{grupo}'.")
                raise

    return resultados


# ============================================================
# GRÁFICOS
# ============================================================

def gerar_graficos_do_relatorio(dfs: dict, cfg: dict, nome_relatorio: str) -> list:
    """
    Gera os gráficos configurados em cfg["graficos"] para UM contexto de
    datasets (todos os datasets do relatório normal, ou os de um único
    grupo). Modos suportados: "contagem", "soma_colunas", "valor_por_categoria".
    """
    graficos_gerados = []

    for grafico_cfg in cfg.get("graficos", []):
        dataset = grafico_cfg["dataset"]
        cid = grafico_cfg.get("cid", dataset)
        df = dfs.get(dataset)

        if df is None:
            logger.warning(f"Dataset '{dataset}' não encontrado para o gráfico '{cid}'.")
            continue
        if df.empty:
            logger.info(f"Gráfico '{cid}' pulado (dataset '{dataset}' vazio).")
            continue

        gerar_funcao = GERADORES_GRAFICO.get(grafico_cfg.get("tipo"))
        if not gerar_funcao:
            logger.error(f"Tipo de gráfico '{grafico_cfg.get('tipo')}' não suportado.")
            continue

        modo = grafico_cfg.get("modo", "contagem")

        if modo == "contagem":
            coluna = grafico_cfg["coluna"]
            if coluna not in df.columns:
                logger.warning(f"Gráfico '{cid}' pulado. Coluna '{coluna}' não existe.")
                continue
            contagem = df[coluna].value_counts()
            labels, valores, sufixo_arquivo = contagem.index.tolist(), contagem.values.tolist(), coluna

        elif modo == "soma_colunas":
            colunas = grafico_cfg["colunas"]
            faltando = [coluna for coluna in colunas if coluna not in df.columns]
            if faltando:
                logger.warning(f"Gráfico '{cid}' pulado. Colunas ausentes: {faltando}")
                continue
            labels = grafico_cfg.get("labels", colunas)
            valores = [df[coluna].sum() for coluna in colunas]
            sufixo_arquivo = "_".join(colunas)

        elif modo == "valor_por_categoria":
            coluna_label, coluna_valor = grafico_cfg["coluna_label"], grafico_cfg["coluna_valor"]
            if coluna_label not in df.columns or coluna_valor not in df.columns:
                logger.warning(f"Gráfico '{cid}' pulado. Colunas necessárias não existem.")
                continue
            labels, valores = df[coluna_label].tolist(), df[coluna_valor].tolist()
            sufixo_arquivo = f"{coluna_label}_{coluna_valor}"

        else:
            logger.error(f"Modo de gráfico '{modo}' não suportado.")
            continue

        caminho_grafico = gerar_funcao(
            labels=labels,
            valores=valores,
            titulo=grafico_cfg["titulo"],
            nome_arquivo=f"{nome_relatorio}_{dataset}_{sufixo_arquivo}.png",
        )
        graficos_gerados.append({"cid": cid, "caminho": caminho_grafico})
        logger.info(f"Gráfico '{grafico_cfg['titulo']}' gerado.")

    return graficos_gerados


# ============================================================
# ENVIO
# ============================================================

def _verificar_tamanho_anexo(caminho_excel: str, nome_relatorio: str) -> None:
    """Aborta o envio se o Excel exceder ANEXO_TAMANHO_MAXIMO_MB; só avisa se exceder ANEXO_TAMANHO_ALERTA_MB."""
    if not os.path.exists(caminho_excel):
        return

    tamanho_mb = os.path.getsize(caminho_excel) / (1024 * 1024)

    if tamanho_mb >= settings.ANEXO_TAMANHO_MAXIMO_MB:
        logger.error(
            f"Relatório '{nome_relatorio}': anexo '{caminho_excel}' possui {tamanho_mb:.1f} MB. "
            f"Limite: {settings.ANEXO_TAMANHO_MAXIMO_MB} MB."
        )
        raise RuntimeError(f"Anexo do relatório '{nome_relatorio}' excede o limite configurado.")

    if tamanho_mb >= settings.ANEXO_TAMANHO_ALERTA_MB:
        logger.warning(
            f"Relatório '{nome_relatorio}': anexo possui {tamanho_mb:.1f} MB. "
            f"Limite de alerta: {settings.ANEXO_TAMANHO_ALERTA_MB} MB."
        )


def _enviar_e_limpar(
    *,
    nome_relatorio: str,
    caminho_excel: str,
    destinatarios: list,
    assunto: str,
    titulo: str,
    tabelas_html: dict,
    nome_template: str,
    graficos: list,
    contexto_extra: dict,
    datasets_keys: list,
    rotulo: str,
    mensagem_sucesso: str,
    dry_run: bool,
) -> bool:
    """
    Cauda compartilhada do envio, usada tanto pelo relatório normal quanto
    por cada grupo de um relatório "por_grupo": checa o tamanho do anexo,
    loga o dry-run OU conecta no SMTP e envia — e SEMPRE fecha a conexão
    SMTP e apaga o Excel gerado ao final, mesmo se o envio falhar.

    'mensagem_sucesso' é logada literalmente após o envio: no caso do
    relatório normal ela precisa terminar em "concluído com sucesso." —
    scripts/duracao_ultima_execucao.py depende desse texto exato para medir
    a duração da última execução bem-sucedida (usado pelo item Zabbix
    automacaoglpi.report.duracao).
    """
    server = None
    try:
        _verificar_tamanho_anexo(caminho_excel, nome_relatorio)
        tamanho_kb = os.path.getsize(caminho_excel) / 1024 if os.path.exists(caminho_excel) else 0

        if dry_run:
            logger.info(f"[DRY-RUN] {rotulo}: enviaria para {destinatarios}")
            logger.info(
                f"[DRY-RUN] Assunto: '{assunto}' | Excel: {caminho_excel} ({tamanho_kb:.0f} KB) | "
                f"Gráficos: {len(graficos)} | Datasets: {datasets_keys}"
            )
            return True

        server = conectar()
        logger.info(f"Enviando {rotulo} para {destinatarios}...")

        enviar_relatorio_email(
            destinatarios=destinatarios,
            assunto=assunto,
            titulo_relatorio=titulo,
            tabelas_html=tabelas_html,
            nome_arquivo_excel=caminho_excel,
            server_smtp=server,
            nome_template=nome_template,
            graficos=graficos,
            contexto_extra=contexto_extra,
        )
        logger.info(mensagem_sucesso)
        return True

    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                logger.warning(f"Não foi possível fechar a conexão SMTP ({rotulo}).")

        if os.path.exists(caminho_excel):
            try:
                os.remove(caminho_excel)
                logger.info(f"Arquivo '{caminho_excel}' removido.")
            except Exception:
                logger.exception(f"Erro removendo o arquivo '{caminho_excel}'.")


def processar_envio_grupo(
    nome_relatorio: str,
    cfg: dict,
    grupo: str,
    datasets: dict,
    periodo_contexto: dict,
    dry_run: bool,
) -> bool:
    """
    Processa completamente UM grupo: destinatários -> gráficos -> tabelas ->
    KPIs -> Excel -> e-mail. Nunca recebe dados de outro grupo. Retorna
    False (sem levantar erro) quando o grupo não tem destinatário configurado.
    """
    logger.info("-" * 50)
    logger.info(f"Processando grupo: {grupo}")
    logger.info("-" * 50)

    destinatarios = obter_destinatarios_por_grupo(cfg, grupo)
    if not destinatarios:
        logger.warning(f"Grupo '{grupo}' não possui destinatários. Nenhum e-mail será enviado.")
        if dry_run:
            logger.info(f"[DRY-RUN] Grupo '{grupo}': status=IGNORADO | motivo=destinatários não configurados.")
        return False

    caminho_excel = obter_nome_excel_do_grupo(cfg, grupo)
    nome_relatorio_grupo = f"{nome_relatorio}_{normalizar_nome_arquivo(grupo)}"

    graficos = gerar_graficos_do_relatorio(dfs=datasets, cfg=cfg, nome_relatorio=nome_relatorio_grupo)
    logger.info(f"Grupo '{grupo}': {len(graficos)} gráfico(s) gerado(s).")

    tabelas_html = montar_tabelas_html(datasets, cfg)
    kpis = extrair_kpis_do_relatorio(datasets, cfg)
    dados_por_grupo = montar_dados_por_grupo(datasets, cfg.get("dados_por_grupo_datasets", []))
    grupos_template = {grupo: {nome: df.to_dict("records") for nome, df in datasets.items()}}

    gerar_arquivo_excel_multi_aba(datasets, caminho_excel)
    logger.info(f"Excel do grupo '{grupo}' gerado: '{caminho_excel}'.")

    contexto_extra = {
        "grupo": grupo,
        "kpis": kpis,
        "dados_por_grupo": dados_por_grupo,
        "grupos": grupos_template,
        **periodo_contexto,
    }

    return _enviar_e_limpar(
        nome_relatorio=nome_relatorio,
        caminho_excel=caminho_excel,
        destinatarios=destinatarios,
        assunto=cfg["assunto"].replace("{{ grupo }}", grupo),
        titulo=cfg["titulo"].replace("{{ grupo }}", grupo),
        tabelas_html=tabelas_html,
        nome_template=cfg["template"],
        graficos=graficos,
        contexto_extra=contexto_extra,
        datasets_keys=list(datasets.keys()),
        rotulo=f"relatório do grupo '{grupo}'",
        mensagem_sucesso=f"Relatório do grupo '{grupo}' enviado com sucesso.",
        dry_run=dry_run,
    )


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def executar_relatorio(nome_relatorio: str, dry_run: bool = False) -> None:
    """
    Executa o pipeline completo de um relatório (ver config/reports.py):

        Normal:    queries -> Excel -> gráficos -> e-mail
        Por grupo: (queries -> Excel -> gráficos -> e-mail) para cada grupo
    """
    if nome_relatorio not in REPORTS:
        logger.error(f"Relatório '{nome_relatorio}' não existe em config/reports.py.")
        logger.error(f"Disponíveis: {list(REPORTS.keys())}")
        raise SystemExit(1)

    cfg = REPORTS[nome_relatorio]

    logger.info(
        f"Iniciando relatório: {nome_relatorio} (pipeline {obter_versao_completa()})"
        f"{' [DRY-RUN — nenhum e-mail será enviado]' if dry_run else ''}"
    )

    data_inicio, data_fim, data_fim_exclusivo = resolver_periodo(cfg["periodo"])

    params = {}
    if data_inicio:
        params = {
            "inicio": data_inicio,
            "fim": data_fim,
            "fim_exclusivo": data_fim_exclusivo,
            "ano": data_inicio.year,
            "mes": data_inicio.month,
        }
        logger.info(f"Período calculado: {data_inicio} até {data_fim}")

    periodo_contexto = {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "data_fim_exclusivo": data_fim_exclusivo,
    }

    if cfg.get("tipo") == "por_grupo":
        _executar_relatorio_por_grupo(nome_relatorio, cfg, params, periodo_contexto, dry_run)
    else:
        _executar_relatorio_normal(nome_relatorio, cfg, params, periodo_contexto, dry_run)


def _executar_relatorio_por_grupo(
    nome_relatorio: str,
    cfg: dict,
    params: dict,
    periodo_contexto: dict,
    dry_run: bool,
) -> None:
    grupos_config = cfg.get("grupos")
    if not grupos_config:
        raise RuntimeError(f"Relatório '{nome_relatorio}' é do tipo 'por_grupo' mas não define 'grupos'.")

    logger.info(f"Relatório '{nome_relatorio}' será executado para {len(grupos_config)} grupo(s): {grupos_config}")

    resultados_por_grupo = executar_queries_por_grupo(cfg=cfg, params=params, grupos=grupos_config)

    enviados = 0
    ignorados = 0

    for grupo in grupos_config:
        datasets = resultados_por_grupo.get(grupo, {})
        if not datasets:
            logger.warning(f"Grupo '{grupo}' não possui datasets retornados.")

        try:
            processado = processar_envio_grupo(
                nome_relatorio=nome_relatorio,
                cfg=cfg,
                grupo=grupo,
                datasets=datasets,
                periodo_contexto=periodo_contexto,
                dry_run=dry_run,
            )
            if processado:
                enviados += 1
            else:
                ignorados += 1
        except Exception:
            logger.exception(f"Falha processando o grupo '{grupo}'.")
            raise

    logger.info("=" * 50)
    logger.info(f"Relatório '{nome_relatorio}' finalizado.")
    logger.info(f"Grupos processados: {len(grupos_config)}")
    logger.info(f"Grupos enviados/simulados: {enviados}")
    logger.info(f"Grupos ignorados: {ignorados}")
    logger.info("=" * 50)

    if not dry_run:
        # Linha de resumo no MESMO formato usada pelo relatório normal —
        # necessária para scripts/duracao_ultima_execucao.py (e o item Zabbix
        # automacaoglpi.report.duracao[*]) conseguirem medir a duração de um
        # relatório "por_grupo" também. Sem isso, o script nunca encontra um
        # par início/fim para esses relatórios e sempre retorna -1, mesmo
        # com todos os grupos processados com sucesso.
        logger.info(f"Relatório '{nome_relatorio}' concluído com sucesso.")


def _executar_relatorio_normal(
    nome_relatorio: str,
    cfg: dict,
    params: dict,
    periodo_contexto: dict,
    dry_run: bool,
) -> None:
    dfs = executar_queries_do_relatorio(cfg, params)

    if dfs and all(df.empty for df in dfs.values()):
        logger.warning(
            f"Relatório '{nome_relatorio}': TODOS os {len(dfs)} dataset(s) vieram vazios: {list(dfs.keys())}."
        )

    graficos = gerar_graficos_do_relatorio(dfs=dfs, cfg=cfg, nome_relatorio=nome_relatorio)
    tabelas_html = montar_tabelas_html(dfs, cfg)
    kpis = extrair_kpis_do_relatorio(dfs, cfg)
    dados_por_grupo = montar_dados_por_grupo(dfs, cfg.get("dados_por_grupo_datasets", []))

    destinatarios_env = cfg.get("destinatarios_env")
    if not destinatarios_env:
        raise RuntimeError(f"Relatório '{nome_relatorio}' não possui 'destinatarios_env'.")

    destinatarios = getattr(settings, destinatarios_env, None)
    if not destinatarios:
        if dry_run:
            logger.warning(f"[DRY-RUN] Relatório '{nome_relatorio}' não possui destinatários configurados.")
            return
        raise RuntimeError(f"Nenhum destinatário configurado para '{destinatarios_env}'.")

    caminho_excel = cfg["nome_arquivo_excel"]
    gerar_arquivo_excel_multi_aba(dfs, caminho_excel)
    logger.info(f"Arquivo Excel '{caminho_excel}' gerado.")

    contexto_extra = {"kpis": kpis, "dados_por_grupo": dados_por_grupo, **periodo_contexto}

    _enviar_e_limpar(
        nome_relatorio=nome_relatorio,
        caminho_excel=caminho_excel,
        destinatarios=destinatarios,
        assunto=cfg["assunto"],
        titulo=cfg["titulo"],
        tabelas_html=tabelas_html,
        nome_template=cfg["template"],
        graficos=graficos,
        contexto_extra=contexto_extra,
        datasets_keys=list(dfs.keys()),
        rotulo=f"relatório '{nome_relatorio}'",
        mensagem_sucesso=f"Relatório '{nome_relatorio}' concluído com sucesso.",
        dry_run=dry_run,
    )
