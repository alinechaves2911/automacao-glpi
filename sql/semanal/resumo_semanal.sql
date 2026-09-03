SELECT COUNT(DISTINCT chamado_id) AS abertos_na_semana,
       SUM(resolvido_flag) AS resolvidos_na_semana
FROM vw_dashboard_temporal
WHERE grupo = :grupo
    AND data_abertura >= :inicio
    AND data_abertura < :fim_exclusivo;
