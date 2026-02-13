#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from src.api import APIGranpix

api = APIGranpix('mysql://root:@localhost:3306/granpix')

# Testar se a migração foi feita
print("Verificando estrutura da tabela pecas...")
import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='1234', database='granpix')
cursor = conn.cursor()

cursor.execute("DESCRIBE pecas")
colunas = cursor.fetchall()

print("\nColunas da tabela pecas:")
for coluna in colunas:
    print(f"  {coluna[0]:25} {coluna[1]:20} {str(coluna[2]):5} {str(coluna[3]):5} {str(coluna[4]):20}")

# Verificar especificamente por equipe_id
tem_equipe_id = any(col[0] == 'equipe_id' for col in colunas)
print(f"\n✓ Coluna 'equipe_id' existe: {tem_equipe_id}")

conn.close()
