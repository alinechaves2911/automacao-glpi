"""
services/retry.py

Decorator simples de retry com backoff exponencial, sem dependência
externa (nada de tenacity/backoff no requirements.txt só por causa
disso). Cobre o item do checklist: "Retry/backoff em caso de falha
transitória de conexão com o banco ou SMTP — hoje uma falha de rede
momentânea derruba o relatório inteiro sem nova tentativa."

Uso:
    from services.retry import retry_com_backoff

    @retry_com_backoff((OperationalError, TimeoutError), tentativas=3)
    def minha_funcao():
        ...

Importante: só use isto em cima de operações IDEMPOTENTES (conectar,
autenticar, executar uma SELECT). NÃO usar em cima de "enviar e-mail"
inteiro (server.sendmail) sem cuidado extra — reenviar após uma falha
parcial de SMTP pode duplicar o e-mail para quem já recebeu.
"""
import time
from functools import wraps

from services.logger import logger


def retry_com_backoff(exceptions, tentativas: int = 3, espera_inicial: float = 2.0, fator: float = 2.0):
    """
    exceptions: tupla de classes de exceção que justificam nova tentativa
                (ex: erros de rede/timeout). Qualquer outra exceção sobe
                na hora, sem retry — não faz sentido tentar de novo um
                erro de sintaxe SQL ou de credencial inválida.
    tentativas: número total de tentativas (1 = sem retry).
    espera_inicial: segundos de espera antes da 2ª tentativa.
    fator: multiplicador da espera a cada nova tentativa (backoff exponencial).
    """
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            espera = espera_inicial
            ultima_excecao = None
            for tentativa in range(1, tentativas + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    ultima_excecao = e
                    if tentativa == tentativas:
                        logger.error(
                            f"'{func.__name__}' falhou após {tentativas} tentativa(s): "
                            f"{type(e).__name__}: {e}"
                        )
                        raise
                    logger.warning(
                        f"'{func.__name__}' falhou na tentativa {tentativa}/{tentativas} "
                        f"({type(e).__name__}: {e}). Nova tentativa em {espera:.0f}s..."
                    )
                    time.sleep(espera)
                    espera *= fator
            # Inalcançável na prática (o raise acima cobre o último caso),
            # mas mantém o linter feliz e serve de rede de segurança.
            if ultima_excecao:
                raise ultima_excecao
        return wrapper
    return decorador
