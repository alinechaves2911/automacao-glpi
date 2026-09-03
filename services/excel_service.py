"""
services/excel_service.py

Geração dos arquivos .xlsx anexados aos e-mails.

Renomeado de excel.py para excel_service.py para seguir o mesmo padrão
de nomes dos demais serviços.
"""
import pandas as pd

from services.logger import logger


def gerar_arquivo_excel_multi_aba(dfs: dict, nome_arquivo: str) -> str:
    """
    Recebe um dict {nome_aba: DataFrame} e gera um único .xlsx com
    uma aba para cada dataset. Nomes de aba no Excel são limitados
    a 31 caracteres — truncamos se necessário.

    :param dfs: dict retornado por executar_queries_do_relatorio
    :param nome_arquivo: nome do arquivo .xlsx de saída
    :return: nome do arquivo gerado
    """
    try:
        with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
            for nome_aba, df in dfs.items():
                aba_valida = nome_aba[:31]
                df.to_excel(writer, sheet_name=aba_valida, index=False)
        logger.info(f"Arquivo Excel '{nome_arquivo}' gerado com sucesso! ({len(dfs)} aba(s))")
        return nome_arquivo
    except Exception as e:
        logger.exception(f"Erro ao gerar o arquivo Excel '{nome_arquivo}': {e}")
        raise
