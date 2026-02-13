import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor()

# Desabilitar verificação de foreign keys temporariamente
cursor.execute("SET FOREIGN_KEY_CHECKS=0")

# Obter todas as tabelas
cursor.execute("SHOW TABLES")
tables = cursor.fetchall()

print(f"Apagando {len(tables)} tabelas...")
for table in tables:
    table_name = table[0]
    print(f"  Apagando: {table_name}")
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

# Reabilitar verificação de foreign keys
cursor.execute("SET FOREIGN_KEY_CHECKS=1")

conn.commit()
conn.close()

print("✅ Banco de dados limpo!")
print("Próxima execução da aplicação vai recriar todas as tabelas.")
