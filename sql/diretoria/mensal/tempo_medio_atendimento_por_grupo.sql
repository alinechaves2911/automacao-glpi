SELECT *
FROM vw_dashboard_tempo_medio
WHERE grupo IN ('Suporte Técnico - 1º Nível', 'Suporte Técnico - 2º Nível', 'Administração de Sistemas', 'Redes e Telecomunicações', 'Desenvolvimento e Aplicações') 
    AND ano = :ano
    AND mes = :mes;
