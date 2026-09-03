"""
scripts/verificar_schema.py

Cobre o item do checklist: "Confirmar periodicamente que os nomes de
views/colunas em sql/ continuam batendo com o schema do GLPI em
produção, já que views podem evoluir."

Estratégia: para cada arquivo .sql em sql/, roda um EXPLAIN (não um
SELECT de verdade) contra o banco configurado no .env. EXPLAIN valida
que a query é executável — tabela/view existe, colunas existem, JOIN
faz sentido — SEM ler os dados de fato, então é seguro rodar em
produção mesmo em horário de pico (custo é o de um parse + plano de
execução, não o de uma varredura de dados).

Detecta exatamente o tipo de drift que já causou dor de cabeça nesse
projeto antes (bug de "corte de data" + mudança de view): a query para
de funcionar antes de alguém notar porque um agendamento falhou.

Uso:
    python3 scripts/verificar_schema.py
    python3 scripts/verificar_schema.py --sql-dir sql/infra

Saída: 0 se tudo OK, 1 se alguma query falhou (para uso em CI/cron com
alerta — ver zabbix/README.md para integrar como um item passivo).

Recomendação de uso: rodar semanalmente via cron/systemd timer separado
dos relatórios normais, OU manualmente depois de qualquer alteração de
schema no GLPI/atualização de versão do GLPI.
"""
import argparse
import glob
import os
import sys

from sqlalchemy import text

# Garante que 'services' e 'config' sejam importáveis rodando o script
# direto de dentro de scripts/ (python3 scripts/verificar_schema.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # noqa: E402
from services.database import obter_engine, _mascarar_senha  # noqa: E402
from services.logger import logger  # noqa: E402

# Valores fictícios só para satisfazer os parâmetros nomeados que
# algumas queries esperam (:inicio, :fim, etc.) — o EXPLAIN nunca lê os
# dados de verdade, então o valor em si é irrelevante, só precisa ter o
# tipo certo para o parser aceitar.
PARAMS_FICTICIOS = {
    "inicio": "2026-01-01",
    "fim": "2026-01-31",
    "fim_exclusivo": "2026-02-01",
    "ano": 2026,
    "mes": 1,
    "grupo": "Administração de Sistemas",
}


def encontrar_arquivos_sql(sql_dir: str) -> list:
    return sorted(glob.glob(os.path.join(sql_dir, "**", "*.sql"), recursive=True))


def verificar_arquivo(engine, caminho_sql: str) -> tuple:
    """Retorna (ok: bool, mensagem: str)."""
    with open(caminho_sql, encoding="utf-8") as f:
        query = f.read().strip().rstrip(";")

    if not query:
        return True, "arquivo vazio, pulado"

    try:
        with engine.connect() as conn:
            conn.execute(text(f"EXPLAIN {query}"), PARAMS_FICTICIOS)
        return True, "OK"
    except Exception as e:
        return False, _mascarar_senha(f"{type(e).__name__}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Verifica se as queries em sql/ ainda batem com o schema atual do GLPI")
    parser.add_argument("--sql-dir", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sql"))
    args = parser.parse_args()

    settings.validar_configuracoes()
    engine = obter_engine()

    arquivos = encontrar_arquivos_sql(args.sql_dir)
    if not arquivos:
        logger.warning(f"Nenhum arquivo .sql encontrado em {args.sql_dir}.")
        sys.exit(1)

    falhas = []
    for caminho in arquivos:
        nome_relativo = os.path.relpath(caminho, args.sql_dir)
        ok, mensagem = verificar_arquivo(engine, caminho)
        if ok:
            logger.info(f"[OK] {nome_relativo}")
        else:
            logger.error(f"[FALHA] {nome_relativo}: {mensagem}")
            falhas.append((nome_relativo, mensagem))

    print()
    print(f"Verificação de schema: {len(arquivos) - len(falhas)}/{len(arquivos)} queries OK.")
    if falhas:
        print("\nQueries com problema (schema pode ter mudado no GLPI):")
        for nome, mensagem in falhas:
            print(f"  - {nome}: {mensagem}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
