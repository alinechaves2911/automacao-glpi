"""
config/groups.py

Grupos utilizados nos relatórios GLPI.

Lista alinhada com os grupos cadastrados no banco do GLPI (tabela
glpi_groups). "id" é o id do grupo no banco, mantido aqui só como
referência — o matching em services/reporter_runner.py é feito pelo
campo "nome".
"""

GRUPOS = {
    "suporte_n1": {
        "id": 1,
        "nome": "Suporte Técnico - 1º Nível",
        "slug": "suporte_tecnico_1_nivel",
        "destinatarios": {
            "mensal": "GRUPO_SUPORTE_N1_MENSAL",
            "semanal": "GRUPO_SUPORTE_N1_SEMANAL",
            "anual": "GRUPO_SUPORTE_N1_ANUAL",
            "criticos": "GRUPO_SUPORTE_N1_CRITICOS",
        }
    },

    "suporte_n2": {
        "id": 2,
        "nome": "Suporte Técnico - 2º Nível",
        "slug": "suporte_tecnico_2_nivel",
        "destinatarios": {
            "mensal": "GRUPO_SUPORTE_N2_MENSAL",
            "semanal": "GRUPO_SUPORTE_N2_SEMANAL",
            "anual": "GRUPO_SUPORTE_N2_ANUAL",
            "criticos": "GRUPO_SUPORTE_N2_CRITICOS",
        }
    },

    "admin_sistemas": {
        "id": 3,
        "nome": "Administração de Sistemas",
        "slug": "administracao_de_sistemas",
        "destinatarios": {
            "mensal": "GRUPO_ADMSIS_MENSAL",
            "semanal": "GRUPO_ADMSIS_SEMANAL",
            "anual": "GRUPO_ADMSIS_ANUAL",
            "criticos": "GRUPO_ADMSIS_CRITICOS",
        }
    },

    "redes_telecom": {
        "id": 4,
        "nome": "Redes e Telecomunicações",
        "slug": "redes_e_telecomunicacoes",
        "destinatarios": {
            "mensal": "GRUPO_REDES_MENSAL",
            "semanal": "GRUPO_REDES_SEMANAL",
            "anual": "GRUPO_REDES_ANUAL",
            "criticos": "GRUPO_REDES_CRITICOS",
        }
    },

    "dev_aplicacoes": {
        "id": 5,
        "nome": "Desenvolvimento e Aplicações",
        "slug": "desenvolvimento_e_aplicacoes",
        "destinatarios": {
            "mensal": "GRUPO_DEV_MENSAL",
            "semanal": "GRUPO_DEV_SEMANAL",
            "anual": "GRUPO_DEV_ANUAL",
            "criticos": "GRUPO_DEV_CRITICOS",
        }
    },
}
