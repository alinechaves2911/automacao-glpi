SELECT categoria_completa,
 COUNT(DISTINCT chamado_id) AS total, 
 COUNT(DISTINCT CASE WHEN resolvido_flag = 1 THEN chamado_id END) AS resolvidos, 
 COUNT(DISTINCT chamado_id) - COUNT(DISTINCT CASE WHEN resolvido_flag = 1 THEN chamado_id END) AS em_aberto 
FROM vw_dashboard_categorias
WHERE grupo IN ('Suporte Técnico - 1º Nível', 'Suporte Técnico - 2º Nível', 'Administração de Sistemas', 'Redes e Telecomunicações', 'Desenvolvimento e Aplicações') 
    AND ano = :ano
    AND mes = :mes
GROUP BY categoria_completa
ORDER BY total DESC LIMIT 33;
