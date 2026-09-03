"""
services/charts.py

Gera gráficos como imagens PNG para embutir nos e-mails (via CID).
Reutilizável entre os relatórios (por grupo, diretoria, etc.).
"""
import os
import matplotlib
matplotlib.use('Agg')  # backend sem interface gráfica, essencial para rodar via cron/servidor
import matplotlib.pyplot as plt

# Paleta consistente com o dashboard do Grafana (ajuste as cores se quiser bater 100%)
CORES_PADRAO = ['#17a2b8', '#0056b3', '#28a745', '#ffc107', '#dc3545', '#6c757d']


def gerar_grafico_pizza(labels, valores, titulo, nome_arquivo, output_dir='charts_tmp', cores=None):
    """
    Gera um gráfico de pizza (ex: 'SLA da Semana') e salva como PNG.

    labels: lista de rótulos, ex: ['Dentro do prazo', 'Fora do prazo', 'Em andamento (Dentro do Prazo)']
    valores: lista de valores numéricos correspondentes
    titulo: título exibido acima do gráfico
    nome_arquivo: nome do arquivo de saída (ex: 'sla_semanal.png')
    output_dir: pasta onde salvar (criada automaticamente se não existir)

    Retorna o caminho completo do arquivo gerado.
    """
    # Default mutável evitado de propósito (B006 do ruff): uma lista
    # como valor padrão de argumento é compartilhada entre TODAS as
    # chamadas da função — se algum código um dia mutar 'cores' in-place
    # (ex: cores.append(...)), o efeito vazaria para as próximas
    # chamadas que não passaram 'cores' explicitamente.
    if cores is None:
        cores = ["#28a745", "#dc3545", "#ffc107"]

    os.makedirs(output_dir, exist_ok=True)
    caminho = os.path.join(output_dir, nome_arquivo)

    # Filtra fatias com valor 0 (ou None) - evita labels colidindo em fatias
    # "invisíveis" e percentuais "0.00%" poluindo o gráfico
    labels_filtrados = []
    valores_filtrados = []
    cores_filtradas = []
    for i, v in enumerate(valores):
        if v and v > 0:
            labels_filtrados.append(labels[i])
            valores_filtrados.append(v)
            cores_filtradas.append(cores[i % len(cores)])

    # Se tudo for zero, evita quebrar o matplotlib com uma pizza vazia
    if not valores_filtrados:
        labels_filtrados = ['Sem dados']
        valores_filtrados = [1]
        cores_filtradas = ['#e0e0e0']

    fig, ax = plt.subplots(figsize=(5, 5), dpi=120)
    wedges, texts, autotexts = ax.pie(
        valores_filtrados,
        autopct='%1.2f%%',
        colors=cores_filtradas,
        startangle=90,
        pctdistance=0.75,
        textprops={'fontsize': 10, 'color': 'white', 'fontweight': 'bold'}
    )
    ax.set_title(titulo, fontsize=13, fontweight='bold', pad=15)
    ax.axis('equal')

    # Legenda lateral em vez de labels ao redor da pizza - elimina
    # colisão de texto independente do tamanho das fatias
    ax.legend(
        wedges,
        labels_filtrados,
        loc='center left',
        bbox_to_anchor=(1, 0.5),
        fontsize=9,
        frameon=False
    )

    plt.tight_layout()
    plt.savefig(caminho, transparent=True, bbox_inches='tight')
    plt.close(fig)

    return caminho


def gerar_grafico_barras(labels, valores, titulo, nome_arquivo, output_dir='charts_tmp', cor='#0056b3'):
    """
    Gera um gráfico de barras (ex: chamados por técnico, por status) e salva como PNG.
    """
    os.makedirs(output_dir, exist_ok=True)
    caminho = os.path.join(output_dir, nome_arquivo)

    fig, ax = plt.subplots(figsize=(7, 4), dpi=120)
    ax.bar(labels, valores, color=cor)
    ax.set_title(titulo, fontsize=13, fontweight='bold', pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.xticks(rotation=30, ha='right', fontsize=9)

    plt.tight_layout()
    plt.savefig(caminho, transparent=True, bbox_inches='tight')
    plt.close(fig)

    return caminho


def limpar_graficos_temporarios(output_dir='charts_tmp'):
    """
    Remove os PNGs temporários depois do envio do e-mail (chamar no final do main.py).
    """
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            os.remove(os.path.join(output_dir, f))
        os.rmdir(output_dir)