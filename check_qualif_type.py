#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor()

# Verificar tipo de ordem_qualificacao em participacoes_etapas
c.execute('DESC participacoes_etapas')
schema = c.fetchall()

print("Schema de participacoes_etapas:")
for row in schema:
    col_name = row[0]
    col_type = row[1]
    if col_name == 'ordem_qualificacao':
        print(f"  ✓ {col_name}: {col_type}")
        
# Verificar dados
c.execute('''
    SELECT ordem_qualificacao, equipe_id
    FROM participacoes_etapas
    LIMIT 5
''')

rows = c.fetchall()
print("\nDados de participacoes_etapas:")
for row in rows:
    print(f"  ordem: {row[0]} (type: {type(row[0]).__name__}), equipe: {row[1][:8]}")

c.close()
conn.close()
