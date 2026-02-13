#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor(dictionary=True)

# Verificar estrutura da tabela volta
c.execute("DESCRIBE volta")
estrutura = c.fetchall()

print("Estrutura da tabela volta:")
for col in estrutura:
    print(f"  {col['Field']}: {col['Type']}")

print("\nVerificando ENUM values:")
c.execute("""SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'volta' AND COLUMN_NAME = 'status'""")
result = c.fetchone()
if result:
    print(f"  Status column type: {result['COLUMN_TYPE']}")

# Verificar dados reais
print("\nDados reais na volta:")
c.execute("SELECT id, status, HEX(status) as status_hex FROM volta LIMIT 3")
dados = c.fetchall()
for d in dados:
    print(f"  ID: {d['id'][:8]}, Status length: {len(d['status']) if d['status'] else 0}, Status: {d['status']!r}, Hex: {d['status_hex']}")

c.close()
conn.close()
