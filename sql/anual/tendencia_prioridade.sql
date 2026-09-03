SELECT chamado_id,ano, grupo, status_nome, prioridade_nome , data_abertura, solvedate
FROM vw_dashboard_temporal
WHERE grupo = :grupo
    AND ano = :ano;
