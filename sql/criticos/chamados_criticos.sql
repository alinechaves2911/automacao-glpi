SELECT 
    chamado_id, 
    titulo, 
    grupo, 
    tecnico, 
    categoria, 
    prioridade_nome, 
    status_nome, 
    dias_em_aberto 
FROM vw_dashboard_aging
WHERE grupo = :grupo
  AND dias_em_aberto >= 7
ORDER BY dias_em_aberto DESC;