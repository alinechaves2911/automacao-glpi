SELECT grupo,
    COUNT(DISTINCT chamado_id) AS total_no_mes, 
    COUNT(DISTINCT CASE WHEN resolvido_flag = 1 THEN chamado_id END) AS resolvidos, 
    COUNT(DISTINCT chamado_id) - 
    COUNT(DISTINCT CASE WHEN resolvido_flag = 1 THEN chamado_id END) AS em_aberto 
FROM vw_dashboard_temporal 
WHERE grupo IN ('Suporte Técnico - 1º Nível', 'Suporte Técnico - 2º Nível', 'Administração de Sistemas', 'Redes e Telecomunicações', 'Desenvolvimento e Aplicações') 
AND ano = :ano AND mes = :mes 
GROUP BY grupo;

