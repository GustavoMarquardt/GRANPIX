#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor()

c.execute('''
    SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, COLLATION_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = "granpix" 
    AND TABLE_NAME IN ("pilotos", "equipes", "etapas") 
    AND COLUMN_NAME = "id"
''')

rows = c.fetchall()
print("Collation das colunas PK:")
for r in rows:
    print(f"  {r[0]}.{r[1]}: {r[2]} - {r[3]}")

c.close()
conn.close()
