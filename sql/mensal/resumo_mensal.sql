SELECT 
    COUNT(DISTINCT chamado_id) AS total_no_mes,
    COUNT(DISTINCT CASE WHEN resolvido_flag = 1 THEN chamado_id END) AS resolvidos,
    COUNT(DISTINCT chamado_id) - COUNT(DISTINCT CASE WHEN resolvido_flag = 1 THEN chamado_id END) AS em_aberto
FROM vw_dashboard_temporal
WHERE grupo = :grupo
    AND ano = :ano
    AND mes = :mes;
