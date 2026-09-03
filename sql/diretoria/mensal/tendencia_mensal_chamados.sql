SELECT grupo, ano, mes,
        COUNT(DISTINCT chamado_id) AS total, 
        COUNT(DISTINCT CASE WHEN resolvido_flag = 1 THEN chamado_id END) AS resolvidos 
FROM vw_dashboard_temporal 
WHERE grupo IN ('Suporte Técnico - 1º Nível', 'Suporte Técnico - 2º Nível', 'Administração de Sistemas', 'Redes e Telecomunicações', 'Desenvolvimento e Aplicações') 
AND ((ano = :ano AND mes <= :mes) OR ano < :ano) 
GROUP BY grupo, ano, mes 
 ORDER BY ano DESC, mes DESC 
LIMIT 18;

