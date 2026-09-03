SELECT COUNT(DISTINCT chamado_id) AS total_no_ano,
       SUM(resolvido_flag) AS resolvidos
FROM vw_dashboard_temporal
WHERE grupo = :grupo
    AND ano = :ano;
