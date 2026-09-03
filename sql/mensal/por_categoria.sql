SELECT categoria_completa,
 COUNT(DISTINCT chamado_id) AS total, 
 COUNT(DISTINCT CASE WHEN resolvido_flag = 1 THEN chamado_id END) AS resolvidos, 
 COUNT(DISTINCT chamado_id) - COUNT(DISTINCT CASE WHEN resolvido_flag = 1 THEN chamado_id END) AS em_aberto 
FROM vw_dashboard_categorias
WHERE grupo = :grupo
    AND ano = :ano
    AND mes = :mes
GROUP BY categoria_completa
ORDER BY resolvidos DESC;
