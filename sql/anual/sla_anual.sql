SELECT *
FROM vw_dashboard_sla
WHERE grupo = :grupo
    AND ano = :ano;
