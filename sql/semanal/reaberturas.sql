SELECT grupo,
       tecnico,
       chamado_id,
       titulo,
       data_ultima_reabertura,
       qtd_reaberturas
FROM vw_dashboard_reaberturas
WHERE grupo = :grupo
LIMIT 10;
