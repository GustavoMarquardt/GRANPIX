#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor()

tables = ['pilotos', 'equipes', 'etapas']

for t in tables:
    print(f"\n{t}:")
    c.execute(f'DESC {t}')
    rows = c.fetchall()
    for row in rows:
        col_name = row[0]
        col_type = row[1]
        is_pk = "PK" if row[3] == 'PRI' else ""
        print(f"  {col_name} ({col_type}) {is_pk}")

c.close()
conn.close()
