#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste direto no banco para verificar compatibilidades JSON
"""
import sys
sys.path.insert(0, 'C:\\Users\\Gustavo Marquardt\\Documents\\GRANPIX')

from src.database import DatabaseManager
import json

# Conectar ao banco
db = DatabaseManager()

print("\n[TEST] Verificando peças e compatibilidades")
print("="*60)

# Conectar e obter peças
conn = db._get_conn()
cursor = conn.cursor()

cursor.execute('SELECT id, nome, compatibilidade FROM pecas_loja LIMIT 5')
pecas = cursor.fetchall()

print(f"\n✓ Primeiras 5 peças do banco:")
for peca in pecas:
    peca_id, nome, compatibilidade = peca
    print(f"\n  ID: {peca_id}")
    print(f"  Nome: {nome}")
    print(f"  Compatibilidade RAW: {repr(compatibilidade)}")
    
    # Tentar parsear como JSON
    if isinstance(compatibilidade, str) and compatibilidade.startswith('{'):
        try:
            data = json.loads(compatibilidade)
            compatibilidades_list = data.get('compatibilidades', [])
            print(f"  ✓ Compatibilidades (JSON): {compatibilidades_list}")
        except Exception as e:
            print(f"  ❌ Erro ao parsear JSON: {e}")
    else:
        print(f"  ⚠ Formato não é JSON: {type(compatibilidade)}")

conn.close()

print("\n" + "="*60)
print("✓ Teste concluído!")
