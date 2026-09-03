"""
services/logger.py

Logging centralizado para o projeto. Substitui os prints soltos por
mensagens com timestamp, nível (INFO/WARNING/ERROR) e destino configurável
(console + arquivo).

Uso em qualquer módulo:
    from services.logger import logger
    logger.info("Extraindo dados das views...")
    logger.error(f"Erro ao executar a query: {e}")

Formato do log de arquivo controlado por LOG_FORMAT no .env:
    LOG_FORMAT=text (padrão) — "2026-08-17 10:00:00 [INFO] mensagem"
    LOG_FORMAT=json          — uma linha JSON por evento, para consumo
                                por Grafana Loki/Promtail ou qualquer
                                coletor de log estruturado, sem precisar
                                de regex de parsing no formato texto.
O console sempre usa o formato texto (mais legível rodando manualmente
no terminal) — só o arquivo respeita LOG_FORMAT.
"""
import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler

from dotenv import load_dotenv

# Carrega o .env aqui também (idempotente — chamar de novo em
# config/settings.py não tem efeito colateral): este módulo é importado
# por config/settings.py ANTES da chamada a load_dotenv() de lá, então
# sem isso LOG_FORMAT nunca seria lido do .env na primeira carga.
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, 'execucao.log')

LOG_FORMAT = os.getenv("LOG_FORMAT", "text").strip().lower()

logger = logging.getLogger('automacaoGLPI')
logger.setLevel(logging.INFO)


class _FormatadorJSON(logging.Formatter):
    """
    Uma linha de JSON por evento de log. Campos estáveis (mesmo nome
    sempre presente) para facilitar dashboards/alertas em cima disso —
    ex: no Loki, filtrar por {nivel="ERROR"} em vez de grep no texto.
    """
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "nivel": record.levelname,
            "mensagem": record.getMessage(),
            "modulo": record.module,
            "processo": record.process,
        }
        if record.exc_info:
            payload["excecao"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_formato_texto = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

_formato_arquivo = _FormatadorJSON() if LOG_FORMAT == "json" else _formato_texto

# Handler de arquivo com rotação diária: à meia-noite, o arquivo atual
# vira execucao.log.YYYY-MM-DD e um novo execucao.log começa vazio.
# backupCount=7 apaga automaticamente qualquer rotação com mais de 7 dias —
# retenção por idade, não por tamanho (rotação por tamanho não garante
# uma janela de retenção previsível: um log que cresce devagar nunca
# "envelhece" o suficiente pra rotacionar).
_file_handler = TimedRotatingFileHandler(
    LOG_PATH, when='midnight', interval=1, backupCount=7, encoding='utf-8'
)
_file_handler.setFormatter(_formato_arquivo)

# Handler de console: sempre texto simples, mesmo com LOG_FORMAT=json —
# é o que se lê rodando manualmente no terminal ou via preview_template.py.
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formato_texto)

if not logger.handlers:
    logger.addHandler(_file_handler)
    logger.addHandler(_console_handler)