# Dashboard Zabbix — automacaoGLPI

Guia passo a passo para montar um dashboard visual em cima dos 23 itens
e 18 triggers já criados no host `AUTOMACAO-GLPI-PROD` (ver
`zabbix/README.md` para a lista completa e como recriá-los em outro
host). Testado em Zabbix 7.0.

## 0. Antes de começar

Confirme que os itens já estão coletando dado — sem isso, os widgets
aparecem vazios/"No data" e fica difícil saber se o problema é o
dashboard ou a coleta:

`Data collection` → `Hosts` → `AUTOMACAO-GLPI-PROD` → `Latest data` →
filtrar por `automacaoglpi` no campo "Name". Itens `unit.state` e
`unit.result` devem ter valor (`inactive`/`success` etc.) já na primeira
checagem (delay 5m); `report.duracao` só popula depois da primeira
execução bem-sucedida de cada relatório; `unit.last_run` só popula
depois da primeira execução de cada unit (fica vazio até lá — normal).

Os 23 itens também já têm uma tag `dash` (valores: `estado`, `resultado`,
`last_run`, `duracao`, `trapper`, `conectividade`, um por item, conforme
o que ele mede) — os widgets `Data overview` abaixo filtram por essa tag,
não por nome do item (o widget não suporta padrão de nome livre nesta
versão do Zabbix).

## 1. Criar o dashboard

`Dashboards` → `All dashboards` → `Create dashboard`:

- **Owner**: seu usuário (ou um usuário de serviço compartilhado, se
  outras pessoas do time forem editar depois).
- **Name**: `automacaoGLPI — Monitoramento`.
- **Default page name**: `Visão geral`.
- Deixe "Display period"/"Start slideshow" como padrão.

Depois de salvar, clique em **Edit dashboard** para começar a adicionar
widgets (o dashboard entra em modo de edição com um grid de 12
colunas — os tamanhos abaixo são "largura x altura" nesse grid).

## 2. Layout sugerido

```
┌─────────────────────────────────────────────────────────────────┐
│  [1] Problems — alertas ativos                    (12 x 5)      │
├───────────────────────────────┬───────────────────────────────┤
│  [2] Estado por unit (12x3)   │  [3] Resultado por unit (12x3)  │
├───────────────────────────────┴───────────────────────────────┤
│  [4] Duração das execuções — gráfico combinado     (12 x 6)      │
├───────────────────────┬───────────────────────┬─────────────────┤
│ [5] SMTP  (4x3)        │ [6] MariaDB (4x3)      │ [7] Últ. exec.  │
│                        │                        │     (4x3)       │
└───────────────────────┴───────────────────────┴─────────────────┘
```

## 3. Widget por widget

### [1] Problems — alertas ativos (topo, largura total)

O mais importante do dashboard: mostra qualquer trigger em estado de
problema, os 18 criados incluem falha reportada, unit não rodou, unit
em failed, duração alta e SMTP/MariaDB fora do ar.

- **Type**: `Problems`
- **Name**: `Alertas ativos — automacaoGLPI`
- **Host groups**: deixe vazio, ou o grupo do host
- **Hosts**: `AUTOMACAO-GLPI-PROD`
- **Show**: `Recent problems` (mostra também os que acabaram de
  resolver, útil pra ver histórico recente sem trocar de tela)
- **Sort entries by**: `Severity`
- **Show tags**: `None` (não usamos tags customizadas)
- **Show timeline**: ativado
- Tamanho: 12 largura x 5 altura.

### [2] Estado por unit (esquerda)

- **Type**: `Data overview`
- **Name**: `Estado das units`
- **Host groups**: deixe vazio
- **Hosts**: `AUTOMACAO-GLPI-PROD`
- **Item tags**: `dash` `Equals` `estado`
- **Hosts location**: `Left`
- Tamanho: 6 largura x 3 altura.

### [3] Resultado por unit (direita)

Igual ao [2], trocando:
- **Name**: `Resultado da última execução`
- **Item tags**: `dash` `Equals` `resultado`
- Tamanho: 6 largura x 3 altura.

Esses dois widgets juntos dão a visão "estado atual x resultado do
último disparo" de cada um dos 5 relatórios/units, lado a lado.

### [4] Duração das execuções — gráfico combinado

- **Type**: `Graph` (o widget de gráfico novo, com múltiplos "Data
  set", não o "Graph (classic)")
- **Name**: `Duração das execuções (segundos)`
- Adicionar **5 Data sets**, um por relatório, cada um:
  - **Host pattern**: `AUTOMACAO-GLPI-PROD`
  - **Item pattern**: `Duração da última execução bem-sucedida
    [<nome_relatorio>]` (os 5 nomes: `atendimento_criticos_grupo`,
    `atendimento_semanal_grupo`, `atendimento_mensal_grupo`,
    `relatorio_mensal_diretores`, `atendimento_anual_grupo`)
  - **Draw**: `Line`
- **Time period**: `Last 30 days` (ajuste depois que tiver mais
  histórico — para o relatório anual, 30 dias nunca vai mostrar nada
  além do ponto mais recente, o que é esperado)
- Tamanho: 12 largura x 6 altura.

Se o campo "Item pattern" do Data set não aparecer nessa versão (o
"Data overview" surpreendeu nesse ponto — filtra por tag, não por
nome), use `Item tags: dash Equals duracao` em vez de "Item pattern"; os
5 itens de duração já têm essa tag.

Se preferir 5 gráficos pequenos e separados em vez de um combinado
(mais fácil de ler quando as escalas de duração são muito diferentes
entre críticos e mensal, por exemplo), repita esse widget uma vez por
relatório com um único Data set cada, tamanho 4x4 ou 3x4.

### [5] Conectividade SMTP

- **Type**: `Item value`
- **Name**: `SMTP`
- **Item**: `AUTOMACAO-GLPI-PROD` → `Conectividade SMTP
  (webmail.exemplo.gov.br:587)`
- **Description**: deixe o padrão (nome do item)
- Em **Value**: ativar `Show: Value`, e em **Thresholds** adicionar:
  - `0` → cor vermelha (indisponível)
  - `1` → cor verde (disponível)

Isso transforma o número cru (`net.tcp.service` retorna 0 ou 1) numa
cor, sem precisar decorar o significado.

### [6] Conectividade MariaDB

Igual ao [5], trocando:
- **Name**: `MariaDB GLPI`
- **Item**: `Conectividade MariaDB GLPI (10.0.0.30:3306)` (nome e chave
  do item foram ajustados de `127.0.0.1` para o IP real — ver
  `zabbix/README.md`, seção de itens fixos, para o motivo)
- Mesmos thresholds (0=vermelho, 1=verde).

### [7] Última execução de cada unit (timestamp)

- **Type**: `Data overview`
- **Name**: `Timestamp da última execução`
- **Hosts**: `AUTOMACAO-GLPI-PROD`
- **Item tags**: `dash` `Equals` `last_run`
- Tamanho: 4 largura x 3 altura.

Esse widget mostra o valor cru em epoch (ex: `1755612000`), não uma
data legível — o "Data overview" não formata automaticamente. Serve
mais para debug manual (`date -d @1755612000`) do que leitura direta;
quem acompanha o dashboard no dia a dia deve confiar no widget [1]
(Problems) para saber se algum relatório está atrasado — é exatamente
pra isso que o trigger de `fuzzytime` existe.

## 4. Testar o dashboard

Depois de montado, force um valor de teste no item trapper pra ver o
widget [1] reagir sem esperar uma falha real:

```bash
cd /opt/automacaoGLPI
venv/bin/python3 scripts/alerta_falha.py "teste-dashboard"
```

Isso deve: (a) aparecer como novo problema no widget `Problems` em
poucos segundos (o trigger usa `nodata(...,10m)=0`, então o problema
fica ativo por até 10 minutos e depois resolve sozinho); (b) chegar
e-mail de alerta; (c) o `alerta_falha.py` imprimir `1 processado(s), 0
falha(s)` no trap.

Depois, force um ciclo completo de um relatório pra ver os widgets [2],
[3], [4] e [7] populando com dado de verdade:

```bash
venv/bin/python3 main.py --report atendimento_semanal_grupo
```

## 5. Alternativa: montar via API

Se preferir não clicar em tudo isso manualmente, dá para criar o
dashboard inteiro via `dashboard.create` da API do Zabbix (mesmo
mecanismo usado para criar os 23 itens/18 triggers — ver histórico de
commits deste projeto para o script usado). Avise se quiser que isso
seja montado assim em vez de manual — é mais rápido e reprodutível para
recriar em produção depois, mas exige um token de API com permissão de
escrita, como da vez anterior.
