"""
config/settings.py

Carrega e valida as variáveis de ambiente (.env) usadas pelo projeto.
Chamar validar_configuracoes() no início do main.py, antes de qualquer
conexão, para falhar rápido e com mensagem clara se algo estiver faltando.
"""
import os
import re
import sys
from dotenv import load_dotenv

from services.logger import logger

load_dotenv()

# Regex simples (não RFC 5322 completo) só para pegar erros grosseiros de
# digitação no .env (ex: "smtp.exemplo.com.br" sem "@" colado sem querer
# em SMTP_FROM, ou uma vírgula sobrando em DESTINATARIOS_*), não para
# validar e-mail de forma rigorosa.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _int_seguro(nome_var: str, valor_bruto: str, padrao: int) -> int:
    """
    Converte a variável de porta para int sem derrubar o processo com um
    traceback cru no import do módulo (antes de validar_configuracoes()
    poder dar uma mensagem clara). Se o valor não for numérico, mantém o
    padrão e deixa o aviso para o log — validar_configuracoes() decide se
    isso é fatal.
    """
    if valor_bruto is None or valor_bruto == "":
        return padrao
    try:
        return int(valor_bruto)
    except ValueError:
        logger.warning(
            f"{nome_var}='{valor_bruto}' não é um número válido no .env; "
            f"usando o padrão {padrao}. Corrija o .env para evitar isso."
        )
        return padrao


def _destinatarios_por_tipo(nome_var: str, fallback: list) -> list:
    """
    Lê a variável de destinatários específica de um grupo+tipo de
    relatório (ex: GRUPO_INFRA_CRITICOS). Se ela não estiver definida
    (ou estiver vazia) no .env, cai de volta para a lista geral da área
    (ex: DESTINATARIOS_INFRA) — assim quem não quer diferenciar
    destinatários por tipo de relatório não precisa preencher as 3
    variáveis, só a geral.

    Corrige um bug anterior em que GRUPO_INFRA_MENSAL, _SEMANAL e
    _CRITICOS eram, na prática, os três hardcoded para ler sempre de
    DESTINATARIOS_INFRA — ou seja, definir GRUPO_INFRA_CRITICOS no .env
    não tinha efeito nenhum, porque o valor era sobrescrito de qualquer
    forma. Agora cada uma lê sua própria chave primeiro.
    """
    valor_bruto = os.getenv(nome_var)

    if valor_bruto is None or valor_bruto.strip() == "":
        return fallback

    return [email.strip() for email in valor_bruto.split(",")]


DB_HOST = os.getenv("DB_HOST")
DB_PORT = _int_seguro("DB_PORT", os.getenv("DB_PORT"), 3306)
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = _int_seguro("SMTP_PORT", os.getenv("SMTP_PORT"), 587)
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM")

# Servidor Zabbix e nome do host cadastrado lá para o trap de falha
# (scripts/alerta_falha.py) — configurável por ambiente porque lab e
# produção reportam para hosts Zabbix diferentes a partir do mesmo código.
ZABBIX_SERVER = os.getenv("ZABBIX_SERVER", "10.14.8.23")
ZABBIX_HOST = os.getenv("ZABBIX_HOST", "AUTOMACAO-GLPI-LAB")

# Linhas de identificação no rodapé do e-mail (templates/base_email.html).
# Opcionais — em branco, o template simplesmente não exibe a linha.
EMAIL_RODAPE_LINHA1 = os.getenv("EMAIL_RODAPE_LINHA1", "")
EMAIL_RODAPE_LINHA2 = os.getenv("EMAIL_RODAPE_LINHA2", "")

# Teto de tamanho do anexo Excel (MB). Muitos servidores SMTP
# corporativos rejeitam a mensagem inteira acima de um limite (comum:
# 20-25 MB) — abortar ANTES de tentar enviar dá um erro claro no log em
# vez de uma falha genérica de SMTP. ANEXO_TAMANHO_ALERTA_MB é só um
# aviso (o envio segue normalmente), útil pra notar a tendência de
# crescimento antes de bater no limite.
ANEXO_TAMANHO_MAXIMO_MB = _int_seguro("ANEXO_TAMANHO_MAXIMO_MB", os.getenv("ANEXO_TAMANHO_MAXIMO_MB"), 20)
ANEXO_TAMANHO_ALERTA_MB = _int_seguro("ANEXO_TAMANHO_ALERTA_MB", os.getenv("ANEXO_TAMANHO_ALERTA_MB"), 10)

DESTINATARIOS_SUPORTE_N1 = os.getenv("DESTINATARIOS_SUPORTE_N1", "").split(",")
DESTINATARIOS_SUPORTE_N2 = os.getenv("DESTINATARIOS_SUPORTE_N2", "").split(",")
DESTINATARIOS_ADMSIS = os.getenv("DESTINATARIOS_ADMSIS", "").split(",")
DESTINATARIOS_REDES = os.getenv("DESTINATARIOS_REDES", "").split(",")
DESTINATARIOS_DEV = os.getenv("DESTINATARIOS_DEV", "").split(",")
DESTINATARIOS_DIRETORIA = os.getenv("DESTINATARIOS_DIRETORIA", "").split(",")

GRUPO_SUPORTE_N1_MENSAL = _destinatarios_por_tipo("GRUPO_SUPORTE_N1_MENSAL", DESTINATARIOS_SUPORTE_N1)
GRUPO_SUPORTE_N1_SEMANAL = _destinatarios_por_tipo("GRUPO_SUPORTE_N1_SEMANAL", DESTINATARIOS_SUPORTE_N1)
GRUPO_SUPORTE_N1_ANUAL = _destinatarios_por_tipo("GRUPO_SUPORTE_N1_ANUAL", DESTINATARIOS_SUPORTE_N1)
GRUPO_SUPORTE_N1_CRITICOS = _destinatarios_por_tipo("GRUPO_SUPORTE_N1_CRITICOS", DESTINATARIOS_SUPORTE_N1)

GRUPO_SUPORTE_N2_MENSAL = _destinatarios_por_tipo("GRUPO_SUPORTE_N2_MENSAL", DESTINATARIOS_SUPORTE_N2)
GRUPO_SUPORTE_N2_SEMANAL = _destinatarios_por_tipo("GRUPO_SUPORTE_N2_SEMANAL", DESTINATARIOS_SUPORTE_N2)
GRUPO_SUPORTE_N2_ANUAL = _destinatarios_por_tipo("GRUPO_SUPORTE_N2_ANUAL", DESTINATARIOS_SUPORTE_N2)
GRUPO_SUPORTE_N2_CRITICOS = _destinatarios_por_tipo("GRUPO_SUPORTE_N2_CRITICOS", DESTINATARIOS_SUPORTE_N2)

GRUPO_ADMSIS_MENSAL = _destinatarios_por_tipo("GRUPO_ADMSIS_MENSAL", DESTINATARIOS_ADMSIS)
GRUPO_ADMSIS_SEMANAL = _destinatarios_por_tipo("GRUPO_ADMSIS_SEMANAL", DESTINATARIOS_ADMSIS)
GRUPO_ADMSIS_ANUAL = _destinatarios_por_tipo("GRUPO_ADMSIS_ANUAL", DESTINATARIOS_ADMSIS)
GRUPO_ADMSIS_CRITICOS = _destinatarios_por_tipo("GRUPO_ADMSIS_CRITICOS", DESTINATARIOS_ADMSIS)

GRUPO_REDES_MENSAL = _destinatarios_por_tipo("GRUPO_REDES_MENSAL", DESTINATARIOS_REDES)
GRUPO_REDES_SEMANAL = _destinatarios_por_tipo("GRUPO_REDES_SEMANAL", DESTINATARIOS_REDES)
GRUPO_REDES_ANUAL = _destinatarios_por_tipo("GRUPO_REDES_ANUAL", DESTINATARIOS_REDES)
GRUPO_REDES_CRITICOS = _destinatarios_por_tipo("GRUPO_REDES_CRITICOS", DESTINATARIOS_REDES)

GRUPO_DEV_MENSAL = _destinatarios_por_tipo("GRUPO_DEV_MENSAL", DESTINATARIOS_DEV)
GRUPO_DEV_SEMANAL = _destinatarios_por_tipo("GRUPO_DEV_SEMANAL", DESTINATARIOS_DEV)
GRUPO_DEV_ANUAL = _destinatarios_por_tipo("GRUPO_DEV_ANUAL", DESTINATARIOS_DEV)
GRUPO_DEV_CRITICOS = _destinatarios_por_tipo("GRUPO_DEV_CRITICOS", DESTINATARIOS_DEV)

def _emails_invalidos(lista: list) -> list:
    """Retorna os itens de uma lista de destinatários que não parecem e-mail válido, ignorando strings vazias (grupo sem destinatário é tratado à parte)."""
    return [e for e in lista if e.strip() and not _EMAIL_RE.match(e.strip())]


def validar_configuracoes():
    """
    Confere se todas as variáveis de ambiente obrigatórias foram carregadas
    E se os valores fazem sentido (porta numérica, e-mails com formato
    plausível) — antes, só a presença era checada; um DB_PORT não-numérico
    ou um DESTINATARIOS_INFRA com vírgula sobrando (gerando um item vazio
    "meio@mail. com, ") só apareciam como erro genérico no meio da
    execução (ou pior, um e-mail simplesmente não chegava, sem erro
    nenhum). Chamar isso no início do main.py, ANTES de tentar conectar em
    qualquer coisa.
    """
    obrigatorias = {
        "DB_HOST": DB_HOST,
        "DB_NAME": DB_NAME,
        "DB_USER": DB_USER,
        "DB_PASS": DB_PASS,
        "SMTP_HOST": SMTP_HOST,
        "SMTP_USER": SMTP_USER,
        "SMTP_PASS": SMTP_PASS,
        "SMTP_FROM": SMTP_FROM,
    }

    faltando = [nome for nome, valor in obrigatorias.items() if not valor]

    if faltando:
        logger.error(
            f"Variáveis de ambiente faltando ou vazias no .env: {', '.join(faltando)}. "
            "Verifique se o arquivo .env existe na raiz do projeto e contém todas as chaves necessárias."
        )
        sys.exit(1)

    erros_formato = []

    if not (1 <= DB_PORT <= 65535):
        erros_formato.append(f"DB_PORT={DB_PORT} fora do intervalo válido de portas (1-65535)")
    if not (1 <= SMTP_PORT <= 65535):
        erros_formato.append(f"SMTP_PORT={SMTP_PORT} fora do intervalo válido de portas (1-65535)")
    if SMTP_FROM and not _EMAIL_RE.match(SMTP_FROM.strip()):
        erros_formato.append(f"SMTP_FROM='{SMTP_FROM}' não parece um e-mail válido")
    if ANEXO_TAMANHO_MAXIMO_MB <= 0:
        erros_formato.append(f"ANEXO_TAMANHO_MAXIMO_MB={ANEXO_TAMANHO_MAXIMO_MB} precisa ser positivo")
    if ANEXO_TAMANHO_ALERTA_MB > ANEXO_TAMANHO_MAXIMO_MB:
        erros_formato.append(
            f"ANEXO_TAMANHO_ALERTA_MB={ANEXO_TAMANHO_ALERTA_MB} não pode ser maior que "
            f"ANEXO_TAMANHO_MAXIMO_MB={ANEXO_TAMANHO_MAXIMO_MB}"
        )

    for nome_var, lista in (
        ("DESTINATARIOS_SUPORTE_N1", DESTINATARIOS_SUPORTE_N1),
        ("DESTINATARIOS_SUPORTE_N2", DESTINATARIOS_SUPORTE_N2),
        ("DESTINATARIOS_ADMSIS", DESTINATARIOS_ADMSIS),
        ("DESTINATARIOS_REDES", DESTINATARIOS_REDES),
        ("DESTINATARIOS_DEV", DESTINATARIOS_DEV),
        ("DESTINATARIOS_DIRETORIA", DESTINATARIOS_DIRETORIA),
    ):
        invalidos = _emails_invalidos(lista)
        if invalidos:
            erros_formato.append(f"{nome_var} contém e-mail(s) com formato suspeito: {invalidos}")

    if erros_formato:
        logger.error(
            "Configurações do .env com formato inválido: " + "; ".join(erros_formato) +
            ". Corrija o .env antes de rodar em produção."
        )
        sys.exit(1)

    if not DESTINATARIOS_SUPORTE_N1 or DESTINATARIOS_SUPORTE_N1 == ['']:
        logger.warning("DESTINATARIOS_SUPORTE_N1 está vazio — nenhum e-mail de Suporte Técnico - 1º Nível será enviado.")
    if not DESTINATARIOS_SUPORTE_N2 or DESTINATARIOS_SUPORTE_N2 == ['']:
        logger.warning("DESTINATARIOS_SUPORTE_N2 está vazio — nenhum e-mail de Suporte Técnico - 2º Nível será enviado.")
    if not DESTINATARIOS_ADMSIS or DESTINATARIOS_ADMSIS == ['']:
        logger.warning("DESTINATARIOS_ADMSIS está vazio — nenhum e-mail de Administração de Sistemas será enviado.")
    if not DESTINATARIOS_REDES or DESTINATARIOS_REDES == ['']:
        logger.warning("DESTINATARIOS_REDES está vazio — nenhum e-mail de Redes e Telecomunicações será enviado.")
    if not DESTINATARIOS_DEV or DESTINATARIOS_DEV == ['']:
        logger.warning("DESTINATARIOS_DEV está vazio — nenhum e-mail de Desenvolvimento e Aplicações será enviado.")
    if not DESTINATARIOS_DIRETORIA or DESTINATARIOS_DIRETORIA == ['']:
        logger.warning("DESTINATARIOS_DIRETORIA está vazio — nenhum e-mail de Diretoria será enviado.")