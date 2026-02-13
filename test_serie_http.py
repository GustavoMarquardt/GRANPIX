#!/usr/bin/env python3
"""Teste simulando a criação de equipe com série B exatamente como feito via POST"""

import mysql.connector
import requests
import json
import time

# Ler config
config = {}
with open('src/config.py', 'r') as f:
    for line in f:
        if 'MYSQL_' in line and '=' in line and not line.strip().startswith('#'):
            try:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"\'')
                if k in ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB']:
                    config[k] = v
            except:
                pass

print("="*60)
print("TESTE: Criação de equipe com Série B")
print("="*60)

# ===== TESTE VIA POST HTTP (Como o frontend faz) =====
print("\n1. Enviando POST para /api/admin/cadastrar-equipe...")

payload = {
    "nome": "Test_Serie_B_" + str(int(time.time())),
    "doricoins": 100000,
    "senha": "teste123",
    "serie": "B",
    "carro_id": None
}

print(f"   Payload: {json.dumps(payload, indent=2)}")

try:
    # Tentar conectar ao servidor Flask
    resp = requests.post(
        'http://localhost:5000/api/admin/cadastrar-equipe',
        json=payload,
        timeout=10
    )
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
except Exception as e:
    print(f"   ERRO ao conectar ao servidor: {e}")
    print("   (Flask pode não estar rodando)")

# ===== VERIFICAR NO BANCO =====
print("\n2. Verificando todas as equipes no banco...")

try:
    conn = mysql.connector.connect(
        host=config.get('MYSQL_HOST', 'localhost'),
        user=config.get('MYSQL_USER', 'root'),
        password=config.get('MYSQL_PASSWORD', ''),
        database=config.get('MYSQL_DB', 'granpix')
    )
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, nome, serie FROM equipes ORDER BY data_criacao DESC LIMIT 3")
    rows = cursor.fetchall()
    print(f"\n   Últimas 3 equipes criadas:")
    for row in rows:
        print(f"   - {row['nome']}: série = '{row['serie']}'")
    
    conn.close()
except Exception as e:
    print(f"   ERRO: {e}")

print("\n" + "="*60)
