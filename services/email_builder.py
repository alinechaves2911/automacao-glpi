"""
services/email_builder.py

Monta o objeto MIMEMultipart do e-mail: corpo HTML, gráficos embutidos
(via CID) e anexo do Excel. Não conecta em nada — só recebe HTML já
pronto (de services/renderer.py) e devolve uma mensagem pronta para o
mailer.py enviar.

Extraído do antigo mailer.py, que misturava montagem de MIME com a
conexão SMTP no mesmo módulo.
"""
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage

from config.settings import SMTP_FROM


def construir_mensagem(
    destinatarios,
    assunto,
    html_rendered,
    nome_arquivo_excel,
    graficos=None,  # lista de dicts: [{'cid': 'grafico1', 'caminho': 'charts_tmp/faixa_idade.png'}, ...]
):
    """
    graficos: cada imagem vira um <img src="cid:SEU_CID"> no template.
              No HTML do template, use exatamente: <img src="cid:grafico1" alt="...">
              O 'cid' aqui deve bater com o que está no template.
    """
    graficos = graficos or []

    # 'related' é o tipo certo quando há imagens embutidas referenciadas no próprio HTML (via cid)
    msg = MIMEMultipart('related')
    msg['From'] = SMTP_FROM
    msg['To'] = ", ".join(destinatarios) if isinstance(destinatarios, list) else destinatarios
    msg['Subject'] = assunto

    # Corpo HTML + anexo de arquivo ficam dentro de um 'mixed' aninhado
    msg_alternativo = MIMEMultipart('mixed')
    msg_alternativo.attach(MIMEText(html_rendered, 'html', 'utf-8'))
    msg.attach(msg_alternativo)

    # Embute cada gráfico como imagem inline referenciada pelo CID
    for grafico in graficos:
        with open(grafico['caminho'], 'rb') as img_file:
            img = MIMEImage(img_file.read())
            img.add_header('Content-ID', f"<{grafico['cid']}>")
            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(grafico['caminho']))
            msg.attach(img)

    # Anexo Excel
    with open(nome_arquivo_excel, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="xlsx")
        attachment.add_header('Content-Disposition', 'attachment', filename=nome_arquivo_excel)
        msg_alternativo.attach(attachment)

    return msg
