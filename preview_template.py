"""
preview_template.py

Renderiza um template de e-mail com dados fictícios e abre o resultado
(preview.html) no navegador. Ferramenta de desenvolvimento — não faz
parte do fluxo de produção, não é chamada por main.py, cron nem systemd.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, ChainableUndefined
import webbrowser


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
PREVIEW_FILE = BASE_DIR / "preview.html"

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    undefined=ChainableUndefined,
    autoescape=True,
)


def _css_inline() -> str:
    return (TEMPLATES_DIR / "css" / "email_styles.css").read_text(encoding="utf-8")


def dados_comuns() -> dict:
    return {
        "titulo_relatorio": "Atendimento Mensal - Suporte Técnico - 1º Nível",
        "periodo": "Agosto/2026",
        "nome_anexo": "Atendimento_Mensal_Grupo_suporte_tecnico_1_nivel.xlsx",
        "rodape_linha1": "Equipe de Automação de Relatórios",
        "rodape_linha2": "Organização Exemplo",
        "css_inline": _css_inline(),
    }


def _tabela(linhas: list[dict]) -> str:
    """Gera uma tabela HTML simples a partir de uma lista de dicts, com as
    mesmas colunas na mesma ordem em que aparecem no primeiro item."""
    if not linhas:
        return None
    colunas = list(linhas[0].keys())
    cabecalho = "".join(f"<th>{c}</th>" for c in colunas)
    linhas_html = "".join(
        "<tr>" + "".join(f"<td>{linha[c]}</td>" for c in colunas) + "</tr>"
        for linha in linhas
    )
    return f"<table><thead><tr>{cabecalho}</tr></thead><tbody>{linhas_html}</tbody></table>"


def dados_por_template() -> dict:
    """Overrides específicos de cada template, mesclados com dados_comuns()
    na hora de renderizar. As chaves usadas (kpis/tabelas/dados_por_grupo)
    seguem a mesma estrutura que services/reporter_runner.py monta a
    partir de dados reais — ver config/reports.py para o "kpis"/"tabelas"
    de cada relatório."""
    return {
        "relatorio_mensal_grupo.html": {
            "kpis": {
                "resumo_total_mes": 12,
                "resumo_resolvidos_mes": 9,
                "resumo_em_aberto_mes": 3,
            },
            "tabelas": {
                "resumo_mensal": _tabela([
                    {"Total no Mês": 12, "Resolvidos": 9, "Em Aberto": 3},
                ]),
                "tendencia_prioridade": _tabela([
                    {"Prioridade": "Alta", "Total": 2},
                    {"Prioridade": "Média", "Total": 5},
                    {"Prioridade": "Baixa", "Total": 5},
                ]),
                "por_tecnico": _tabela([
                    {"Técnico": "Técnico A", "Novo": 1, "Em Atendimento": 2, "Pendente": 0, "Solucionado": 4, "Fechado": 0, "Total Geral": 7},
                    {"Técnico": "Técnico B", "Novo": 0, "Em Atendimento": 1, "Pendente": 1, "Solucionado": 3, "Fechado": 0, "Total Geral": 5},
                ]),
                "por_categoria": _tabela([
                    {"Categoria": "Solicitações e Alterações", "Total": 5, "Resolvidos": 4, "Em Aberto": 1},
                    {"Categoria": "Software", "Total": 4, "Resolvidos": 3, "Em Aberto": 1},
                    {"Categoria": "Hardware", "Total": 3, "Resolvidos": 2, "Em Aberto": 1},
                ]),
                "sla_mensal": _tabela([
                    {"Total Com SLA": 10, "Dentro Do Prazo": 8, "Fora Do Prazo": 1, "Em Andamento (Dentro do Prazo)": 1, "% SLA": "80.0%"},
                ]),
                "sla_tecnico": _tabela([
                    {"Técnico": "Técnico A", "Total Com SLA": 6, "Dentro Do Prazo": 5, "Fora Do Prazo": 1, "% SLA OK": "83.3%"},
                    {"Técnico": "Técnico B", "Total Com SLA": 4, "Dentro Do Prazo": 3, "Fora Do Prazo": 0, "% SLA OK": "100.0%"},
                ]),
                "tempo_medio": _tabela([
                    {"Média de Horas p/ Primeira Resposta": "1h 20min", "Média de Horas p/ Resolução": "4h 10min", "Total Resolvidos": 9},
                ]),
            },
        },

        "relatorio_semanal_grupo.html": {
            "titulo_relatorio": "Atendimento Semanal - Suporte Técnico - 1º Nível",
            "nome_anexo": "Atendimento_Semanal_Grupo_suporte_tecnico_1_nivel.xlsx",
            "kpis": {
                "situacao_total_ativos": 8,
                "situacao_novos": 3,
                "situacao_em_atendimento": 4,
                "situacao_pendentes": 1,
                "situacao_alta_prioridade": 1,
                "resumo_abertos": 5,
                "resumo_resolvidos": 3,
            },
            "tabelas": {
                "situacao_atual": _tabela([
                    {"Total Ativos": 8, "Novos": 3, "Em Atendimento": 4, "Pendentes": 1, "Alta Prioridade": 1},
                ]),
                "resumo_semanal": _tabela([
                    {"Abertos na Semana": 5, "Resolvidos na Semana": 3},
                ]),
                "status_tecnico_7d": _tabela([
                    {"Técnico": "Técnico A", "Novo": 1, "Em Atendimento": 1, "Pendente": 0, "Solucionado": 2, "Fechado": 0, "Total Geral": 4},
                    {"Técnico": "Técnico B", "Novo": 0, "Em Atendimento": 1, "Pendente": 1, "Solucionado": 1, "Fechado": 0, "Total Geral": 3},
                ]),
                "sla_semanal": _tabela([
                    {"Semana Início": "2026-08-24", "Total Com SLA": 5, "Dentro Do Prazo": 4, "Fora Do Prazo": 1},
                ]),
                "reaberturas": None,
                "tempo_medio": _tabela([
                    {"Média de Horas p/ Primeira Resposta": "0h 45min", "Média de Horas p/ Resolução": "3h 05min", "Total Resolvidos": 3},
                ]),
            },
        },

        "relatorio_criticos_grupo.html": {
            "titulo_relatorio": "Chamados Críticos - Suporte Técnico - 1º Nível",
            "nome_anexo": "Chamados_Criticos_Grupo_suporte_tecnico_1_nivel.xlsx",
            "tabelas": {
                "chamados_criticos": _tabela([
                    {"Chamado": 101, "Título": "Impressora não responde", "Técnico": "Técnico A", "Categoria": "Hardware", "Prioridade": "Baixa", "Status": "Pendente", "Dias em Aberto": 9},
                    {"Chamado": 87, "Título": "Lentidão no sistema", "Técnico": "Não Atribuído", "Categoria": "Software", "Prioridade": "Média", "Status": "Em atendimento", "Dias em Aberto": 7},
                ]),
            },
        },

        "relatorio_anual_grupo.html": {
            "titulo_relatorio": "Atendimento Anual - Desenvolvimento e Aplicações",
            "nome_anexo": "Atendimento_Anual_Grupo_desenvolvimento_e_aplicacoes.xlsx",
            "kpis": {
                "resumo_anual": 42,
                "resumo_resolvidos_anual": 38,
            },
            "tabelas": {
                "resumo_anual": _tabela([
                    {"Total no Ano": 42, "Resolvidos": 38, "Em Aberto": 4},
                ]),
                "tempo_medio_ano": None,
                "tendencia_prioridade": _tabela([
                    {"Prioridade": "Alta", "Total": 6},
                    {"Prioridade": "Média", "Total": 18},
                    {"Prioridade": "Baixa", "Total": 18},
                ]),
                "por_tecnico_ano": _tabela([
                    {"Técnico": "Técnico A", "Total": 22, "Resolvidos": 20, "Em Aberto": 2},
                    {"Técnico": "Técnico B", "Total": 20, "Resolvidos": 18, "Em Aberto": 2},
                ]),
                "por_categoria_ano": _tabela([
                    {"Categoria": "Solicitações e Alterações", "Total": 15, "Resolvidos": 14, "Em Aberto": 1},
                    {"Categoria": "Software", "Total": 14, "Resolvidos": 12, "Em Aberto": 2},
                    {"Categoria": "Hardware", "Total": 13, "Resolvidos": 12, "Em Aberto": 1},
                ]),
                "sla_anual": _tabela([
                    {"Total Com SLA": 40, "Dentro Do Prazo": 34, "Fora Do Prazo": 4, "Em Andamento (Dentro do Prazo)": 2, "% SLA OK": "85.0%"},
                ]),
                "sla_tecnico_ano": _tabela([
                    {"Técnico": "Técnico A", "Total Com SLA": 21, "Dentro Do Prazo": 18, "Fora Do Prazo": 3},
                    {"Técnico": "Técnico B", "Total Com SLA": 19, "Dentro Do Prazo": 16, "Fora Do Prazo": 1},
                ]),
            },
        },

        "relatorio_diretoria_mensal.html": {
            "titulo_relatorio": "Consolidado Mensal (mês anterior)",
            "nome_anexo": "Atendimento_Mensal_Diretoria.xlsx",
            "dados_por_grupo": {
                "resumo_geral": [
                    {"grupo": "Suporte Técnico - 1º Nível", "total_no_mes": 12, "resolvidos": 9, "em_aberto": 3},
                    {"grupo": "Suporte Técnico - 2º Nível", "total_no_mes": 8, "resolvidos": 7, "em_aberto": 1},
                    {"grupo": "Administração de Sistemas", "total_no_mes": 5, "resolvidos": 5, "em_aberto": 0},
                    {"grupo": "Redes e Telecomunicações", "total_no_mes": 6, "resolvidos": 4, "em_aberto": 2},
                    {"grupo": "Desenvolvimento e Aplicações", "total_no_mes": 3, "resolvidos": 3, "em_aberto": 0},
                ],
                "sla_geral": [
                    {"grupo": "Suporte Técnico - 1º Nível", "percentual_sla": 78.0, "dentro_do_prazo": 9, "fora_do_prazo": 2},
                    {"grupo": "Suporte Técnico - 2º Nível", "percentual_sla": 92.0, "dentro_do_prazo": 7, "fora_do_prazo": 1},
                    {"grupo": "Administração de Sistemas", "percentual_sla": None, "dentro_do_prazo": 0, "fora_do_prazo": 0},
                    {"grupo": "Redes e Telecomunicações", "percentual_sla": 66.0, "dentro_do_prazo": 4, "fora_do_prazo": 2},
                    {"grupo": "Desenvolvimento e Aplicações", "percentual_sla": 100.0, "dentro_do_prazo": 3, "fora_do_prazo": 0},
                ],
            },
            "tabelas": {
                "resumo_geral": _tabela([
                    {"Grupo": "Suporte Técnico - 1º Nível", "Total no Mês": 12, "Resolvidos": 9, "Em Aberto": 3},
                    {"Grupo": "Suporte Técnico - 2º Nível", "Total no Mês": 8, "Resolvidos": 7, "Em Aberto": 1},
                ]),
                "sla_geral": _tabela([
                    {"Grupo": "Suporte Técnico - 1º Nível", "Total Com SLA": 11, "Dentro Do Prazo": 9, "Fora Do Prazo": 2, "% SLA": "78.0%"},
                ]),
                "sla_tecnico": _tabela([
                    {"Grupo": "Suporte Técnico - 1º Nível", "Técnico": "Técnico A", "Total Com SLA": 6, "% SLA OK": "83.3%"},
                ]),
                "por_tecnico": _tabela([
                    {"Técnico": "Técnico A", "Total": 22, "Resolvidos": 20, "Em Aberto": 2},
                ]),
                "por_categoria": _tabela([
                    {"Categoria": "Solicitações e Alterações", "Total": 15, "Resolvidos": 14, "Em Aberto": 1},
                ]),
            },
        },
    }


def listar_templates() -> list[str]:
    return sorted(
        file.name
        for file in TEMPLATES_DIR.glob("*.html")
        if file.name != "base_email.html"
    )


def escolher_template() -> str | None:
    templates = listar_templates()

    if not templates:
        print("Nenhum template encontrado.")
        return None

    print()
    print("=" * 60)
    print("TEMPLATES DISPONÍVEIS")
    print("=" * 60)

    for indice, template in enumerate(templates, start=1):
        print(f"{indice} - {template}")

    print()

    while True:
        escolha = input("Escolha o relatório: ").strip()
        try:
            indice = int(escolha)
            if 1 <= indice <= len(templates):
                return templates[indice - 1]
        except ValueError:
            pass
        print("Opção inválida. Tente novamente.")


def gerar_preview(nome_template: str) -> Path:
    print()
    print(f"Renderizando: {nome_template}")

    template = env.get_template(nome_template)

    contexto = dados_comuns()
    contexto.update(dados_por_template().get(nome_template, {}))

    html = template.render(**contexto)

    PREVIEW_FILE.write_text(html, encoding="utf-8")

    print()
    print("Preview gerado com sucesso!")
    print(f"Arquivo: {PREVIEW_FILE}")

    return PREVIEW_FILE


def main():
    nome_template = escolher_template()

    if not nome_template:
        return

    preview = gerar_preview(nome_template)

    print()
    print("=" * 60)
    print("ABRINDO PREVIEW")
    print("=" * 60)

    try:
        webbrowser.open(preview.as_uri())
    except Exception:
        pass

    print()
    print("Preview disponível em:")
    print(preview)


if __name__ == "__main__":
    main()
