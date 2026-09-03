SELECT tecnico,
       SUM(total_com_sla) AS total_com_sla,
       SUM(dentro_do_prazo) AS dentro_do_prazo,
       SUM(fora_do_prazo) AS fora_do_prazo
FROM vw_dashboard_sla_tecnico
WHERE grupo = :grupo
    AND ano = :ano
GROUP BY tecnico;
