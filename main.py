"""
main.py

Ponto de entrada CLI da automação. Depois da unificação com
services/reporter_runner.py, este arquivo não conhece mais os detalhes
de "como" um relatório é gerado (queries, Excel, gráficos, tabelas,
e-mail) — ele só cuida de:
    1. Parsear o argumento --report
    2. Validar as configurações do .env
    3. Delegar para reporter_runner.executar_relatorio()
    4. Garantir a limpeza dos gráficos temporários no final, mesmo em falha

Toda a lógica de orquestração de um relatório individual vive em
services/reporter_runner.py. As funções auxiliares de formatação/extração
de dados (normalizar_floats_inteiros, formatar_colunas_horas,
formatar_colunas_percentual, extrair_kpis_do_relatorio,
montar_tabelas_html, montar_dados_por_grupo) vivem em
services/report_renderer.py — não redefina-as aqui. Se precisar delas,
importe de lá.
"""
import argparse
import sys
from config import settings
from config.reports import REPORTS
from services.logger import logger
from services.charts import limpar_graficos_temporarios
from services.reporter_runner import executar_relatorio, obter_versao_completa


def main():
    parser = argparse.ArgumentParser(description="Automação de relatórios GLPI")
    parser.add_argument(
        "--report",
        choices=list(REPORTS.keys()),
        help="Nome do relatório a ser executado (ver config/reports.py)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Executa todo o pipeline (queries, Excel, gráficos, renderização) "
            "SEM conectar no SMTP nem enviar e-mail — só loga o que seria "
            "enviado. Pensado para rodar contra um .env de homologação "
            "(ver seção 'Ambiente de homologação' no README)."
        ),
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Mostra a versão do pipeline (VERSAO_PIPELINE + hash do commit git) e sai.",
    )
    args = parser.parse_args()

    if args.version:
        print(f"automacaoGLPI pipeline v{obter_versao_completa()}")
        sys.exit(0)

    if not args.report:
        parser.error("--report é obrigatório (a menos que --version seja usado).")

    settings.validar_configuracoes()

    try:
        executar_relatorio(args.report, dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Falha na execução do relatório '{args.report}': {e}", exc_info=True)
        raise
    finally:
        limpar_graficos_temporarios()


if __name__ == "__main__":
    main()

