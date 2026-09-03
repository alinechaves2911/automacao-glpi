"""
scripts/duracao_ultima_execucao.py

Calcula a duração (em segundos) da última execução BEM-SUCEDIDA de um
relatório, lendo logs/execucao.log. Pensado para ser chamado pelo
UserParameter "automacaoglpi.report.duracao[*]" do Zabbix agent
(ver zabbix/userparameter_automacaoglpi.conf).

Uso:
    python3 duracao_ultima_execucao.py <nome_do_relatorio>

Saída: um único número (segundos) em stdout, ou -1 se não encontrar um
par início/fim completo nos logs disponíveis.

Limitações conhecidas:
- O log rotaciona por DIA (TimedRotatingFileHandler, à meia-noite), não
  por execução. Em teoria uma execução pode ficar dividida entre
  execucao.log e a rotação do dia anterior (execucao.log.YYYY-MM-DD) —
  o script cobre o arquivo atual mais a rotação mais recente, mas não
  tenta reconstruir uma execução partida no meio da rotação.
- Mede só execuções que terminaram com sucesso (a linha "concluído com
  sucesso!"). Uma execução que falhou não tem "fim" nesse sentido — isso
  é intencional, já que o alerta de falha (scripts/alerta_falha.py) cobre
  esse caso separadamente.
"""
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"


def _arquivos_de_log() -> list[Path]:
    """Rotação mais recente (execucao.log.YYYY-MM-DD, se existir) + arquivo atual, em ordem cronológica."""
    rotacoes = sorted(LOG_DIR.glob("execucao.log.20*"))
    arquivos = ([rotacoes[-1]] if rotacoes else []) + [LOG_DIR / "execucao.log"]
    return [arquivo for arquivo in arquivos if arquivo.exists()]

TS_FMT = "%Y-%m-%d %H:%M:%S"
LINHA_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[\w+\] (?P<msg>.*)$")
INICIO_RE = re.compile(r"^Iniciando relatório: (?P<nome>\S+)")
FIM_RE = re.compile(r"^Relatório '(?P<nome>[^']+)' concluído com sucesso\.")


def ultima_duracao_segundos(nome_relatorio: str):
    """
    Percorre os logs em ordem cronológica e guarda a duração do ÚLTIMO par
    início/fim encontrado para o relatório pedido (o log já é sequencial,
    então o último par visto é o mais recente).
    """
    linhas = []
    for caminho in _arquivos_de_log():
        linhas.extend(caminho.read_text(encoding="utf-8", errors="replace").splitlines())

    inicio_ts = None
    ultima_duracao = None

    for linha in linhas:
        m = LINHA_RE.match(linha)
        if not m:
            continue
        ts_str, msg = m.group("ts"), m.group("msg")

        m_inicio = INICIO_RE.match(msg)
        if m_inicio and m_inicio.group("nome") == nome_relatorio:
            inicio_ts = ts_str
            continue

        m_fim = FIM_RE.match(msg)
        if m_fim and m_fim.group("nome") == nome_relatorio and inicio_ts:
            try:
                t0 = datetime.strptime(inicio_ts, TS_FMT)
                t1 = datetime.strptime(ts_str, TS_FMT)
                ultima_duracao = (t1 - t0).total_seconds()
            except ValueError:
                pass
            inicio_ts = None

    return ultima_duracao


def main() -> None:
    if len(sys.argv) < 2:
        print("-1")
        sys.exit(1)

    nome_relatorio = sys.argv[1]
    duracao = ultima_duracao_segundos(nome_relatorio)
    print(int(duracao) if duracao is not None else -1)


if __name__ == "__main__":
    main()
