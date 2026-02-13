#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor(dictionary=True)

# Verificar voltas
c.execute('''
    SELECT v.id_piloto, v.id_equipe, v.id_etapa, v.status, v.data_criacao
    FROM volta v
    WHERE v.id_etapa = (SELECT id FROM etapas WHERE status = "em_andamento" LIMIT 1)
    ORDER BY v.data_criacao ASC
''')

rows = c.fetchall()
print("Voltas com status aberto:")
for row in rows:
    print(f"  Equipe: {row['id_equipe'][:8]}, Status: {row['status']}")

# Verificar participação para ordem
c.execute('''
    SELECT v.id_equipe, pe.ordem_qualificacao, v.status
    FROM volta v
    INNER JOIN participacoes_etapas pe ON pe.equipe_id = v.id_equipe
    WHERE v.id_etapa = (SELECT id FROM etapas WHERE status = "em_andamento" LIMIT 1)
    ORDER BY pe.ordem_qualificacao ASC
''')

rows = c.fetchall()
print("\nVoltas com ordem de qualificação:")
for row in rows:
    print(f"  QUAL: {row['ordem_qualificacao']}, Equipe: {row['id_equipe'][:8]}, Status: {row['status']}")

c.close()
conn.close()
