"""
services/database.py

Camada de acesso ao banco de dados. Único módulo do projeto que sabe
como conectar e executar SQL — os demais serviços recebem sempre um
DataFrame já pronto.

Renomeado de db.py para database.py: "db" era ambíguo (conflitava
mentalmente com "banco de dados" vs "objeto de conexão"). O nome do
arquivo agora bate com o que o módulo representa.
"""
import traceback
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, DBAPIError
from urllib.parse import quote_plus
import pandas as pd

from config import settings
from services.logger import logger
from services.retry import retry_com_backoff

# Erros que valem retry: problemas de conexão/rede/timeout com o
# MariaDB (host fora do ar, timeout, reset momentâneo). OperationalError
# cobre a grande maioria disso no SQLAlchemy/mysql-connector; DBAPIError
# é o guarda-chuva mais genérico do driver. Erros de sintaxe SQL ou de
# credencial inválida NÃO caem aqui (não adianta tentar de novo).
_ERROS_TRANSITORIOS_DB = (OperationalError, DBAPIError, TimeoutError, ConnectionError)


def _mensagem_erro_sanitizada(e: Exception) -> str:
    """
    Remove qualquer ocorrência literal de DB_PASS do texto da exceção
    antes de logar. Alguns erros do driver (ex: falha de autenticação,
    URL malformada) ecoam a connection string inteira na mensagem —
    isso garante que a senha não vá parar no log mesmo nesse caso.
    """
    texto = f"{type(e).__name__}: {e}"
    return _mascarar_senha(texto)


def _mascarar_senha(texto: str) -> str:
    if settings.DB_PASS:
        texto = texto.replace(settings.DB_PASS, "***")
        texto = texto.replace(quote_plus(settings.DB_PASS), "***")
    return texto


def _url_mascarada() -> str:
    """
    Versão da connection string SEM a senha, só para uso em logs.
    Nunca logar a URL retornada por obter_engine() diretamente: o driver
    mysql-connector-python (e o próprio SQLAlchemy, em alguns erros de
    conexão) pode incluir a URL completa — com a senha em texto plano —
    na mensagem de exceção. Como o log vai para logs/execucao.log em
    disco (e para o journal via systemd), isso vazaria DB_PASS para
    quem tiver acesso de leitura ao arquivo/journal, mesmo sem acesso
    ao .env.
    """
    return (
        f"mysql+mysqlconnector://{settings.DB_USER}:***"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )


def obter_engine():
    db_user = quote_plus(settings.DB_USER)
    db_pass = quote_plus(settings.DB_PASS)
    url = (
        f"mysql+mysqlconnector://{db_user}:{db_pass}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
    return create_engine(url)


def executar_query(query: str, params: dict = None) -> pd.DataFrame:
    """
    params: dict opcional para queries parametrizadas, ex:
            executar_query("SELECT * FROM vw WHERE dia BETWEEN :inicio AND :fim",
                            {"inicio": data_inicio, "fim": data_fim})

    A query é envolvida com text() para que o SQLAlchemy traduza os
    parâmetros nomeados (:nome) para a sintaxe correta do driver
    mysql-connector-python — sem isso, o driver recebe ':nome' literal
    e gera erro de sintaxe SQL.

    Falhas transitórias de conexão (host momentaneamente inacessível,
    timeout) são reexecutadas automaticamente até 3x com backoff
    exponencial (2s, 4s) antes de desistir — ver services/retry.py.
    """
    try:
        return _executar_query_com_retry(query, params)
    except Exception as e:
        # NÃO usar logger.exception()/exc_info=True aqui: o logging
        # formataria o traceback chamando str(e) de novo internamente,
        # o que reintroduziria a senha em texto plano caso ela apareça
        # na mensagem original da exceção (comum em erro de autenticação
        # ou de URL malformada do driver). Formatamos e sanitizamos o
        # traceback manualmente antes de logar.
        traceback_sanitizado = _mascarar_senha(traceback.format_exc())
        logger.error(
            f"Erro ao executar a query no banco de dados ({_url_mascarada()}): "
            f"{_mensagem_erro_sanitizada(e)}\n{traceback_sanitizado}"
        )
        raise


@retry_com_backoff(_ERROS_TRANSITORIOS_DB, tentativas=3, espera_inicial=2.0, fator=2.0)
def _executar_query_com_retry(query: str, params: dict = None) -> pd.DataFrame:
    engine = obter_engine()
    return pd.read_sql(text(query), engine, params=params)
