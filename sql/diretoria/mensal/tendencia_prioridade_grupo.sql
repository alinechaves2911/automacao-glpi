SELECT grupo, prioridade_nome, COUNT(chamado_id) AS total
FROM vw_dashboard_temporal
WHERE grupo IN ('Suporte Técnico - 1º Nível', 'Suporte Técnico - 2º Nível', 'Administração de Sistemas', 'Redes e Telecomunicações', 'Desenvolvimento e Aplicações')
    AND ano = :ano
    AND mes = :mes
GROUP BY grupo, prioridade_nome
ORDER BY grupo ASC,
    FIELD(prioridade_nome COLLATE utf8mb4_uca1400_ai_ci,
          'Muito Alta', 'Alta', 'Média', 'Baixa', 'Muito Baixa');
