#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor(dictionary=True)

c.execute('''
    SELECT v.id_equipe, v.status, v.nota_linha, v.nota_angulo, v.nota_estilo,
           pe.ordem_qualificacao
    FROM volta v
    JOIN participacoes_etapas pe ON pe.piloto_id = v.id_piloto 
        AND pe.equipe_id = v.id_equipe
    WHERE v.id_etapa IN (SELECT id FROM etapas WHERE status = "em_andamento")
    ORDER BY pe.ordem_qualificacao
''')

voltas = c.fetchall()
print("Tabela volta com novos status:")
for v in voltas:
    status_hex = v['status'].encode('utf-8').hex() if v['status'] else "None"
    print(f"  QUAL {v['ordem_qualificacao']}: equipe={v['id_equipe'][:8]}, status={v['status']!r} (hex={status_hex}), notas={v['nota_linha']},{v['nota_angulo']},{v['nota_estilo']}")

c.close()
conn.close()
