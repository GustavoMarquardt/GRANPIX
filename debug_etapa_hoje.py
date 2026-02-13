#!/usr/bin/env python3
"""Debug: Verificar se o endpoint /api/admin/etapa-hoje retorna dados"""

import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'granpix'
}

conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor(dictionary=True)

print("\n" + "="*70)
print("DEBUG: VERIFICAR ETAPA DE HOJE")
print("="*70)

# Obter etapa de hoje
print("\n1️⃣  Buscando etapa para hoje (data atual: CURDATE())...")
cursor.execute('''
    SELECT 
        e.id,
        e.numero,
        e.nome,
        e.data_etapa,
        e.hora_etapa,
        e.serie,
        c.id as campeonato_id,
        c.nome as campeonato_nome
    FROM etapas e
    LEFT JOIN campeonatos c ON e.campeonato_id = c.id
    WHERE DATE(e.data_etapa) = CURDATE()
    LIMIT 1
''')

etapa = cursor.fetchone()

if etapa:
    print(f"\n✅ ETAPA ENCONTRADA:")
    for key, value in etapa.items():
        print(f"   {key}: {value}")
else:
    print(f"\n❌ NENHUMA ETAPA ENCONTRADA PARA HOJE!")
    print(f"\n   Verificando etapas PRÓXIMAS:")
    cursor.execute('''
        SELECT 
            e.id,
            e.numero,
            e.nome,
            e.data_etapa,
            e.hora_etapa,
            e.serie,
            c.nome as campeonato_nome
        FROM etapas e
        LEFT JOIN campeonatos c ON e.campeonato_id = c.id
        ORDER BY e.data_etapa ASC, e.numero ASC
        LIMIT 5
    ''')
    
    proximas = cursor.fetchall()
    for et in proximas:
        print(f"   - {et['numero']}: {et['nome']} em {et['data_etapa']} ({et['data_etapa'].strftime('%d/%m/%Y') if hasattr(et['data_etapa'], 'strftime') else et['data_etapa']})")

# Verificar data de hoje
print("\n2️⃣  Verificando CURDATE()...")
cursor.execute("SELECT CURDATE() as hoje")
hoje = cursor.fetchone()
print(f"   Data de hoje no banco: {hoje['hoje']}")

conn.close()
print("\n" + "="*70 + "\n")
