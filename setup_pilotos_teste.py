#!/usr/bin/env python3
"""
Script para criar:
1. 1 piloto inicial
2. Solicitações "preciso_piloto" para todas as equipes série A
3. 10 pilotos candidatos
4. Inscrever os 10 pilotos de forma aleatória nas equipes série A
"""

import mysql.connector
import uuid
import random
from datetime import datetime, timedelta

# Configuração do banco
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'granpix'
}

def conectar():
    return mysql.connector.connect(**DB_CONFIG)

def criar_piloto(piloto_id, piloto_nome):
    """Cria um novo piloto no banco"""
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute('''
            INSERT INTO pilotos (id, nome, equipe_id, vitoria, derrotas, empates)
            VALUES (%s, %s, NULL, 0, 0, 0)
            ON DUPLICATE KEY UPDATE nome = VALUES(nome)
        ''', (piloto_id, piloto_nome))
        
        conn.commit()
        print(f"   ✓ Piloto criado: {piloto_nome} ({piloto_id})")
        return True
    except Exception as e:
        print(f"   ✗ Erro ao criar piloto: {e}")
        return False
    finally:
        conn.close()

def obter_equipes_serie_a():
    """Obtém todas as equipes da série A"""
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT id, nome FROM equipes WHERE serie = 'A'")
        equipes = cursor.fetchall()
        return equipes
    finally:
        conn.close()

def obter_ou_criar_etapa():
    """Obtém uma etapa existente ou cria uma para hoje"""
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Verificar se há uma etapa para hoje
        cursor.execute('''
            SELECT id, numero, campeonato_id FROM etapas 
            WHERE data_etapa = CURDATE()
            LIMIT 1
        ''')
        
        etapa = cursor.fetchone()
        if etapa:
            print(f"   ✓ Etapa encontrada para hoje: {etapa['numero']} (ID: {etapa['id']})")
            return etapa['id']
        
        # Se não houver, usar primeira etapa do presente ou futuro
        cursor.execute('''
            SELECT id, numero, data_etapa FROM etapas 
            WHERE data_etapa >= CURDATE()
            ORDER BY data_etapa ASC, numero ASC
            LIMIT 1
        ''')
        
        etapa = cursor.fetchone()
        if etapa:
            print(f"   ✓ Etapa encontrada: {etapa['numero']} em {etapa['data_etapa']}")
            return etapa['id']
        
        # Se ainda não houver, criar uma para hoje
        print("   ! Nenhuma etapa encontrada, criando uma para hoje...")
        etapa_id = str(uuid.uuid4())
        campeonato_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT INTO campeonatos (id, nome, serie, data_criacao)
            VALUES (%s, %s, %s, NOW())
        ''', (campeonato_id, 'Campeonato Teste', 'A'))
        
        cursor.execute('''
            INSERT INTO etapas (id, campeonato_id, numero, nome, descricao, data_etapa, hora_etapa, serie, status)
            VALUES (%s, %s, 1, %s, %s, CURDATE(), '14:00:00', %s, 'agendada')
        ''', (etapa_id, campeonato_id, 'Etapa Teste', 'Etapa para teste', 'A'))
        
        conn.commit()
        print(f"   ✓ Etapa criada: {etapa_id}")
        return etapa_id
        
    finally:
        conn.close()

def criar_solicitacao_piloto_equipe(etapa_id, equipe_id, equipe_nome):
    """Cria uma participação de tipo 'precisa_piloto' para uma equipe"""
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    
    try:
        participacao_id = str(uuid.uuid4())
        
        # Verificar se já existe
        cursor.execute('''
            SELECT id FROM participacoes_etapas
            WHERE etapa_id = %s AND equipe_id = %s
        ''', (etapa_id, equipe_id))
        
        if cursor.fetchone():
            print(f"   ! {equipe_nome}: já tem participação nesta etapa")
            return False
        
        cursor.execute('''
            INSERT INTO participacoes_etapas (id, etapa_id, equipe_id, tipo_participacao, status)
            VALUES (%s, %s, %s, 'precisa_piloto', 'inscrita')
        ''', (participacao_id, etapa_id, equipe_id))
        
        conn.commit()
        print(f"   ✓ Solicitação criada para: {equipe_nome}")
        return True
    except Exception as e:
        print(f"   ✗ Erro ao criar solicitação: {e}")
        return False
    finally:
        conn.close()

def inscrever_piloto_etapa(etapa_id, equipe_id, piloto_id, piloto_nome, equipe_nome):
    """Inscreve um piloto como candidato em uma etapa/equipe"""
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    
    try:
        candidato_id = str(uuid.uuid4())
        
        # Verificar se já é candidato
        cursor.execute('''
            SELECT id FROM candidatos_piloto_etapa
            WHERE etapa_id = %s AND equipe_id = %s AND piloto_id = %s
        ''', (etapa_id, equipe_id, piloto_id))
        
        if cursor.fetchone():
            return False  # Já é candidato
        
        cursor.execute('''
            INSERT INTO candidatos_piloto_etapa (id, etapa_id, equipe_id, piloto_id, status)
            VALUES (%s, %s, %s, %s, 'pendente')
        ''', (candidato_id, etapa_id, equipe_id, piloto_id))
        
        conn.commit()
        print(f"      ✓ {piloto_nome} inscrito em {equipe_nome}")
        return True
    except Exception as e:
        print(f"      ✗ Erro: {e}")
        return False
    finally:
        conn.close()

# ===== MAIN =====
print("\n" + "="*70)
print("🎮 TESTE - CRIAR PILOTOS E SOLICITAÇÕES")
print("="*70)

# 1. Criar 1 piloto inicial
print("\n1️⃣  Criando 1 piloto inicial...")
piloto_admin_id = str(uuid.uuid4())
criar_piloto(piloto_admin_id, "Admin Piloto Principal")

# 2. Obter equipes série A
print("\n2️⃣  Obtendo equipes série A...")
equipes_a = obter_equipes_serie_a()
print(f"   Encontradas {len(equipes_a)} equipes série A:")
for eq in equipes_a:
    print(f"   - {eq['nome']}")

if not equipes_a:
    print("   ❌ Nenhuma equipe série A encontrada!")
    exit(1)

# 3. Obter/criar etapa
print("\n3️⃣  Obtendo ou criando etapa...")
etapa_id = obter_ou_criar_etapa()

# 4. Criar solicitações "preciso_piloto" para todas as equipes série A
print(f"\n4️⃣  Criando solicitações 'preciso_piloto' para etapa {etapa_id}...")
for eq in equipes_a:
    criar_solicitacao_piloto_equipe(etapa_id, eq['id'], eq['nome'])

# 5. Criar 10 pilotos candidatos
print("\n5️⃣  Criando 10 pilotos candidatos...")
pilotos_ids = []
for i in range(1, 11):
    piloto_id = str(uuid.uuid4())
    piloto_nome = f"Piloto Teste {i}"
    criar_piloto(piloto_id, piloto_nome)
    pilotos_ids.append((piloto_id, piloto_nome))

# 6. Inscrever pilotos de forma aleatória nas equipes
print(f"\n6️⃣  Inscrevendo pilotos de forma aleatória nas equipes série A...")
print(f"   Total de pilotos: {len(pilotos_ids)}")
print(f"   Total de equipes: {len(equipes_a)}")

inscricoes_sucesso = 0
for piloto_id, piloto_nome in pilotos_ids:
    # Selecionar 2-4 equipes aleatórias para cada piloto
    num_equipes = random.randint(2, min(4, len(equipes_a)))
    equipes_selecionadas = random.sample(equipes_a, num_equipes)
    
    print(f"\n   📋 {piloto_nome}:")
    for eq in equipes_selecionadas:
        if inscrever_piloto_etapa(etapa_id, eq['id'], piloto_id, piloto_nome, eq['nome']):
            inscricoes_sucesso += 1

print("\n" + "="*70)
print(f"✅ RESUMO:")
print(f"   - Pilotos criados: 11 (1 admin + 10 candidatos)")
print(f"   - Equipes série A: {len(equipes_a)}")
print(f"   - Solicitações 'preciso_piloto': {len(equipes_a)}")
print(f"   - Inscrições realizadas: {inscricoes_sucesso}")
print("="*70 + "\n")
