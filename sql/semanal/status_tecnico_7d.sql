SELECT
  tecnico AS "Técnico",
  COUNT(DISTINCT CASE WHEN status = 1 THEN chamado_id END) AS "Novo",
  COUNT(DISTINCT CASE WHEN status = 2 THEN chamado_id END) AS "Em atendimento (atribuído)",
  COUNT(DISTINCT CASE WHEN status = 3 THEN chamado_id END) AS "Em atendimento (planejado)",
  COUNT(DISTINCT CASE WHEN status = 4 THEN chamado_id END) AS "Pendente",
  COUNT(DISTINCT CASE WHEN status = 5 THEN chamado_id END) AS "Solucionado",
  COUNT(DISTINCT CASE WHEN status = 6 THEN chamado_id END) AS "Fechado",
  COUNT(DISTINCT chamado_id) AS "Total Geral"
FROM vw_dashboard_tecnicos
WHERE grupo = :grupo
    AND dia BETWEEN :inicio AND :fim
GROUP BY tecnico
ORDER BY `Total Geral` DESC;