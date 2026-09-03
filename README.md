# Automação de relatórios do GLPI

Automação de relatórios do GLPI: extrai dados de views MariaDB, gera planilhas Excel e envia relatórios por e-mail (HTML + gráficos embutidos), com agendamento independente por relatório via systemd timer.

## Objetivo

Para atender às demandas da diretoria referente aos chamados do GLPI — com coleta de métricas mensais, semanais, anuais e de chamados críticos — foi desenvolvida uma aplicação para envio de relatórios automatizados.

Cobre hoje cinco grupos — **Suporte Técnico - 1º Nível**, **Suporte Técnico - 2º Nível**, **Administração de Sistemas**, **Redes e Telecomunicações** e **Desenvolvimento e Aplicações** —, podendo evoluir para outros grupos conforme necessidade (ver `config/groups.py`).

Os relatórios são disparados por e-mail para os técnicos/coordenadores de cada grupo e, no caso do consolidado mensal, para a diretoria.

## Capturas de tela

Prints dos e-mails gerados pelo pipeline (dados fictícios, gerados via `preview_template.py`). Clique em cada um para expandir:

<details>
<summary><strong>Consolidado mensal (diretoria)</strong></summary>
<br>
<img src="docs/images/relatorio_diretoria_mensal.png" width="480">
</details>

<details>
<summary><strong>Atendimento mensal por grupo</strong></summary>
<br>
<img src="docs/images/relatorio_mensal_grupo.png" width="480">
</details>

<details>
<summary><strong>Atendimento semanal por grupo</strong></summary>
<br>
<img src="docs/images/relatorio_semanal_grupo.png" width="480">
</details>

<details>
<summary><strong>Chamados críticos por grupo</strong></summary>
<br>
<img src="docs/images/relatorio_criticos_grupo.png" width="480">
</details>

<details>
<summary><strong>Atendimento anual por grupo</strong></summary>
<br>
<img src="docs/images/relatorio_anual_grupo.png" width="480">
</details>

## Ambiente de produção

| Item | Valor |
|---|---|
| Servidor da aplicação | Linux (Debian), acesso de rede ao MariaDB do GLPI na porta 3306 |
| Caminho da aplicação | `/opt/automacaoGLPI` |
| Servidor de banco de dados (MariaDB) | instância do GLPI (ver `DB_HOST` no `.env`) |
| Usuário de execução (systemd) | `automacaoglpi` |
| Unidades systemd | `systemd/automacao-glpi-{critico,semanal,mensal,anual}@.service` e `.timer` (unit template, uma instância por relatório) |

## Como funciona (visão geral)

```
main.py --report <nome>
   │
   ├─► config/reports.py            → busca a configuração do relatório (queries, template, destinatários...)
   ├─► services/reporter_runner.py  → orquestra as etapas abaixo, na ordem
   │      ├─► services/periodos.py       → calcula data de início/fim (semanal/mensal/anual)
   │      ├─► services/database.py       → executa as queries no MariaDB e retorna DataFrames (pandas)
   │      ├─► services/excel_service.py  → gera o .xlsx (uma aba por dataset)
   │      ├─► services/charts.py         → gera os gráficos (pizza/barras) como PNG
   │      ├─► services/report_renderer.py→ monta tabelas HTML e extrai KPIs para o template
   │      └─► services/mailer.py         → conecta no SMTP e envia
   │              ├─► services/renderer.py      → renderiza o Jinja + aplica CSS inline (premailer)
   │              └─► services/email_builder.py → monta o MIME (corpo, imagens inline, anexo)
   └─► services/logger.py           → logging centralizado (console + arquivo com rotação), usado em todas as etapas
```

Cada relatório é uma **entrada independente** no dicionário `REPORTS` (`config/reports.py`). Existem dois formatos de entrada:

- **Normal**: uma execução, um Excel, um e-mail (ex: o consolidado da diretoria).
- **Por grupo** (`"tipo": "por_grupo"`): as mesmas queries rodam uma vez para cada grupo em `"grupos"` (injetando `:grupo` automaticamente), gerando um Excel e um e-mail **separado por grupo** — cada grupo só recebe seus próprios dados. Os destinatários de cada grupo são resolvidos por `services/reporter_runner.py::obter_destinatarios_por_grupo()`, usando o mapeamento em `config/groups.py` (ver seção "Destinatários por grupo" abaixo).

As queries SQL de cada relatório não ficam escritas dentro do Python — cada uma é um arquivo `.sql` próprio em `sql/`, referenciado pelo caminho.

## Estrutura do projeto

```
automacaoGLPI/
├── main.py                      # ponto de entrada, aceita --report <nome>; só orquestra
├── preview_template.py          # FERRAMENTA DE DEV: renderiza um template com dados fictícios no navegador
├── requirements.txt
├── .env                         # credenciais (NÃO versionado)
│
├── config/
│   ├── settings.py              # carrega e valida variáveis do .env
│   ├── groups.py                # grupos GLPI + mapeamento grupo/tipo de relatório -> variável de destinatário
│   └── reports.py               # registro central: um relatório = uma entrada aqui (SQL fica em sql/)
│
├── sql/
│   ├── mensal/                  # datasets usados por "atendimento_mensal_grupo" — parametrizados com :grupo
│   ├── semanal/                 # idem, "atendimento_semanal_grupo"
│   ├── anual/                   # idem, "atendimento_anual_grupo"
│   ├── criticos/                # idem, "atendimento_criticos_grupo" (sem filtro de período)
│   └── diretoria/mensal/        # datasets do consolidado da diretoria (todos os grupos numa query só)
│       # cada arquivo .sql corresponde a 1 dataset de 1 relatório,
│       # ex: sql/mensal/por_tecnico.sql
│
├── services/
│   ├── database.py              # conexão SQLAlchemy (mysql-connector) + execução de queries
│   ├── reporter_runner.py       # orquestra a execução de um relatório (normal ou por grupo) do início ao fim
│   ├── report_renderer.py       # tabelas HTML, KPIs, formatação de horas ("Xh Ymin") e percentuais
│   ├── excel_service.py         # geração dos arquivos .xlsx (multi-aba)
│   ├── charts.py                # geração de gráficos (pizza, barras) como PNG
│   ├── renderer.py              # Jinja + CSS inline (premailer) — só transforma template em HTML
│   ├── email_builder.py         # monta o MIME (corpo, imagens inline via CID, anexo)
│   ├── mailer.py                # só SMTP: conectar e enviar a mensagem já pronta
│   ├── periodos.py              # cálculo de "semana anterior" / "mês anterior" / "ano anterior"
│   └── logger.py                # logging centralizado (console + arquivo com rotação)
│
├── templates/
│   ├── base_email.html          # layout comum (header, footer, injeta o CSS)
│   ├── relatorio_mensal_grupo.html    # usado por atendimento_mensal_grupo
│   ├── relatorio_semanal_grupo.html   # usado por atendimento_semanal_grupo
│   ├── relatorio_anual_grupo.html     # usado por atendimento_anual_grupo
│   ├── relatorio_criticos_grupo.html  # usado por atendimento_criticos_grupo
│   ├── relatorio_diretoria_mensal.html# usado por relatorio_mensal_diretores
│   └── css/email_styles.css     # estilos do e-mail (injetado no <style> do base_email)
│
├── logs/                        # gerado automaticamente por services/logger.py (não versionado)
│                                 # em produção: /opt/automacaoGLPI/logs/execucao.log
│
├── scripts/
│   ├── health_check.py              # confere .env, banco, SMTP, disco e diretório de logs
│   ├── verificar_schema.py          # roda EXPLAIN em todo .sql de sql/ contra o banco configurado
│   ├── duracao_ultima_execucao.py   # lê logs/execucao.log, usado pelo item Zabbix de duração
│   └── alerta_falha.py              # disparado via OnFailure= do systemd em caso de falha
│
└── systemd/
    ├── automacao-glpi-critico@.service / .timer   # segunda e quinta às 08:00
    ├── automacao-glpi-semanal@.service / .timer   # toda segunda às 08:00
    ├── automacao-glpi-mensal@.service / .timer    # dia 1º do mês às 08:00
    ├── automacao-glpi-anual@.service / .timer     # 1º de janeiro às 08:00
    ├── automacao-glpi@.service / .timer           # template genérico (base p/ agendamento customizado via drop-in)
    └── automacao-glpi-alerta@.service             # disparado via OnFailure= dos serviços acima
```

## Pré-requisitos

- Python 3.11+
- Acesso de rede do servidor da aplicação ao servidor MariaDB do GLPI, porta 3306
- Conta de e-mail para envio via SMTP (Gmail exige **senha de app**, não a senha normal, se a conta tiver verificação em duas etapas)

## Instalação

```bash
cd /opt
git clone <url-do-repositorio> automacaoGLPI
cd automacaoGLPI

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

Ajuste o dono dos arquivos para o usuário técnico que vai rodar via systemd:

```bash
sudo chown -R automacaoglpi:automacaoglpi /opt/automacaoGLPI
```

## Configuração (`.env`)

Crie o arquivo `.env` na raiz do projeto (`/opt/automacaoGLPI/.env`) e restrinja a permissão:

```bash
touch /opt/automacaoGLPI/.env
chmod 600 /opt/automacaoGLPI/.env
chown automacaoglpi:automacaoglpi /opt/automacaoGLPI/.env
```

Variáveis obrigatórias (validadas em `config/settings.py` — o script encerra com mensagem clara se faltar alguma):

| Variável | Descrição |
|---|---|
| `DB_HOST` | Endereço do servidor MariaDB do GLPI |
| `DB_PORT` | Porta (padrão 3306) |
| `DB_NAME` | Nome do banco |
| `DB_USER` / `DB_PASS` | Credenciais do banco |
| `SMTP_HOST` / `SMTP_PORT` | Servidor de envio de e-mail |
| `SMTP_USER` / `SMTP_PASS` | Credenciais do SMTP (senha de app, se Gmail com 2FA) |
| `SMTP_FROM` | Remetente exibido no e-mail |

Variáveis de destinatários gerais por grupo (opcionais individualmente, mas recomenda-se preencher todas — se vazias, apenas um aviso é logado e o e-mail daquele grupo/relatório é pulado):

| Variável | Usada por... |
|---|---|
| `DESTINATARIOS_SUPORTE_N1` | Todos os tipos de relatório do grupo Suporte Técnico - 1º Nível, exceto onde houver override (ver abaixo) |
| `DESTINATARIOS_SUPORTE_N2` | Idem, Suporte Técnico - 2º Nível |
| `DESTINATARIOS_ADMSIS` | Idem, Administração de Sistemas |
| `DESTINATARIOS_REDES` | Idem, Redes e Telecomunicações |
| `DESTINATARIOS_DEV` | Idem, Desenvolvimento e Aplicações |
| `DESTINATARIOS_DIRETORIA` | `relatorio_mensal_diretores` (consolidado) |

### Destinatários por grupo (override opcional por tipo de relatório)

Os relatórios `"tipo": "por_grupo"` (`atendimento_mensal_grupo`, `atendimento_semanal_grupo`, `atendimento_anual_grupo`, `atendimento_criticos_grupo`) resolvem o destinatário de cada grupo através de `config/groups.py`, que mapeia grupo + tipo de relatório para uma variável específica:

| Variável | Grupo | Tipo de relatório |
|---|---|---|
| `GRUPO_SUPORTE_N1_MENSAL` / `_SEMANAL` / `_ANUAL` / `_CRITICOS` | Suporte Técnico - 1º Nível | mensal / semanal / anual / críticos |
| `GRUPO_SUPORTE_N2_MENSAL` / `_SEMANAL` / `_ANUAL` / `_CRITICOS` | Suporte Técnico - 2º Nível | idem |
| `GRUPO_ADMSIS_MENSAL` / `_SEMANAL` / `_ANUAL` / `_CRITICOS` | Administração de Sistemas | idem |
| `GRUPO_REDES_MENSAL` / `_SEMANAL` / `_ANUAL` / `_CRITICOS` | Redes e Telecomunicações | idem |
| `GRUPO_DEV_MENSAL` / `_SEMANAL` / `_ANUAL` / `_CRITICOS` | Desenvolvimento e Aplicações | idem |

Essas 20 variáveis são **opcionais**: se uma delas não estiver definida (ou estiver vazia) no `.env`, `config/settings.py` cai automaticamente no `DESTINATARIOS_*` geral daquele grupo. Só preencha uma `GRUPO_*` específica se aquele tipo de relatório daquele grupo precisar ir para uma lista diferente da geral (ex: críticos indo para o plantão, e mensal/semanal indo para o coordenador). Ver exemplo comentado em `.env.example`.

Todos os campos de destinatários aceitam múltiplos e-mails separados por vírgula.

Exemplo de `.env` mínimo (só com as variáveis gerais, sem overrides por tipo):

```env
DB_HOST=10.0.0.20
DB_PORT=3306
DB_NAME=glpi
DB_USER=usuario_relatorios
DB_PASS=troque-esta-senha

SMTP_HOST=smtp.exemplo.com.br
SMTP_PORT=587
SMTP_USER=relatorios@exemplo.com.br
SMTP_PASS=troque-esta-senha
SMTP_FROM=relatorios@exemplo.com.br

DESTINATARIOS_SUPORTE_N1=n1-a@exemplo.com.br,n1-b@exemplo.com.br
DESTINATARIOS_SUPORTE_N2=n2@exemplo.com.br
DESTINATARIOS_ADMSIS=admsis@exemplo.com.br
DESTINATARIOS_REDES=redes@exemplo.com.br
DESTINATARIOS_DEV=dev@exemplo.com.br
DESTINATARIOS_DIRETORIA=diretoria@exemplo.com.br
```

**O `.env` nunca deve ser commitado.** Se um `.env` acabar indo parar no histórico do Git em algum momento, as credenciais nele devem ser consideradas expostas e rotacionadas — reescrever o histórico depois não é suficiente sozinho.

## Uso manual

```bash
cd /opt/automacaoGLPI
source venv/bin/activate
python3 main.py --report atendimento_criticos_grupo

# Testar sem enviar e-mail de verdade (roda queries, Excel, gráficos,
# renderização — só não conecta no SMTP nem envia nada):
python3 main.py --report atendimento_criticos_grupo --dry-run

# Ver a versão do pipeline em execução (útil pra correlacionar com o log):
python3 main.py --version
```

### Relatórios disponíveis

Lista sempre atualizada em `config/reports.py`, chave do dicionário `REPORTS`:

| Relatório | Tipo | Grupos cobertos | Periodicidade |
|---|---|---|---|
| `atendimento_criticos_grupo` | por_grupo | os 5 grupos de `config/groups.py` | diária/sob demanda (chamados com 7+ dias em aberto) |
| `atendimento_semanal_grupo` | por_grupo | idem | semanal |
| `atendimento_mensal_grupo` | por_grupo | idem | mensal |
| `atendimento_anual_grupo` | por_grupo | idem | anual |
| `relatorio_mensal_diretores` | normal | consolidado (todos os grupos numa query só) | mensal |

Um relatório `por_grupo` gera **um e-mail por grupo** (3 e-mails, no caso acima) na mesma execução — não é preciso uma entrada em `REPORTS` por grupo.

## Adicionando um novo relatório

Não é necessário tocar no `main.py` nem no `services/reporter_runner.py`. Resumo rápido — para o passo a passo completo com exemplo, ver **[`docs/adicionar-relatorio.md`](docs/adicionar-relatorio.md)**:

1. Criar o(s) arquivo(s) `.sql` do relatório em `sql/<periodo>/`, um por dataset. Se o relatório for `por_grupo`, a query deve filtrar por `WHERE grupo = :grupo` (injetado automaticamente).
2. Criar o template HTML em `templates/`, com `{% extends "base_email.html" %}` e um bloco `{% block conteudo %}`.
3. Adicionar uma entrada em `config/reports.py` — normal (um `destinatarios_env`) ou por grupo (`"tipo": "por_grupo"`, `"tipo_relatorio"`, `"grupos"`; destinatário resolvido via `config/groups.py`, ver seção acima).
4. Se o dataset precisar de filtro de data, use `:inicio`, `:fim`, `:fim_exclusivo`, `:ano` ou `:mes` na query — `services/periodos.py` calcula os valores automaticamente com base no campo `"periodo"`.
5. Criar a instância do timer/service correspondente (ver seção abaixo) e habilitá-la.
6. Antes de habilitar em produção: `python3 scripts/verificar_schema.py --sql-dir sql/<periodo>` (a query bate com o schema atual?) e `python3 main.py --report <nome> --dry-run` (o pipeline inteiro roda sem erro, sem enviar e-mail de verdade?).

## Agendamento via systemd (recomendado em produção)

A aplicação utiliza templates de unidade baseados em frequência (`critico`, `semanal`, `mensal`, `anual`). O próprio timer já injeta o agendamento correto (`OnCalendar`) sem a necessidade de criar arquivos manuais de drop-in, exceto para horários diferentes do padrão.

### 1. Instalar os templates

```bash
sudo cp systemd/automacao-glpi-*@.service /etc/systemd/system/
sudo cp systemd/automacao-glpi-*@.timer   /etc/systemd/system/
sudo cp systemd/automacao-glpi-alerta@.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 2. Habilitar uma instância por relatório

Cada relatório vira uma instância independente, no template correspondente ao seu período:

```bash
sudo systemctl enable --now automacao-glpi-critico@atendimento_criticos_grupo.timer
sudo systemctl enable --now automacao-glpi-semanal@atendimento_semanal_grupo.timer
sudo systemctl enable --now automacao-glpi-mensal@atendimento_mensal_grupo.timer
sudo systemctl enable --now automacao-glpi-mensal@relatorio_mensal_diretores.timer
sudo systemctl enable --now automacao-glpi-anual@atendimento_anual_grupo.timer
```

Cada relatório `por_grupo` acima dispara **um e-mail por grupo** na mesma execução (não precisa de uma instância por grupo).

### 3. Ajustar o horário de uma instância específica (drop-in override)

Se uma instância precisar de um horário diferente do padrão do template, use um **drop-in** para sobrescrever só o `OnCalendar` daquela instância:

```bash
sudo systemctl edit automacao-glpi-mensal@relatorio_mensal_diretores.timer
```

Isso abre um arquivo em `/etc/systemd/system/automacao-glpi-mensal@relatorio_mensal_diretores.timer.d/override.conf`. Exemplo de conteúdo — todo dia 2 do mês, às 07:00 (depois que os relatórios por grupo já rodaram):

```ini
[Timer]
OnCalendar=
OnCalendar=*-*-02 07:00:00
```

(A primeira linha `OnCalendar=` vazia limpa o valor herdado do template antes de definir o novo, senão os dois horários coexistem.)

Depois de criar/editar um drop-in:

```bash
sudo systemctl daemon-reload
sudo systemctl restart automacao-glpi-mensal@relatorio_mensal_diretores.timer
```

### 4. Verificar e depurar

```bash
# lista todos os timers de relatório ativos e o próximo disparo
systemctl list-timers 'automacao-glpi*'

# dispara manualmente uma execução (sem esperar o timer), útil para testar
sudo systemctl start automacao-glpi-semanal@atendimento_semanal_grupo.service
# acompanha o log de uma instância específica
journalctl -u automacao-glpi-semanal@atendimento_semanal_grupo.service -f
# log em arquivo (todas as instâncias escrevem no mesmo arquivo, pois é o mesmo processo)
tail -f /opt/automacaoGLPI/logs/execucao.log
```

## Ferramentas de desenvolvimento

`preview_template.py` renderiza qualquer template com dados fictícios e abre o resultado (`preview.html`) no navegador — útil para ajustar o layout de um e-mail sem rodar o pipeline completo (banco, Excel, SMTP) a cada teste. Não faz parte do fluxo de produção e não é chamado por `main.py`, cron nem systemd.

```bash
python3 preview_template.py
```

## Testes automatizados

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Cobertura hoje (44 testes): `services/periodos.py` (bordas de calendário: virada de mês/ano, ano bissexto, semana cruzando meses), `services/report_renderer.py` (formatação de horas/percentual, KPIs com dataset vazio ou ausente, comportamento de tabela HTML com DataFrame vazio) e `services/retry.py` (número de tentativas, backoff, quais exceções disparam retry — cobre indiretamente a lógica de retry usada por `services/database.py` e `services/mailer.py`). Ainda falta um teste de integração fim a fim usando um banco MariaDB de teste (ver "Ainda pendente" abaixo).

## Logs

Todas as execuções são registradas em `logs/execucao.log` (em produção: `/opt/automacaoGLPI/logs/execucao.log`), com timestamp e nível (INFO/WARNING/ERROR), com rotação automática (máximo 5 arquivos de 2 MB). Em caso de falha, o traceback completo é gravado no log. A pasta `logs/` não é versionada. Execuções via systemd também ficam disponíveis no `journalctl`, por instância (ver seção de agendamento acima). Formato controlado por `LOG_FORMAT` no `.env` (`text`, padrão, ou `json` — ver `services/logger.py`).

## Rotação de credenciais

`DB_PASS` e `SMTP_PASS` vivem só no `.env` (permissão `600`, fora do controle de versão). Não existe rotação automática — é responsabilidade manual de quem administra o servidor. Processo recomendado, na ordem:

1. Trocar a senha primeiro **na origem** (MariaDB/GLPI para `DB_PASS`; provedor de e-mail/Google Workspace para `SMTP_PASS` — lembrando que Gmail com 2FA exige gerar uma nova "senha de app", não a senha normal da conta).
2. Atualizar o `.env` em produção com o valor novo (`sudo -u automacaoglpi vim /opt/automacaoGLPI/.env` ou equivalente).
3. Validar sem esperar o próximo agendamento: `python3 main.py --report <qualquer_relatorio> --dry-run` — se a nova credencial estiver errada, isso falha rápido (na conexão) sem mandar e-mail nenhum.
4. Só depois de validar, revogar a credencial antiga na origem (se o provedor suportar múltiplas credenciais ativas simultaneamente) ou aceitar a janela de indisponibilidade entre os passos 1 e 2 (se não suportar).

Não há hoje um lembrete automático de expiração — se a política da organização exigir rotação periódica (ex: a cada 90 dias), isso precisa ser um lembrete externo (calendário, ticket recorrente), não algo que o próprio pipeline sabe verificar.

## Dependências externas críticas

A automação depende de três sistemas fora do seu controle. Comportamento esperado quando cada um falha:

| Dependência | Se cair... | Comportamento hoje |
|---|---|---|
| **MariaDB/GLPI** (leitura das views) | Sem dado nenhum pra nenhum relatório | `services/database.py` tenta reconectar 3x (2s, 4s de backoff) antes de desistir; se persistir, a exceção sobe, o systemd marca o serviço como falho e dispara `OnFailure=` → alerta por e-mail + Zabbix trapper (ver `zabbix/README.md`). Nenhum relatório é enviado incompleto/corrompido — ou funciona, ou falha visivelmente. |
| **Servidor SMTP corporativo** (envio) | Excel/gráficos são gerados normalmente, mas o e-mail não sai | Mesmo retry de 3x (2s, 4s) na conexão SMTP (`services/mailer.py`). Falha na autenticação (senha errada/expirada) **não** entra no retry de propósito — não adianta tentar de novo. Falha também dispara o alerta de `OnFailure=`. O `.xlsx` gerado é removido mesmo em caso de falha de envio (não fica acumulando em disco). |
| **Zabbix** (monitoramento/alerta) | A automação continua funcionando normalmente — Zabbix é só observador, não dependência do pipeline em si | O envio do trapper em `scripts/alerta_falha.py` (pacote `zabbix-utils`) tem timeout curto; se falhar, é só logado, não derruba a execução do relatório. Efeito colateral: se Zabbix estiver fora do ar bem na hora de uma falha real de relatório, você perde a visibilidade daquela falha específica no Zabbix (mas ainda tem o alerta por e-mail, se o SMTP estiver de pé, e sempre tem o `journalctl`). |

Casos não cobertos hoje: se **tanto** o SMTP quanto o Zabbix caírem ao mesmo tempo que uma falha real acontece, a única forma de descobrir é olhar o `journalctl`/`logs/execucao.log` manualmente — não há um segundo canal de alerta independente desses dois.

## Status atual / pendências conhecidas

Concluído:

- [x] Consolidação dos relatórios em padrão `"tipo": "por_grupo"` — um relatório processa todos os grupos numa execução (queries + Excel + e-mail separados por grupo), em vez de uma entrada em `REPORTS` por grupo. Reduz de ~9 relatórios individuais para 5.
- [x] Relatório anual por grupo (`atendimento_anual_grupo`) — antes só existia mensal/semanal/críticos.
- [x] Destinatário por grupo **e** por tipo de relatório (`GRUPO_SUPORTE_N1_MENSAL`, `GRUPO_ADMSIS_ANUAL`, etc., com fallback pro `DESTINATARIOS_*` geral se não preenchido) — ver seção "Destinatários por grupo" acima.
- [x] Alerta por e-mail e Zabbix trapper em caso de falha na execução agendada — `OnFailure=automacao-glpi-alerta@%n.service` em todos os `.service` de relatório, disparando `scripts/alerta_falha.py`.
- [x] Monitorar tempo de execução de cada relatório — `scripts/duracao_ultima_execucao.py` + item Zabbix `automacaoglpi.report.duracao[*]` (ver `zabbix/README.md`).
- [x] `requirements.txt` com versões fixadas.
- [x] Mascaramento de credencial (`DB_PASS`) em mensagens de erro logadas por `services/database.py`.
- [x] Testes automatizados para `services/periodos.py`, `services/report_renderer.py` e `services/retry.py` (44 testes).
- [x] Validação de tipos/formato das variáveis do `.env` (`DB_PORT`/`SMTP_PORT` numéricos, `SMTP_FROM`/`DESTINATARIOS_*` com formato de e-mail plausível, teto de anexo consistente) em `validar_configuracoes()`.
- [x] Retry/backoff em falha transitória de conexão — `services/retry.py` aplicado à conexão com o MariaDB e ao handshake SMTP. Deliberadamente **não** aplicado a `server.sendmail()` (risco de duplicar e-mail em falha parcial) nem a erro de autenticação (não adianta tentar de novo).
- [x] Script pra confirmar que as queries de `sql/` continuam batendo com o schema do GLPI — `scripts/verificar_schema.py`, valida via `EXPLAIN` (sem ler dados de verdade).
- [x] Health check de pré-produção — `scripts/health_check.py` (confere `.env`, banco, SMTP, disco, diretório de logs).
- [x] Log estruturado em JSON — `LOG_FORMAT=json` no `.env`.
- [x] Lint/CI — `ruff.toml` + `.github/workflows/ci.yml` (lint + pytest a cada push/PR pra `main`/`develop`).

Ainda pendente:

- [ ] Testes automatizados: falta um teste de integração fim a fim automatizado contra um MariaDB de teste (a lógica de retry em si já é coberta por `tests/test_retry.py`, mas não há teste automatizado batendo de fato em `services/database.py`/`services/mailer.py`).
- [ ] CI não roda `scripts/verificar_schema.py` (exigiria um MariaDB com o schema real do GLPI disponível no runner). Rodar esse script manualmente após mudanças de schema, ou considerar um job de CI separado com um MariaDB de teste + fixtures simulando as views do GLPI.
- [ ] `scripts/verificar_schema.py` valida que as queries *executam* (via `EXPLAIN`), mas não valida que os *nomes/tipos de coluna retornados* continuam batendo com o que `config/reports.py`/`COLUNAS_LABEL`/os templates esperam — uma view que passa a retornar uma coluna a mais/a menos sem quebrar o `EXPLAIN` não seria pega por esse script.
- [ ] Nenhum hardening de systemd (`NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp` etc.) está de fato aplicado nos `.service` de `systemd/` hoje — considerar adicionar antes de produção definitiva.
- [ ] Confirmar no servidor de produção que as instâncias de timer habilitadas usam os nomes de relatório atuais (`atendimento_mensal_grupo`, `atendimento_semanal_grupo`, `atendimento_anual_grupo`, `atendimento_criticos_grupo`, `relatorio_mensal_diretores`) — instâncias antigas de antes da consolidação (`atendimento_mensal_infra`, `chamados_criticos_infra` etc.) não existem mais em `config/reports.py` e vão falhar se ainda estiverem habilitadas.
