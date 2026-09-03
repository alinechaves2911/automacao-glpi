
-- SLA por tecnico com os mariores slas e mais total_com_sla
SELECT tecnico,
    SUM(total_com_sla) AS total_com_sla,
    SUM(dentro_do_prazo) AS dentro_do_prazo,
    SUM(fora_do_prazo) AS fora_do_prazo,
    ROUND(SUM(dentro_do_prazo) / NULLIF(SUM(total_com_sla), 0) * 100, 1) AS percentual_sla_ok
FROM vw_dashboard_sla_tecnico
WHERE grupo IN ('Suporte Técnico - 1º Nível', 'Suporte Técnico - 2º Nível', 'Administração de Sistemas', 'Redes e Telecomunicações', 'Desenvolvimento e Aplicações')
    AND ano = :ano
    AND mes = :mes
GROUP BY tecnico
HAVING SUM(total_com_sla) >= 1
ORDER BY total_com_sla DESC, percentual_sla_ok DESC;
