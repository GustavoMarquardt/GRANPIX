#!/usr/bin/env python3
"""Debug simples - verificar série no banco de dados"""

import mysql.connector
import json

# Conectar ao banco
with open('src/config.py', 'r') as f:
    config_content = f.read()
    
# Extrair config
config = {}
for line in config_content.split('\n'):
    if '=' in line and not line.strip().startswith('#'):
        try:
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"\'')
            if k in ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB']:
                config[k] = v
        except:
            pass

print("Conectando ao MySQL...")
print(f"Host: {config.get('MYSQL_HOST')}")
print(f"DB: {config.get('MYSQL_DB')}")

try:
    conn = mysql.connector.connect(
        host=config.get('MYSQL_HOST', 'localhost'),
        user=config.get('MYSQL_USER', 'root'),
        password=config.get('MYSQL_PASSWORD', ''),
        database=config.get('MYSQL_DB', 'granpix')
    )
    cursor = conn.cursor(dictionary=True)
    
    print("\n" + "="*60)
    print("VERIFICANDO SÉRIE DE EQUIPES")
    print("="*60)
    
    cursor.execute("DESCRIBE equipes")
    print("\nColunas da tabela equipes:")
    for col in cursor.fetchall():
        print(f"  - {col['Field']}: {col['Type']}")
    
    cursor.execute("SELECT id, nome, serie FROM equipes")
    rows = cursor.fetchall()
    print(f"\nEquipes no banco ({len(rows)} total):")
    for row in rows:
        print(f"  - {row['nome']}: série = '{row['serie']}'")
    
    conn.close()
    print("\n" + "="*60)
    
except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
