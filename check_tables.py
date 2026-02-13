import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='granpix'
)
cursor = conn.cursor()

cursor.execute("SHOW TABLES LIKE '%equipe%'")
tables = cursor.fetchall()
print('Tabelas com equipe:')
for table in tables:
    print(' -', table[0])

cursor.execute("SHOW TABLES LIKE '%etapa%'")
tables = cursor.fetchall()
print('Tabelas com etapa:')
for table in tables:
    print(' -', table[0])

cursor.close()
conn.close()