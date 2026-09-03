# Como adicionar um novo relatório

Guia fim a fim para quem for adicionar um relatório novo à automação.
Existem dois formatos possíveis — escolha o que se encaixa:

- **Normal**: uma execução, um Excel, um e-mail. Use quando o relatório
  não é segmentado por grupo (ex: um consolidado único para a diretoria).
- **Por grupo** (`"tipo": "por_grupo"`): as mesmas queries rodam uma vez
  para cada grupo em `"grupos"` (com `:grupo` injetado automaticamente),
  gerando um Excel e um e-mail **separado por grupo**. Use quando o
  relatório deve ir para os grupos cadastrados em `config/groups.py`
  (hoje: Suporte Técnico - 1º Nível, Suporte Técnico - 2º Nível,
  Administração de Sistemas, Redes e Telecomunicações, Desenvolvimento
  e Aplicações), cada um só com seus próprios dados.

Vamos usar como exemplo um relatório fictício **por grupo**: "Atendimento
Quinzenal", com um dataset simples e um gráfico. No fim, uma nota mostra
o que muda para o formato normal.

## 1. Escreva a(s) query(s) SQL

Cada dataset do relatório vira um arquivo `.sql` próprio em
`sql/<periodo>/<nome>.sql`. Não escreva SQL direto em
`config/reports.py` — ele só referencia o caminho do arquivo.

Para um relatório `por_grupo`, a query **precisa** filtrar por
`WHERE grupo = :grupo` — `services/reporter_runner.py` injeta esse
parâmetro automaticamente em cada execução, um valor de `"grupos"` por vez.

```
sql/quinzenal/resumo_quinzenal.sql
```

```sql
-- quinzenal/resumo_quinzenal
SELECT tecnico, COUNT(*) AS total_chamados
FROM vw_dashboard_tecnicos
WHERE grupo = :grupo
  AND data_criacao BETWEEN :inicio AND :fim_exclusivo
GROUP BY tecnico
ORDER BY total_chamados DESC;
```

Pontos importantes:
- Use os parâmetros nomeados `:inicio`, `:fim`, `:fim_exclusivo`, `:ano`,
  `:mes` quando o relatório tiver período (ver `services/periodos.py`).
  Prefira `:fim_exclusivo` em vez de `BETWEEN :inicio AND :fim` — o
  primeiro evita cortar o último dia do período por um problema de
  granularidade de `DATETIME` vs `DATE` que já mordeu esse projeto antes.
- **Teste a query isoladamente** contra o banco antes de conectar no
  pipeline: `mysql -u ... -e "$(cat sql/quinzenal/resumo_quinzenal.sql)"`
  com valores fixos no lugar dos `:parametros`.
- Depois de adicionar, rode `python3 scripts/verificar_schema.py` para
  confirmar que a query passa no `EXPLAIN` (pega erro de digitação de
  nome de coluna/view antes de ir pra produção).

## 2. Crie o template HTML

Copie o `.html` mais parecido em `templates/` como ponto de partida —
para um relatório `por_grupo`, `templates/relatorio_semanal_grupo.html`
é o exemplo mais próximo.

Regra de ouro de todo template: **envolva cada tabela em
`{% if tabelas.<nome_dataset> %} ... {% else %}<p class="empty-msg">Nenhum
dado disponível.</p>{% endif %}`** — é o que faz o relatório não quebrar
(nem ficar com uma tabela HTML vazia estranha) quando o período não tem
nenhum chamado.

Use `python3 preview_template.py` (ver README) para renderizar o HTML
localmente com dados fake antes de rodar o pipeline de verdade.

## 3. Registre o relatório em `config/reports.py`

Adicione uma entrada no dict `REPORTS`:

```python
"atendimento_quinzenal_grupo": {
    "tipo": "por_grupo",
    "tipo_relatorio": "quinzenal",  # precisa existir em config/groups.py, ver passo 5
    "grupos": ["Suporte Técnico - 1º Nível", "Administração de Sistemas"],
    "queries": {
        "resumo_quinzenal": _sql("quinzenal/resumo_quinzenal.sql"),
    },
    "datasets_por_grupo": ["resumo_quinzenal"],
    "template": "relatorio_quinzenal_grupo.html",
    "assunto": "Atendimento Quinzenal - {{ grupo }}",
    "titulo": "Atendimento Quinzenal - {{ grupo }}",
    "nome_arquivo_excel": "Atendimento_Quinzenal_Grupo.xlsx",
    "periodo": "semana_anterior",  # ou crie um novo período em services/periodos.py
    "tabelas": ["resumo_quinzenal"],
    "graficos": [
        {
            "dataset": "resumo_quinzenal",
            "tipo": "barras",
            "cid": "grafico_quinzenal",
            "titulo": "Chamados por Técnico",
            "coluna_label": "tecnico",
            "coluna_valor": "total_chamados",
        },
    ],
},
```

Campos:
- `tipo`: `"por_grupo"` para o padrão descrito acima; omitido (ou
  qualquer outro valor) para um relatório normal de execução única.
- `tipo_relatorio`: só para `por_grupo` — a chave usada em
  `config/groups.py::GRUPOS[x]["destinatarios"]` para achar a variável
  de destinatário de cada grupo (ver passo 5). Hoje existem `mensal`,
  `semanal`, `anual`, `criticos`.
- `grupos`: só para `por_grupo` — lista dos nomes de grupo exatamente
  como aparecem em `config/groups.py::GRUPOS[x]["nome"]` (maiúsculo).
- `queries`: nome do dataset → conteúdo SQL (via `_sql(...)`). Um relatório
  pode ter vários datasets.
- `template`: arquivo em `templates/`. Em `"{{ grupo }}"` dentro de
  `assunto`/`titulo`, o texto é substituído pelo nome do grupo em tempo
  de envio (só em relatórios `por_grupo`).
- `destinatarios_env` (só relatório **normal**): precisa bater com uma
  variável definida em `config/settings.py` (ex: `DESTINATARIOS_DIRETORIA`).
  Se for um destinatário novo, crie a variável lá **e** no
  `.env`/`.env.example` primeiro.
- `periodo`: nome resolvido por `services/periodos.py::resolver_periodo()`.
  Períodos hoje disponíveis: `"mes_anterior"`, `"semana_anterior"`,
  `"ano_anterior"`; qualquer outro valor (ex: `"hoje"`, usado pelos
  relatórios de críticos) não aplica filtro de data — a query resolve
  o período sozinha (ex: `dias_em_aberto >= 7`). Um período novo baseado
  em data (ex: "quinzena_anterior") precisa de uma função nova em
  `services/periodos.py` — **e um teste correspondente em
  `tests/test_periodos.py`** cobrindo pelo menos a virada de mês/ano.
- `tabelas`: quais datasets viram `{{ tabelas.<nome> }}` no template
  (HTML já formatado via `services/report_renderer.py`).
- `kpis` (opcional): números soltos extraídos de uma célula específica de
  um dataset, ex: `{"total_ativos_kpi": ("situacao_atual", "total_ativos")}`.
- `graficos` (opcional): um gráfico por entrada, gerado por
  `services/charts.py`.

## 4. Crie o unit + timer systemd

Copie o par `.service`/`.timer` mais parecido em `systemd/` (ex:
`automacao-glpi-semanal@`) e ajuste o `OnCalendar=` do timer para a nova
frequência. Lembre de manter o `OnFailure=automacao-glpi-alerta@%n.service`.

```bash
sudo cp systemd/automacao-glpi-semanal@.service systemd/automacao-glpi-quinzenal@.service
sudo cp systemd/automacao-glpi-semanal@.timer systemd/automacao-glpi-quinzenal@.timer
# editar OnCalendar= no .timer e a Description=
sudo systemctl daemon-reload
sudo systemctl enable --now automacao-glpi-quinzenal@atendimento_quinzenal_grupo.timer
```

Um relatório `por_grupo` precisa de **uma única instância de timer**
mesmo cobrindo vários grupos — o e-mail separado por grupo acontece
dentro da mesma execução, não precisa de uma instância por grupo.

## 5. Se for um grupo/tipo de relatório novo

**Grupo novo** (ex: um sexto grupo além dos cinco já cadastrados em
`config/groups.py`):
1. Adicione uma entrada em `config/groups.py::GRUPOS`, com `"nome"`
   (deve bater exatamente com o valor usado em `"grupos"` no
   `config/reports.py`, maiúsculo) e um `"destinatarios"` mapeando cada
   `tipo_relatorio` para o nome de uma variável de ambiente.
2. Crie essas variáveis em `.env.example` (documentadas, comentadas por
   padrão) e no `.env` real de produção, se quiser diferenciar do
   `DESTINATARIOS_*` geral daquele grupo.

**Tipo de relatório novo** (ex: `"quinzenal"`, como no exemplo acima):
1. Adicione a chave `"quinzenal"` no `"destinatarios"` de cada grupo em
   `config/groups.py` (ex: `"quinzenal": "GRUPO_ADMSIS_QUINZENAL"`).
2. Documente as novas variáveis `GRUPO_*_QUINZENAL` em `.env.example`.
   Se não forem preenchidas no `.env`, `config/settings.py` cai
   automaticamente no `DESTINATARIOS_*` geral da área — não é obrigatório
   preencher todas.

## 6. Teste antes de ir pra produção

```bash
# 1. Query passa no schema atual?
python3 scripts/verificar_schema.py --sql-dir sql/quinzenal

# 2. Pipeline completo roda sem erro, sem mandar e-mail de verdade?
#    (gera Excel/gráficos por grupo, loga quem receberia e o quê)
python3 main.py --report atendimento_quinzenal_grupo --dry-run

# 3. (se mudou algo em services/periodos.py) testes passam?
pytest tests/ -v

# 4. Lint
ruff check .
```

Só depois disso, tirar o `--dry-run` e rodar de verdade (ou deixar o
`.timer` disparar sozinho).

## Nota: relatório normal (não por grupo)

Para um relatório de execução única (sem segmentar por grupo), a
diferença principal em `config/reports.py` é:

```python
"meu_relatorio_normal": {
    # sem "tipo": "por_grupo", sem "grupos", sem "tipo_relatorio"
    "queries": {
        "meu_dataset": _sql("meu_periodo/meu_dataset.sql"),
    },
    "template": "meu_template.html",
    "assunto": "Assunto do e-mail",       # texto fixo, sem "{{ grupo }}"
    "titulo": "Título exibido no relatório",
    "destinatarios_env": "DESTINATARIOS_DIRETORIA",  # variável direta, não por grupo
    "nome_arquivo_excel": "Meu_Relatorio.xlsx",
    "periodo": "mes_anterior",
    "tabelas": ["meu_dataset"],
},
```

Veja `relatorio_mensal_diretores` em `config/reports.py` como exemplo
real desse formato — nesse caso, a segmentação por grupo acontece dentro
da própria query SQL (`GROUP BY grupo`), não no Python.
