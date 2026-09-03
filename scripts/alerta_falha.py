"""
scripts/alerta_falha.py

Executado pelo systemd via OnFailure= sempre que algum service de
relatório (automacao-glpi-critico@, -mensal@, -semanal@ ou o genérico)
termina com falha.

Recebe como argumento o nome da unit que falhou (systemd expande isso
via %I no arquivo automacao-glpi-alerta@.service) e:
  1. Lê as últimas linhas do journal dessa unit, pra dar contexto do erro
     sem precisar abrir o servidor.
  2. Envia um e-mail de alerta para DESTINATARIOS_DIRETORIA, reaproveitando
     as credenciais SMTP já configuradas no .env.
  3. Se o binário zabbix_sender existir no host, envia um trap para o
     Zabbix na chave 'automacaoglpi.falha' (item trapper — ver
     zabbix/userparameter_automacaoglpi.conf e o README da pasta zabbix/).

De propósito, este script NÃO importa services/reporter_runner.py nem
qualquer outro módulo do pipeline principal além de config/settings.py —
se a falha original for causada por um import quebrado em outro módulo,
o alerta ainda precisa conseguir ser enviado.

Uso manual (para testar sem esperar uma falha real):
    python3 scripts/alerta_falha.py "automacao-glpi-critico@sla_semanal.service"
"""
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

# Garante que "config" seja importável mesmo se o systemd chamar este
# script com um WorkingDirectory diferente por engano.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from config import settings
except Exception as e:  # pragma: no cover - caminho defensivo, não o fluxo normal
    print(f"[alerta_falha] Não foi possível carregar config/settings.py: {e}", file=sys.stderr)
    settings = None

try:
    from zabbix_utils import Sender, ItemValue
except Exception:  # pragma: no cover - caminho defensivo
    Sender = None
    ItemValue = None

# IP/host do servidor Zabbix e nome do host cadastrado lá — configuráveis
# via ZABBIX_SERVER/ZABBIX_HOST no .env (config/settings.py), porque cada
# ambiente (lab, produção) reporta para um host Zabbix diferente a partir
# do mesmo código. O nome precisa bater EXATAMENTE com o "Hostname=" usado
# no zabbix_agent2.conf daquele servidor.
ZABBIX_SERVER = settings.ZABBIX_SERVER if settings else "10.14.8.23"
ZABBIX_PORT = 10051
ZABBIX_HOST = settings.ZABBIX_HOST if settings else "AUTOMACAO-GLPI-LAB"
ZABBIX_CHAVE_FALHA = "automacaoglpi.falha"

LINHAS_JOURNAL = 30


def obter_ultimas_linhas_journal(unit: str, linhas: int = LINHAS_JOURNAL) -> str:
    try:
        resultado = subprocess.run(
            ["journalctl", "-u", unit, "-n", str(linhas), "--no-pager"],
            capture_output=True, text=True, timeout=10,
        )
        return resultado.stdout.strip() or "(journal vazio ou sem permissão de leitura)"
    except Exception as e:
        return f"(não foi possível ler o journal: {e})"


def enviar_email_alerta(unit: str, corpo: str) -> None:
    if settings is None:
        print("[alerta_falha] settings indisponível, e-mail de alerta não enviado.", file=sys.stderr)
        return

    destinatarios = settings.DESTINATARIOS_DIRETORIA
    if not destinatarios or destinatarios == [""]:
        print("[alerta_falha] DESTINATARIOS_DIRETORIA vazio, e-mail de alerta não enviado.", file=sys.stderr)
        return

    msg = MIMEText(corpo)
    msg["Subject"] = f"[ALERTA] Falha na automação GLPI \u2014 {unit}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = ", ".join(destinatarios)

    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.sendmail(settings.SMTP_FROM, destinatarios, msg.as_string())
        server.quit()
        print(f"[alerta_falha] E-mail de alerta enviado para {destinatarios}.")
    except Exception as e:
        print(f"[alerta_falha] Falha ao enviar e-mail de alerta: {e}", file=sys.stderr)


def enviar_trap_zabbix(unit: str) -> None:
    """
    Envia o alerta diretamente pro Zabbix server via socket (porta 10051),
    usando o pacote oficial zabbix-utils. Isso NÃO depende do binário
    zabbix_sender estar instalado no host, e funciona normalmente entre
    servidores diferentes na mesma rede (confirmado: automacaoGLPI e
    Zabbix estão na mesma VLAN, sem firewall entre eles).

    Item trapper (push) — independe de o host estar configurado como
    "passive" ou "active" pro resto dos checks do agent; um trap chega
    direto no servidor a qualquer momento.
    """
    if Sender is None:
        print("[alerta_falha] pacote zabbix-utils não instalado, trap não enviado.", file=sys.stderr)
        return

    mensagem = f"Falha em {unit} as {datetime.now().isoformat(timespec='seconds')}"
    try:
        sender = Sender(server=ZABBIX_SERVER, port=ZABBIX_PORT)
        item = ItemValue(ZABBIX_HOST, ZABBIX_CHAVE_FALHA, mensagem)
        resposta = sender.send([item])
        print(f"[alerta_falha] Trap enviado ao Zabbix: {resposta.processed} processado(s), {resposta.failed} falha(s).")
    except Exception as e:
        print(f"[alerta_falha] Falha ao enviar trap ao Zabbix: {e}", file=sys.stderr)


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: alerta_falha.py <nome_da_unit_que_falhou>", file=sys.stderr)
        sys.exit(1)

    unit = sys.argv[1]
    print(f"[alerta_falha] Disparado para a unit: {unit}")

    journal = obter_ultimas_linhas_journal(unit)
    corpo = (
        f"A unit systemd '{unit}' falhou.\n\n"
        f"Últimas {LINHAS_JOURNAL} linhas do journal:\n"
        f"{'-' * 60}\n{journal}\n{'-' * 60}\n\n"
        f"Para investigar diretamente no servidor:\n"
        f"  journalctl -u {unit} -n 100 --no-pager\n"
    )

    enviar_email_alerta(unit, corpo)
    enviar_trap_zabbix(unit)


if __name__ == "__main__":
    main()
