"""
scripts/check_db_zabbix.py

Testa a conectividade real com o banco GLPI (SELECT 1, via credenciais do
.env) e sai com código 0 (sucesso) ou 1 (falha). Pensado para ser chamado
pelo UserParameter "automacaoglpi.db.conectividade" do Zabbix agent — mais
forte que um Simple Check de porta TCP, porque valida usuário/senha e
execução de query, não só se a porta está aberta.

Existe como script isolado (em vez de "python3 -c ..." embutido direto no
UserParameter/sudoers) porque o sudoers não aceita ';'/aspas complexas
como argumento de comando — precisa de um caminho fixo, sem argumentos
dinâmicos.

Uso manual:
    python3 scripts/check_db_zabbix.py && echo OK || echo FALHOU
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.database import executar_query


def main() -> None:
    try:
        executar_query("SELECT 1")
    except Exception as e:
        print(f"Falha na conectividade com o banco: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
