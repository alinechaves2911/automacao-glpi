"""
config/reports.py

Registro central de todos os relatórios. Cada relatório novo = uma entrada
nova aqui, sem precisar duplicar lógica no main.py.

Estrutura alinhada ao dashboard Grafana existente (GLPI - Atendimentos):
cada seção do dashboard vira um dataset/gráfico/tabela aqui, agrupados
por relatório (semanal / mensal / anual).

O SQL de cada dataset NÃO fica mais escrito aqui dentro. Cada entrada em
"queries" aponta para um arquivo .sql em sql/<grupo>/<periodo>/<nome>.sql,
carregado por _sql() na importação deste módulo. Isso permite estudar,
revisar e versionar cada consulta individualmente, com highlight de SQL
de verdade no editor, em vez de strings Python concatenadas.

Exemplo de árvore:
    sql/
    ├── infra/
    │   ├── criticos/chamados.sql
    │   ├── semanal/situacao_atual.sql
    │   ├── mensal/resumo_mensal.sql
    │   └── anual/resumo_anual.sql
    └── servicedesk/
        ├── criticos/chamados.sql
        ├── semanal/situacao_atual.sql
        └── mensal/resumo_mensal.sql
"""
import os
from functools import lru_cache


_SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sql")


@lru_cache(maxsize=None)
def _sql(caminho_relativo: str) -> str:
    """
    Carrega o conteúdo de um arquivo .sql a partir de sql/<caminho_relativo>.
    O resultado fica em cache (lru_cache) — o arquivo só é lido do disco
    uma vez por execução, mesmo que vários relatórios usem a mesma query.
    """
    caminho_absoluto = os.path.normpath(os.path.join(_SQL_DIR, caminho_relativo))
    with open(caminho_absoluto, "r", encoding="utf-8") as f:
        return f.read()


# ==================================================================
# Rótulos de exibição — nome técnico da coluna (como vem do banco)
# -> nome bonito para exibir nas tabelas HTML dos e-mails.
# Usado apenas no rename() antes do to_html(), nunca dentro do SQL.
# ==================================================================
COLUNAS_LABEL = {
    "grupo": "Grupo",
    "tecnico": "Técnico",
    "chamado_id": "Chamado",
    "titulo": "Título",
    "categoria": "Categoria",
    "prioridade_nome": "Prioridade",
    "status_nome": "Status",
    "dias_em_aberto": "Dias em Aberto",
    "data_abertura": "Data de Abertura",
    "data_ultima_reabertura": "Última Reabertura",
    "qtd_reaberturas": "Quantidade Reaberturas",
    "semana_inicio": "Semana Início",
    "total_com_sla": "Total Com SLA",
    "dentro_do_prazo": "Dentro Do Prazo",
    "fora_do_prazo": "Fora Do Prazo",
    "percentual_sla_ok": "% SLA OK",
    "percentual_sla": "% SLA",
    "total_ativos": "Total Ativos",
    "novos": "Novos",
    "em_atendimento": "Em Atendimento",
    "pendentes": "Pendentes",
    "alta_prioridade": "Alta Prioridade",
    "abertos_na_semana": "Abertos na Semana",
    "resolvidos_na_semana": "Resolvidos na Semana",
    "total": "Total",
    "resolvidos": "Resolvidos",
    "em_aberto": "Em Aberto",
    "total_no_mes": "Total no Mês",
    "total_no_ano": "Total no Ano",
    "media_horas_resolucao": "Média de Horas p/ Resolução",
    "total_resolvidos": "Total Resolvidos",
    "media_horas_primeira_resposta": "Média de Horas p/ Primeira Resposta",
    "em_andamento_prazo": "Em Andamento (Dentro do Prazo)",
}


REPORTS = {
        # diretoria
        "relatorio_mensal_diretores": {
                "queries": {
                    "resumo_geral": _sql("diretoria/mensal/resumo_geral_por_grupo.sql"),
                    "por_tecnico": _sql("diretoria/mensal/tecnicos_que_mais_atendem.sql"),
                    "por_categoria": _sql("diretoria/mensal/categorias_mais_atendidas.sql"),
                    "tempo_medio": _sql("diretoria/mensal/tempo_medio_atendimento_por_grupo.sql"),
                    "tendencia_prioridade": _sql("diretoria/mensal/tendencia_prioridade_grupo.sql"),
                    "sla_geral": _sql("diretoria/mensal/sla_geral.sql"),
                    "sla_tecnico": _sql("diretoria/mensal/sla_por_tecnico_geral.sql"),
                },
                "template": "relatorio_diretoria_mensal.html",
                "assunto": "Consolidado Mensal - Diretoria",
                "titulo": "Consolidado Mensal (mês anterior)",
                "destinatarios_env": "DESTINATARIOS_DIRETORIA",
                "nome_arquivo_excel": "Atendimento_Mensal_Diretoria.xlsx",
                "periodo": "mes_anterior",
                "kpis": {
                    "resumo_total_mes": ("resumo_geral", "total_no_mes"),
                    "resumo_resolvidos_mes": ("resumo_geral", "resolvidos"),
                    "resumo_em_aberto_mes": ("resumo_geral", "em_aberto"),
                },
                "graficos": [
                    {
                        "tipo": "barras",
                        "dataset": "tendencia_prioridade",
                        "modo": "contagem",
                        "coluna": "prioridade_nome",
                        "titulo": "Tendência de Prioridade",
                        "cid": "grafico_prioridade_mes",
                    },
                    {
                        "tipo": "pizza",
                        "dataset": "sla_geral",
                        "modo": "soma_colunas",
                        "colunas": [
                            "dentro_do_prazo",
                            "fora_do_prazo",
                            "em_andamento_prazo"
                        ],
                        "labels": [
                            "Dentro do prazo",
                            "Fora do prazo",
                            "Em andamento (Dentro do Prazo)"
                        ],
                    "cores": ["#28a745", "#dc3545","#ffc107"],
                        "titulo": "SLA geral",
                        "cid": "grafico_sla_mes",
                    },
                ],
                "tabelas": [
                    "resumo_geral",
                    "por_tecnico",
                    "por_categoria",
                    "tempo_medio",
                    "sla_geral",
                    "sla_tecnico",
                ],
                "colunas_horas": {
                    "tempo_medio": [
                        "media_horas_primeira_resposta",
                        "media_horas_resolucao",
                    ],
                },
                "colunas_percentual": {
                    "sla_geral": ["percentual_sla"],
                    "sla_tecnico": ["percentual_sla_ok"],
                },
                # Datasets que o template Jinja itera diretamente como lista de
                # dicts (ex: {% for linha in resumo_geral %}), além de usá-los
                # como tabela HTML acima. Antes vinha hardcoded em main.py;
                # movido pra cá durante a unificação com reporter_runner.py
                # pra não ficar escondido em código Python que não é
                # específico deste relatório.
                "dados_por_grupo_datasets": ["resumo_geral", "sla_geral"],
            },


        "atendimento_mensal_grupo": {
            "tipo": "por_grupo",
            "tipo_relatorio": "mensal",

            "grupos": [
                "Suporte Técnico - 1º Nível",
                "Suporte Técnico - 2º Nível",
                "Administração de Sistemas",
                "Redes e Telecomunicações",
                "Desenvolvimento e Aplicações",
            ],

            "queries": {
                "resumo_mensal": _sql("mensal/resumo_mensal.sql"),
                "por_tecnico": _sql("mensal/por_tecnico.sql"),
                "por_categoria": _sql("mensal/por_categoria.sql"),
                "tempo_medio": _sql("mensal/tempo_medio.sql"),
                "tendencia_prioridade": _sql("mensal/tendencia_prioridade.sql"),
                "sla_mensal": _sql("mensal/sla_mensal.sql"),
                "sla_tecnico": _sql("mensal/sla_tecnico.sql"),
            },

            "datasets_por_grupo": [
                "resumo_mensal",
                "por_tecnico",
                "por_categoria",
                "tempo_medio",
                "tendencia_prioridade",
                "sla_mensal",
                "sla_tecnico",
            ],

            "template": "relatorio_mensal_grupo.html",

            "assunto": "Atendimento Mensal - {{ grupo }}",

            "titulo": "Atendimento Mensal - {{ grupo }}",


            "nome_arquivo_excel": "Atendimento_Mensal_Grupo.xlsx",

            "periodo": "mes_anterior",

            "kpis": {
                "resumo_total_mes": ("resumo_mensal", "total_no_mes"),
                "resumo_resolvidos_mes": ("resumo_mensal", "resolvidos"),
                "resumo_em_aberto_mes": ("resumo_mensal", "em_aberto"),
            },

            "graficos": [
                {
                    "tipo": "barras",
                    "dataset": "tendencia_prioridade",
                    "modo": "contagem",
                    "coluna": "prioridade_nome",
                    "titulo": "Tendência de Prioridade",
                    "cid": "grafico_prioridade_mes",
                },
                {
                    "tipo": "pizza",
                    "dataset": "sla_mensal",
                    "modo": "soma_colunas",
                    "colunas": [
                        "dentro_do_prazo",
                        "fora_do_prazo",
                        "em_andamento_prazo",
                    ],
                    "labels": [
                        "Dentro do prazo",
                        "Fora do prazo",
                        "Em andamento (Dentro do Prazo)",
                    ],
                    "cores": [
                        "#28a745",
                        "#dc3545",
                        "#ffc107",
                    ],
                    "titulo": "SLA do Mês",
                    "cid": "grafico_sla_mes",
                },
            ],

            "tabelas": [
                "resumo_mensal",
                "por_tecnico",
                "por_categoria",
                "tempo_medio",
                "sla_mensal",
                "sla_tecnico",
            ],

            "colunas_horas": {
                "tempo_medio": [
                    "media_horas_primeira_resposta",
                    "media_horas_resolucao",
                ],
            },
        },
        "atendimento_semanal_grupo": {
            "tipo": "por_grupo",
            "tipo_relatorio": "semanal",
            "grupos": [
                "Suporte Técnico - 1º Nível",
                "Suporte Técnico - 2º Nível",
                "Administração de Sistemas",
                "Redes e Telecomunicações",
                "Desenvolvimento e Aplicações",
            ],

            "queries": {
                "situacao_atual": _sql("semanal/situacao_atual.sql"),
                "resumo_semanal": _sql("semanal/resumo_semanal.sql"),
                "status_tecnico_7d": _sql("semanal/status_tecnico_7d.sql"),
                "sla_semanal": _sql("semanal/sla_semanal.sql"),
                "reaberturas": _sql("semanal/reaberturas.sql"),
                "tempo_medio": _sql("semanal/tempo_medio.sql"),
            },

            "datasets_por_grupo": [
                "situacao_atual",
                "resumo_semanal",
                "status_tecnico_7d",
                "sla_semanal",
                "reaberturas",
                "tempo_medio",
            ],

            "template": "relatorio_semanal_grupo.html",

            "assunto": "Atendimento Semanal - {{ grupo }}",

            "titulo": "Atendimento Semanal - {{ grupo }}",


            "nome_arquivo_excel": "Atendimento_Semanal_Grupo.xlsx",

            "periodo": "semana_anterior",

            "kpis": {
                "situacao_total_ativos": (
                    "situacao_atual",
                    "total_ativos",
                ),
                "situacao_novos": (
                    "situacao_atual",
                    "novos",
                ),
                "situacao_em_atendimento": (
                    "situacao_atual",
                    "em_atendimento",
                ),
                "situacao_pendentes": (
                    "situacao_atual",
                    "pendentes",
                ),
                "situacao_alta_prioridade": (
                    "situacao_atual",
                    "alta_prioridade",
                ),
                "resumo_abertos": (
                    "resumo_semanal",
                    "abertos_na_semana",
                ),
                "resumo_resolvidos": (
                    "resumo_semanal",
                    "resolvidos_na_semana",
                ),
            },

            "graficos": [
                {
                    "tipo": "pizza",
                    "dataset": "sla_semanal",
                    "modo": "soma_colunas",
                    "colunas": [
                        "dentro_do_prazo",
                        "fora_do_prazo",
                        "em_andamento_prazo",
                    ],
                    "labels": [
                        "Dentro do prazo",
                        "Fora do prazo",
                        "Em andamento (Dentro do Prazo)",
                    ],
                    "cores": [
                        "#17a2b8",
                        "#dc3545",
                        "#ffc107",
                    ],
                    "titulo": "SLA da Semana",
                    "cid": "grafico_sla_semanal",
                },
            ],

            "tabelas": [
                "situacao_atual",
                "resumo_semanal",
                "status_tecnico_7d",
                "sla_semanal",
                "reaberturas",
                "tempo_medio",
            ],

            "colunas_horas": {
                "tempo_medio": [
                    "media_horas_primeira_resposta",
                    "media_horas_resolucao",
                ],
            },
        },
        "atendimento_criticos_grupo": {
            "tipo": "por_grupo",
            "tipo_relatorio": "criticos",
            "grupos": [
                "Suporte Técnico - 1º Nível",
                "Suporte Técnico - 2º Nível",
                "Administração de Sistemas",
                "Redes e Telecomunicações",
                "Desenvolvimento e Aplicações",
            ],
            "queries": {
                "chamados_criticos": _sql("criticos/chamados_criticos.sql"),
            },
            "datasets_por_grupo": [
                "chamados_criticos",
            ],
            "template": "relatorio_criticos_grupo.html",
            "assunto": "Chamados Críticos - {{ grupo }}",
            "titulo": "Chamados Críticos - {{ grupo }}",
            "nome_arquivo_excel": "Chamados_Criticos_Grupo.xlsx",
            "periodo": "hoje",
            "tabelas": [
                "chamados_criticos",
    
            ],
        },
        "atendimento_anual_grupo": {
            "tipo": "por_grupo",
            "tipo_relatorio": "anual",
            "grupos": [
                "Suporte Técnico - 1º Nível",
                "Suporte Técnico - 2º Nível",
                "Administração de Sistemas",
                "Redes e Telecomunicações",
                "Desenvolvimento e Aplicações",
            ],
            "queries": {
                "resumo_anual": _sql("anual/resumo_anual.sql"),
                "por_tecnico_ano": _sql("anual/por_tecnico_ano.sql"),
                "por_categoria_ano": _sql("anual/por_categoria_ano.sql"),
                "tendencia_prioridade": _sql("anual/tendencia_prioridade.sql"),
                "tempo_medio_ano": _sql("anual/tempo_medio_ano.sql"),
                "sla_anual": _sql("anual/sla_anual.sql"),
                "sla_tecnico_ano": _sql("anual/sla_tecnico_ano.sql"),
            },
            "datasets_por_grupo": [
                "resumo_anual",
                "por_tecnico_ano",
                "por_categoria_ano",
                "tendencia_prioridade",
                "tempo_medio_ano",
                "sla_anual",
                "sla_tecnico_ano",
            ],
            "template": "relatorio_anual_grupo.html",
            "assunto": "Atendimento Anual - {{ grupo }}",
            "titulo": "Atendimento Anual - {{ grupo }}",
            "nome_arquivo_excel": "Atendimento_Anual_Grupo.xlsx",
            "periodo": "ano_anterior",
            "kpis": {
                "resumo_anual": ("resumo_anual", "total_no_ano"),
                "resumo_resolvidos_anual": ("resumo_anual", "resolvidos"),
            },
            "graficos": [
                {
                    "tipo": "barras",
                    "dataset": "tempo_medio_ano",
                    "modo": "soma_colunas",
                    "colunas": [
                        "total_resolvidos",
                    ],
                    "labels": [
                        "Total Resolvidos",
                    ],
                    "titulo": "Resolvidos no Ano por Técnico",
                    "cid": "grafico_resolvidos_ano",
                },
            ],
            "tabelas": [
                "resumo_anual",
                "por_tecnico_ano",
                "por_categoria_ano",
                "tendencia_prioridade",
                "tempo_medio_ano",
                "sla_anual",
                "sla_tecnico_ano",
            ],
            "colunas_horas": {
                "tempo_medio_ano": [
                    "media_horas_resolucao",
                ],
            },
        },
}