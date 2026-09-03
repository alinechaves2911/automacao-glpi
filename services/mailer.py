"""
services/mailer.py

Só sabe falar SMTP: conectar, autenticar, enviar, encerrar. Não sabe
renderizar template nem montar MIME — isso é responsabilidade de
services/renderer.py e services/email_builder.py, respectivamente.

Essa separação é o que torna trivial, no futuro, trocar "enviar e-mail"
por "gerar PDF" ou "postar no Slack" sem reescrever a parte de SMTP.
"""
import smtplib

from config.settings import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM,
    EMAIL_RODAPE_LINHA1, EMAIL_RODAPE_LINHA2,
)
from services.renderer import renderizar_email, carregar_css
from services.email_builder import construir_mensagem
from services.logger import logger
from services.retry import retry_com_backoff

# Erros que valem retry: falha de conexão/timeout com o servidor SMTP.
# smtplib.SMTPAuthenticationError e afins NÃO estão aqui de propósito —
# credencial errada não se resolve tentando de novo.
_ERROS_TRANSITORIOS_SMTP = (
    smtplib.SMTPConnectError,
    smtplib.SMTPServerDisconnected,
    TimeoutError,
    ConnectionError,
    OSError,
)


@retry_com_backoff(_ERROS_TRANSITORIOS_SMTP, tentativas=3, espera_inicial=2.0, fator=2.0)
def conectar() -> smtplib.SMTP:
    logger.info("Conectando ao servidor SMTP...")
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASS)
    return server


def enviar_relatorio_email(
    destinatarios,
    assunto,
    titulo_relatorio,
    tabelas_html,
    nome_arquivo_excel,
    server_smtp,
    nome_template,
    graficos=None,
    contexto_extra=None,
):
    """
    Orquestra o envio de um relatório: renderiza o HTML (renderer.py),
    monta a mensagem MIME (email_builder.py) e entrega ao servidor SMTP
    já conectado (server_smtp, obtido via conectar()).

    tabelas_html: dict {nome_dataset: html_da_tabela_ou_None}, já pronto
                  (gerado por services/report_renderer.py).
                  No template, acesse com {{ tabelas.nome_dataset }}.

    contexto_extra: variáveis soltas (não tabelas) para uso direto no template,
                     ex: {'situacao_total_ativos': 24, 'resumo_abertos': 2}
                     Usadas em cards de KPI, onde não faz sentido renderizar
                     uma tabela HTML inteira para 1 número só.

    graficos: lista de dicts [{'cid': 'grafico_x', 'caminho': '...png'}, ...]
              gerada por main.py. Além de ser usada por email_builder.py para
              anexar as imagens via Content-ID, também precisa virar um dict
              indexado por cid (graficos_por_cid) para que o template Jinja
              consiga checar se cada gráfico existe antes de renderizar a tag
              <img src="cid:...">, ex: {% if graficos_por_cid.grafico_x %}.
    """
    try:
        graficos_por_cid = {g["cid"]: g for g in (graficos or [])}

        contexto = {
            "titulo_relatorio": titulo_relatorio,
            "tabelas": tabelas_html,
            "nome_anexo": nome_arquivo_excel,
            "css_inline": carregar_css(),
            "graficos_por_cid": graficos_por_cid,
            "rodape_linha1": EMAIL_RODAPE_LINHA1,
            "rodape_linha2": EMAIL_RODAPE_LINHA2,
            **(contexto_extra or {}),
        }

        html_rendered = renderizar_email(nome_template, contexto)

        msg = construir_mensagem(
            destinatarios=destinatarios,
            assunto=assunto,
            html_rendered=html_rendered,
            nome_arquivo_excel=nome_arquivo_excel,
            graficos=graficos,
        )

        server_smtp.sendmail(SMTP_FROM, destinatarios, msg.as_string())
        logger.info(f"E-mail '{assunto}' enviado para: {destinatarios}")
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed: {e}")
        raise Exception("SMTP Authentication Error - verifique credenciais") from e
    
    except smtplib.SMTPRecipientsRefused as e:
        logger.error(f"SMTP Recipients refused: {e}")
        raise Exception(f"Email addresses refused: {e}") from e
    
    except smtplib.SMTPSenderRefused as e:
        logger.error(f"SMTP Sender refused: {e}")
        raise Exception(f"Sender address refused: {e}") from e
    
    except smtplib.SMTPServerDisconnected as e:
        logger.error(f"SMTP Server disconnected: {e}")
        raise Exception("SMTP Server disconnected - reconectando") from e
    
    except smtplib.SMTPException as e:
        logger.error(f"SMTP Error: {e}")
        raise Exception(f"SMTP Error: {str(e)[:100]}") from e
    
    except Exception as e:
        logger.error(f"Unexpected error sending email: {type(e).__name__}: {e}")
        raise