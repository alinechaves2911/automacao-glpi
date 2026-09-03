SELECT *
FROM vw_dashboard_tempo_medio
WHERE grupo = :grupo
    AND ano = :ano
    AND mes = :mes;
