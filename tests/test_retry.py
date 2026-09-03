"""
tests/test_retry.py

Cobre services/retry.py — o decorator de retry/backoff usado tanto por
services/database.py (conexão MariaDB) quanto por services/mailer.py
(handshake SMTP). Ver README, "Ainda pendente": faltava cobertura de
database.py/mailer.py; como ambos delegam a lógica de retry para este
módulo comum, testar o decorator isoladamente (sem precisar de um banco
ou SMTP de verdade) cobre a parte que realmente importa: quantas vezes
tenta, quanto espera, e quais exceções disparam retry.
"""
import time

import pytest

from services.retry import retry_com_backoff


class ErroTransitorio(Exception):
    """Simula um erro de rede/timeout — deveria disparar retry."""


class ErroPermanente(Exception):
    """Simula um erro de sintaxe/credencial — NÃO deveria disparar retry."""


def _sem_espera(monkeypatch):
    """Remove o time.sleep() real dos testes, sem alterar a lógica testada."""
    monkeypatch.setattr(time, "sleep", lambda segundos: None)


def test_sucesso_de_primeira_nao_dispara_retry(monkeypatch):
    _sem_espera(monkeypatch)
    chamadas = []

    @retry_com_backoff((ErroTransitorio,), tentativas=3, espera_inicial=1.0)
    def func():
        chamadas.append(1)
        return "ok"

    resultado = func()

    assert resultado == "ok"
    assert len(chamadas) == 1


def test_sucesso_apos_falhas_transitorias(monkeypatch):
    _sem_espera(monkeypatch)
    chamadas = []

    @retry_com_backoff((ErroTransitorio,), tentativas=3, espera_inicial=1.0)
    def func():
        chamadas.append(1)
        if len(chamadas) < 3:
            raise ErroTransitorio("falha momentânea")
        return "ok"

    resultado = func()

    assert resultado == "ok"
    assert len(chamadas) == 3  # falhou 2x, teve sucesso na 3ª


def test_esgota_tentativas_e_propaga_a_ultima_excecao(monkeypatch):
    _sem_espera(monkeypatch)
    chamadas = []

    @retry_com_backoff((ErroTransitorio,), tentativas=3, espera_inicial=1.0)
    def func():
        chamadas.append(1)
        raise ErroTransitorio(f"falha {len(chamadas)}")

    with pytest.raises(ErroTransitorio, match="falha 3"):
        func()

    assert len(chamadas) == 3  # tentou exatamente o número configurado, nem mais nem menos


def test_excecao_fora_da_tupla_nao_dispara_retry(monkeypatch):
    """
    Erro de sintaxe SQL ou credencial inválida não deve ser retentado —
    é exatamente o caso de uso documentado em services/database.py e
    services/mailer.py (SMTPAuthenticationError não entra na tupla de
    exceções transitórias).
    """
    _sem_espera(monkeypatch)
    chamadas = []

    @retry_com_backoff((ErroTransitorio,), tentativas=3, espera_inicial=1.0)
    def func():
        chamadas.append(1)
        raise ErroPermanente("credencial inválida")

    with pytest.raises(ErroPermanente):
        func()

    assert len(chamadas) == 1  # nenhuma tentativa extra


def test_backoff_exponencial_respeita_fator(monkeypatch):
    """
    espera_inicial=2.0, fator=2.0 -> as esperas entre tentativas devem
    ser 2s, depois 4s (nunca tentadas de novo após a última falha).
    """
    esperas_registradas = []
    monkeypatch.setattr(time, "sleep", lambda segundos: esperas_registradas.append(segundos))

    @retry_com_backoff((ErroTransitorio,), tentativas=3, espera_inicial=2.0, fator=2.0)
    def func():
        raise ErroTransitorio("sempre falha")

    with pytest.raises(ErroTransitorio):
        func()

    assert esperas_registradas == [2.0, 4.0]


def test_tentativas_igual_a_1_nao_faz_retry_nenhum(monkeypatch):
    _sem_espera(monkeypatch)
    chamadas = []

    @retry_com_backoff((ErroTransitorio,), tentativas=1, espera_inicial=1.0)
    def func():
        chamadas.append(1)
        raise ErroTransitorio("falha única")

    with pytest.raises(ErroTransitorio):
        func()

    assert len(chamadas) == 1


def test_preserva_nome_e_docstring_da_funcao_original():
    """functools.wraps deve manter introspecção normal (útil para logs/debug)."""

    @retry_com_backoff((ErroTransitorio,))
    def minha_funcao_especial():
        """Docstring original."""

    assert minha_funcao_especial.__name__ == "minha_funcao_especial"
    assert minha_funcao_especial.__doc__ == "Docstring original."


def test_repassa_args_e_kwargs_para_a_funcao_original(monkeypatch):
    _sem_espera(monkeypatch)

    @retry_com_backoff((ErroTransitorio,))
    def soma(a, b, c=0):
        return a + b + c

    assert soma(1, 2, c=3) == 6
