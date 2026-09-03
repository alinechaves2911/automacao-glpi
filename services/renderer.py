"""
services/renderer.py

Responsável só por transformar (template Jinja + CSS + contexto) em HTML
final, pronto para virar corpo de e-mail. Não sabe nada sobre SMTP,
MIME ou anexos — só entrega uma string de HTML.

Extraído do antigo mailer.py, que fazia isso e mais MIME/SMTP no mesmo
lugar. Separar deixa o caminho livre para, no futuro, gerar um PDF a
partir do mesmo HTML sem tocar em nada relacionado a envio de e-mail.
"""
import os
from jinja2 import Environment, FileSystemLoader
from premailer import transform

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
CSS_PATH = os.path.join(TEMPLATES_DIR, 'css', 'email_styles.css')

_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))


def carregar_css() -> str:
    with open(CSS_PATH, 'r', encoding='utf-8') as f:
        return f.read()


def renderizar_email(nome_template: str, contexto: dict) -> str:
    """
    Renderiza o template Jinja indicado com o contexto fornecido e aplica
    o premailer (transform), que converte as regras do <style> em estilo
    inline em cada tag — necessário porque a maioria dos clientes de
    e-mail ignora ou trunca <style> no <head>.

    contexto já deve conter tudo que o template espera: titulo_relatorio,
    tabelas, nome_anexo, css_inline e quaisquer KPIs extras.
    """
    template = _env.get_template(nome_template)
    html_bruto = template.render(**contexto)
    return transform(html_bruto)
