SELECT *
FROM vw_dashboard_sla_tecnico
WHERE grupo = :grupo
    AND ano = :ano
    AND mes = :mes
GROUP BY tecnico
ORDER BY percentual_sla_ok DESC;