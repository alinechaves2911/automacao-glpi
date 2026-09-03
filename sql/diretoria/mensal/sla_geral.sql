SELECT grupo,
        SUM(total_com_sla) AS total_com_sla,
        SUM(dentro_do_prazo) AS dentro_do_prazo, 
        SUM(fora_do_prazo) AS fora_do_prazo, 
        SUM(em_andamento_prazo) AS em_andamento_prazo,
        ROUND(SUM(dentro_do_prazo) / NULLIF(SUM(total_com_sla), 0) * 100, 1) AS percentual_sla 
FROM vw_dashboard_sla 
WHERE grupo IN ('Suporte Técnico - 1º Nível', 'Suporte Técnico - 2º Nível', 'Administração de Sistemas', 'Redes e Telecomunicações', 'Desenvolvimento e Aplicações') 
AND ano = :ano AND mes = :mes 
GROUP BY grupo;

