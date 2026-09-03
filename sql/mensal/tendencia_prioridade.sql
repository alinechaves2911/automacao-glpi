SELECT *
FROM vw_dashboard_temporal
WHERE grupo = :grupo
    AND ano = :ano
    AND mes = :mes;
