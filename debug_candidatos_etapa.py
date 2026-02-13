#!/usr/bin/env python3
"""Debug: Verificar candidatos e participações por etapa"""

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
print("DEBUG: CANDIDATOS E PARTICIPAÇÕES POR ETAPA")
print("="*70)

# Obter etapa de hoje
cursor.execute("SELECT id, numero, data_etapa FROM etapas WHERE data_etapa = CURDATE() LIMIT 1")
etapa = cursor.fetchone()

if not etapa:
    print("\n❌ Nenhuma etapa para hoje!")
    conn.close()
    exit(1)

etapa_id = etapa['id']
print(f"\n📅 Etapa: {etapa['numero']} (ID: {etapa_id})")

# Candidatos por equipe
print("\n1️⃣  CANDIDATOS INSCRITOS:")
cursor.execute('''
    SELECT 
        e.nome as equipe_nome,
        COUNT(cpe.id) as total_candidatos
    FROM candidatos_piloto_etapa cpe
    INNER JOIN equipes e ON cpe.equipe_id = e.id
    WHERE cpe.etapa_id = %s AND cpe.status = 'pendente'
    GROUP BY cpe.equipe_id, e.nome
    ORDER BY e.nome
''', (etapa_id,))

candidatos_por_equipe = cursor.fetchall()
for row in candidatos_por_equipe:
    print(f"   - {row['equipe_nome']}: {row['total_candidatos']} candidatos")

# Participações por equipe
print("\n2️⃣  PARTICIPAÇÕES (tipo precisa_piloto):")
cursor.execute('''
    SELECT 
        e.nome as equipe_nome,
        pe.tipo_participacao,
        pe.piloto_id,
        COUNT(pe.id) as total
    FROM participacoes_etapas pe
    INNER JOIN equipes e ON pe.equipe_id = e.id
    WHERE pe.etapa_id = %s AND pe.tipo_participacao = 'precisa_piloto'
    GROUP BY pe.equipe_id, e.nome, pe.tipo_participacao
    ORDER BY e.nome
''', (etapa_id,))

participacoes = cursor.fetchall()
for row in participacoes:
    print(f"   - {row['equipe_nome']}: tipo={row['tipo_participacao']}, piloto_id={row['piloto_id']}")

# A query original da função
print("\n3️⃣  RESULTADO DA QUERY DA FUNÇÃO (candidatos com INNER JOIN participacoes - tipo='precisa_piloto'):")
cursor.execute('''
    SELECT 
        cpe.id as candidato_id,
        cpe.etapa_id,
        cpe.equipe_id,
        e.nome as equipe_nome,
        cpe.piloto_id,
        p.nome as piloto_nome,
        cpe.status,
        pe.tipo_participacao,
        pe.piloto_id as pe_piloto_id
    FROM candidatos_piloto_etapa cpe
    INNER JOIN equipes e ON cpe.equipe_id = e.id
    INNER JOIN pilotos p ON cpe.piloto_id = p.id
    INNER JOIN participacoes_etapas pe ON cpe.etapa_id = pe.etapa_id AND cpe.equipe_id = pe.equipe_id
    WHERE cpe.etapa_id = %s 
      AND cpe.status = 'pendente'
      AND pe.tipo_participacao = 'precisa_piloto'
''', (etapa_id,))

candidatos_filtrados = cursor.fetchall()
print(f"   Total de registros retornados: {len(candidatos_filtrados)}")

equipes_unicas = {}
for row in candidatos_filtrados:
    equipe_id = row['equipe_id']
    if equipe_id not in equipes_unicas:
        equipes_unicas[equipe_id] = row['equipe_nome']

print(f"   Equipes únicas: {len(equipes_unicas)}")
for eq_nome in equipes_unicas.values():
    print(f"   - {eq_nome}")

conn.close()
print("\n" + "="*70 + "\n")
