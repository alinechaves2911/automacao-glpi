SELECT categoria,
       COUNT(DISTINCT chamado_id) AS total,
       CAST(SUM(resolvido_flag) AS UNSIGNED) AS resolvidos,
       CAST(COUNT(DISTINCT chamado_id) - SUM(resolvido_flag) AS SIGNED) AS em_aberto
FROM vw_dashboard_categorias
WHERE grupo = :grupo
    AND ano = :ano
GROUP BY categoria
ORDER BY resolvidos DESC;
