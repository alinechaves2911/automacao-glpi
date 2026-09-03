SELECT *
FROM vw_dashboard_sla_semanal
WHERE grupo = :grupo
    AND semana_inicio BETWEEN :inicio AND :fim;
