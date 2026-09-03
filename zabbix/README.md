# Monitoramento Zabbix — automacaoGLPI

Setup confirmado: servidor Zabbix em `10.0.0.30:8080` (mesma rede do
servidor da automacaoGLPI, sem firewall entre os dois) — monitorado via
**passive checks** (mais simples de configurar/depurar que active checks,
e não há motivo pra active aqui já que não há restrição de rede).

Este diretório cobre a configuração do lado do **agente** (host onde a
automação roda). O lado do **servidor/frontend Zabbix** (itens, triggers)
é configurado manualmente pela interface web em `10.0.0.30:8080` — os
passos abaixo descrevem o que criar lá. A seção 5 lista o conjunto exato
já criado no host de laboratório (`AUTOMACAO-GLPI-PROD`, hostid `10684`),
pronto para replicar no host de produção.

## 1. Instalar e configurar o zabbix-agent2 no servidor da automacaoGLPI

```bash
# No servidor onde o automacaoGLPI roda (NÃO no 10.0.0.30):
apt install zabbix-agent2
```

Editar `/etc/zabbix/zabbix_agent2.conf` com o conteúdo de
`agent-automacaoglpi.conf.snippet` (ajustar `Hostname=` se usar outro nome
— precisa bater EXATAMENTE com o "Host name" cadastrado no passo 2).

**Habilitar `UnsafeUserParameters=1`** — sem isso, o agent recusa
qualquer UserParameter cujo valor substituído contenha certos caracteres
"especiais", e **todo nome de unit systemd deste projeto usa `@`**
(padrão de unit template, ex: `automacao-glpi-critico@atendimento_criticos_grupo.service`)
— sem essa opção, `automacaoglpi.unit.state[*]`, `.result[*]` e
`.last_run[*]` retornam sempre `ZBX_NOTSUPPORTED: Character "@" is not
allowed`, mesmo com o parâmetro entre aspas. `automacaoglpi.report.duracao[*]`
não é afetado (o nome do relatório não tem `@`).

```bash
echo "UnsafeUserParameters=1" >> /etc/zabbix/zabbix_agent2.conf
```

Copiar `userparameter_automacaoglpi.conf` para
`/etc/zabbix/zabbix_agent2.d/` e reiniciar:

```bash
cp userparameter_automacaoglpi.conf /etc/zabbix/zabbix_agent2.d/
systemctl restart zabbix-agent2
systemctl status zabbix-agent2   # confirmar que subiu sem erro
```

Garantir que o usuário do zabbix-agent2 consegue ler o journal (grupo
`systemd-journal`) e o diretório logs/ do projeto:

```bash
usermod -aG systemd-journal zabbix
```

Testar localmente, no próprio host da automacaoGLPI, antes de mexer no
servidor Zabbix (usa o binário do agent, não depende de rede):

```bash
/opt/zabbix-agent2/sbin/zabbix_agent2 -c /etc/zabbix/zabbix_agent2.conf \
  -t "automacaoglpi.unit.state[automacao-glpi-critico@atendimento_criticos_grupo.service]"
# esperado: ...[s|inactive] (ou active/failed, dependendo do momento)
```

## 2. Cadastrar o host no Zabbix (interface web, 10.0.0.30:8080)

`Data collection` → `Hosts` → `Create host`:
- **Host name**: exatamente o mesmo valor usado em `Hostname=` no agent
  (no host de laboratório: `AUTOMACAO-GLPI-PROD`).
- **Interfaces**: adicionar uma interface **Agent**, IP do servidor da
  automacaoGLPI, porta `10050`.
- **Templates**: nenhum obrigatório — os itens da seção 5 são criados
  manualmente ou via API (ver `docs/` do host de laboratório para o
  script usado), à sua escolha.

## 3. Testar a conectividade (antes de criar os itens)

A partir do PRÓPRIO servidor Zabbix (10.0.0.30), testando se ele
consegue consultar o agent remoto:

```bash
zabbix_get -s <IP_do_servidor_automacaoGLPI> -k "automacaoglpi.unit.state[automacao-glpi-critico@atendimento_criticos_grupo.service]"
```

Se retornar `active`, `inactive` ou `failed`, a passive check está
funcionando. Se der `ZBX_NOTSUPPORTED`/`Character "@" is not allowed`,
falta o `UnsafeUserParameters=1` do passo 1. Se der timeout, checar
firewall/porta 10050 e o `systemctl status zabbix-agent2` no host da
automacaoGLPI.

## 4. Item trapper para o alerta de falha (independe de passive/active)

`scripts/alerta_falha.py` envia o alerta direto pro Zabbix server via
socket (porta 10051), usando o pacote Python oficial `zabbix-utils`
(`pip install zabbix-utils`, já incluído em `requirements.txt`) — **não
depende do binário `zabbix_sender` estar instalado no host**, o que é
mais simples de manter entre servidores diferentes.

Isso é um item **trapper** (push): funciona independente de o host estar
configurado como passive ou active para o resto dos checks — o trap
chega no server a qualquer momento, direto na porta 10051.

Criar no Zabbix o item:
- **Key**: `automacaoglpi.falha`
- **Type**: Zabbix trapper
- **Type of information**: Text

Antes de usar em produção, ajustar em `scripts/alerta_falha.py`:
```python
ZABBIX_SERVER = "10.0.0.30"      # já correto
ZABBIX_HOST = "AUTOMACAO-GLPI-PROD"  # ajustar pro Host name EXATO cadastrado no passo 2
```

Testar manualmente (sem esperar uma falha real acontecer):
```bash
cd /opt/automacaoGLPI
venv/bin/python3 scripts/alerta_falha.py "teste-manual"
```

## 5. Itens e triggers já criados (referência para replicar em produção)

Este é o conjunto exato criado via API no host de laboratório
(`AUTOMACAO-GLPI-PROD`, hostid `10684`), cobrindo os 5 relatórios/units
habilitados hoje em `systemd/` — 23 itens + 18 triggers. Ao configurar o
host de produção, recriar o mesmo conjunto trocando só o hostid.

### Itens (tipo "Zabbix agent", passive — exceto o trapper)

Por unit (`automacao-glpi-critico@atendimento_criticos_grupo.service`,
`-semanal@atendimento_semanal_grupo`, `-mensal@atendimento_mensal_grupo`,
`-mensal@relatorio_mensal_diretores`, `-anual@atendimento_anual_grupo` —
5 units × 3 itens = 15):

| Chave | Tipo de dado | Delay |
|---|---|---|
| `automacaoglpi.unit.state[<unit>]` | Texto (character) | 5m |
| `automacaoglpi.unit.result[<unit>]` | Texto (character) | 5m |
| `automacaoglpi.unit.last_run[<unit>]` | Numérico (unsigned) | 5m |

Por nome de relatório (`atendimento_criticos_grupo`, `atendimento_semanal_grupo`,
`atendimento_mensal_grupo`, `relatorio_mensal_diretores`,
`atendimento_anual_grupo` — 5 itens):

| Chave | Tipo de dado | Delay |
|---|---|---|
| `automacaoglpi.report.duracao[<nome_relatorio>]` | Numérico (unsigned) | 15m |

Fixos (4 itens):

| Chave | Tipo | Tipo de dado | Delay |
|---|---|---|---|
| `automacaoglpi.falha` | Zabbix trapper | Texto | — (push) |
| `net.tcp.service[tcp,webmail.exemplo.gov.br,587]` | Simple check | Numérico | 1m |
| `net.tcp.service[tcp,10.0.0.30,3306]` | Simple check | Numérico | 1m |
| `automacaoglpi.db.conectividade` | Zabbix agent | Numérico (unsigned) | 1m |

`automacaoglpi.db.conectividade` roda `scripts/check_db_zabbix.py` (SELECT 1
real contra o banco, via `services.database.executar_query`) — mais forte que
o Simple Check de porta TCP acima, porque valida credencial e execução de
query, não só se a porta 3306 está aberta. Precisa de:

- **UserParameter** (em `zabbix_agentd.d/` ou `zabbix_agent2.d/`, conforme a
  versão do agent):
  ```
  UserParameter=automacaoglpi.db.conectividade,cd /opt/automacaoGLPI && sudo -u automacaoglpi /opt/automacaoGLPI/venv/bin/python3 scripts/check_db_zabbix.py >/dev/null 2>&1 && echo 1 || echo 0
  ```
- **sudoers** (`/etc/sudoers.d/zabbix-automacaoglpi`, criado via `visudo -f`
  — nunca editar direto com outro editor, sudoers corrompido pode travar
  o `sudo` da máquina inteira):
  ```
  zabbix ALL=(automacaoglpi) NOPASSWD: /opt/automacaoGLPI/venv/bin/python3 scripts/check_db_zabbix.py
  ```
  (o agent roda como usuário `zabbix`, sem acesso ao `.env` — chmod 600,
  dono `automacaoglpi` — daí a necessidade do `sudo -u`. Evite embutir
  `python3 -c "...; ...; ..."` diretamente no `UserParameter`/sudoers: o
  parser do sudoers trata `;` como separador de comando e rejeita a linha
  com "expected a fully-qualified path name" — por isso esse item chama um
  script de arquivo fixo em vez de um one-liner inline.)
- **Timeout do item no Zabbix**: aumentar pra ~10s (o padrão de 3s pode não
  ser suficiente — em caso de falha real, o retry com backoff de
  `executar_query` leva uns 6s antes de desistir).

Uso do IP `10.0.0.30` (em vez de `127.0.0.1`, mesmo o MariaDB rodando
no mesmo servidor da automacaoGLPI — `DB_HOST=localhost` no `.env` de
laboratório): o `zabbix-server` desta instância roda dentro de um
container Docker (`zabbix-server-pgsql`), então "Simple checks" são
executados de dentro do container — `127.0.0.1` ali é o loopback do
container, não o do host, e a checagem sempre falha mesmo com o MariaDB
saudável. Usar o IP real da máquina (roteável a partir do container via
a rede Docker) resolve. Em produção, se o `zabbix-server` rodar direto
no host (sem Docker) e o banco estiver noutro servidor, usar o IP real
do `DB_HOST` configurado lá.

### Triggers (18)

| Descrição | Expressão | Prioridade |
|---|---|---|
| Falha reportada (trapper) | `nodata(/HOST/automacaoglpi.falha,10m)=0` | High |
| `<unit>` não rodou no horário esperado (× 5, uma por unit) | `fuzzytime(/HOST/automacaoglpi.unit.last_run[<unit>],<janela>)=0` | Average |
| `<unit>` terminou em failed (× 5) | `last(/HOST/automacaoglpi.unit.result[<unit>])="failed"` | High |
| `<relatório>` demorando mais que o normal (× 5) | `last(/HOST/automacaoglpi.report.duracao[<nome>])>avg(/HOST/automacaoglpi.report.duracao[<nome>],7d)*1.5 and last(/HOST/automacaoglpi.report.duracao[<nome>])>0` | Warning |
| SMTP inacessível | `last(/HOST/net.tcp.service[tcp,webmail.exemplo.gov.br,587])=0` | High |
| MariaDB GLPI inacessível | `last(/HOST/net.tcp.service[tcp,10.0.0.30,3306])=0` | High |

`<janela>` do `fuzzytime` (em segundos — a função não aceita sufixos
combinados tipo `4d12h`, só um valor puro), com folga sobre o intervalo
real de cada `.timer`:

| Unit | Intervalo do timer | Janela usada |
|---|---|---|
| `-critico@atendimento_criticos_grupo` | Mon,Thu 08:00 (maior vão: 4 dias) | `388800` (4d12h) |
| `-semanal@atendimento_semanal_grupo` | Mon 08:00 | `691200` (8d) |
| `-mensal@atendimento_mensal_grupo` | dia 1 08:00 | `2851200` (33d) |
| `-mensal@relatorio_mensal_diretores` | dia 1 08:00 | `2851200` (33d) |
| `-anual@atendimento_anual_grupo` | 1º de janeiro 08:00 | `31968000` (370d) |

Os triggers de "não rodou no horário esperado" ficam falso-positivo até
cada unit rodar pela primeira vez (`unit.last_run` fica vazio até lá) —
normal, não indica problema.

## 6. Dependências externas (SMTP e MariaDB)

Já cobertas pelos dois itens "Simple check" da seção 5 — nenhum
UserParameter customizado necessário para eles.

Considerar também aplicar o template pronto de MySQL/MariaDB do Zabbix no
host do banco GLPI, se ainda não estiver aplicado.
