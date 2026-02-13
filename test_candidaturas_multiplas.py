#!/usr/bin/env python3
"""
Script para testar cenário de múltiplas candidaturas para uma equipe
"""
import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Importar direto do arquivo database.py
import importlib.util
spec = importlib.util.spec_from_file_location("database", os.path.join(os.path.dirname(__file__), 'src', 'database.py'))
database_module = importlib.util.module_from_spec(spec)

# Mock as imports relativas
import sys
from unittest.mock import MagicMock

# Criar mocks para os imports relativos
sys.modules['src.models'] = MagicMock()
sys.modules['src.mysql_utils'] = MagicMock()

from src.database import DatabaseManager
from datetime import datetime, timedelta
import random

def main():
    db = DatabaseManager()
    
    print("[TEST] Iniciando teste de múltiplas candidaturas...")
    
    # ===== 1. CRIAR 10 EQUIPES COM CARROS =====
    print("\n[TEST] Criando 10 equipes...")
    equipe_ids = []
    carro_ids = []
    
    for i in range(1, 11):
        equipe_id = f"equipe_teste_{i}"
        equipe_nome = f"Equipe Teste {i}"
        
        # Inserir equipe
        resultado = db.cadastrar_equipe(equipe_id, equipe_nome, "senha123", 1000000)
        print(f"  ✓ Equipe {i} criada: {equipe_nome}")
        equipe_ids.append(equipe_id)
        
        # Criar um carro para cada equipe
        carro_id = f"carro_teste_{i}"
        carro_nome = f"Carro Teste {i}"
        
        conn = db._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO carros (id, equipe_id, nome, modelo, placa, ano, serie)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (carro_id, equipe_id, carro_nome, "Modelo X", f"ABC{1000+i}", 2023, "A1"))
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"    → Carro criado: {carro_nome}")
        carro_ids.append((equipe_id, carro_id))
    
    # ===== 2. CRIAR 10 PILOTOS =====
    print("\n[TEST] Criando 10 pilotos...")
    piloto_ids = []
    
    for i in range(1, 11):
        piloto_id = f"piloto_teste_{i}"
        piloto_nome = f"Piloto Teste {i}"
        
        resultado = db.cadastrar_piloto(piloto_nome, "senha123")
        if resultado['sucesso']:
            piloto_ids.append((piloto_id, piloto_nome))
            print(f"  ✓ Piloto {i} criado: {piloto_nome}")
        else:
            # Se já existe, apenas usar o ID
            piloto_ids.append((piloto_id, piloto_nome))
            print(f"  ✓ Piloto {i} já existe: {piloto_nome}")
    
    # ===== 3. CRIAR UMA ETAPA =====
    print("\n[TEST] Criando uma etapa...")
    etapa_id = "etapa_teste_multiplas"
    
    # Data de amanhã
    data_etapa = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    hora_etapa = "14:00:00"
    
    conn = db._get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO etapas (id, campeonato_id, numero, nome, descricao, data_etapa, hora_etapa, serie, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (etapa_id, "campeonato_1", 1, "Etapa de Teste", "Etapa para teste de múltiplas candidaturas", data_etapa, hora_etapa, "A1", "agendada"))
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"  ✓ Etapa criada: {etapa_id}")
    print(f"    Data: {data_etapa} às {hora_etapa}")
    
    # ===== 4. INSCREVER EQUIPES NA ETAPA (tipo precisa_piloto) =====
    print("\n[TEST] Inscrevendo equipes na etapa (tipo: precisa_piloto)...")
    
    for idx, (equipe_id, carro_id) in enumerate(carro_ids):
        conn = db._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO participacoes_etapas (id, etapa_id, equipe_id, carro_id, piloto_id, tipo_participacao, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (f"part_teste_{idx+1}", etapa_id, equipe_id, carro_id, None, "precisa_piloto", "sem_piloto"))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"  ✓ Equipe {idx+1} inscrita (precisa_piloto)")
    
    # ===== 5. CENÁRIO DE MÚLTIPLAS CANDIDATURAS =====
    print("\n[TEST] === CENÁRIO DE MÚLTIPLAS CANDIDATURAS ===")
    print("\nEstrutura do teste:")
    print("  - Pilotos 1-5 se candidatam para EQUIPE 1 (Equipe Teste 1)")
    print("  - Pilotos 6-10 se candidatam para EQUIPES 2-10 (1 piloto por equipe)")
    
    # Pilotos 1-5 candidatam para Equipe 1
    print("\n[CANDIDATURAS] Pilotos 1-5 → Equipe Teste 1:")
    equipe_1_id = equipe_ids[0]
    
    for i in range(5):
        piloto_id, piloto_nome = piloto_ids[i]
        resultado = db.inscrever_piloto_candidato_etapa(etapa_id, equipe_1_id, piloto_id, piloto_nome)
        
        if resultado['sucesso']:
            print(f"  ✓ {piloto_nome} candidatado com sucesso")
        else:
            print(f"  ✗ {piloto_nome}: {resultado['erro']}")
    
    # Pilotos 6-10 candidatam para Equipes 2-10
    print("\n[CANDIDATURAS] Pilotos 6-10 → Equipes 2-10 (1 por equipe):")
    for i in range(5, 10):
        piloto_id, piloto_nome = piloto_ids[i]
        equipe_id = equipe_ids[i]  # Equipe i
        
        resultado = db.inscrever_piloto_candidato_etapa(etapa_id, equipe_id, piloto_id, piloto_nome)
        
        if resultado['sucesso']:
            equipe_idx = i + 1
            print(f"  ✓ {piloto_nome} → Equipe Teste {equipe_idx}")
        else:
            print(f"  ✗ {piloto_nome}: {resultado['erro']}")
    
    # ===== 6. SIMULAR CONFIRMAÇÃO DO PILOTO 1 PARA EQUIPE 1 =====
    print("\n[TEST] === SIMULANDO CONFIRMAÇÃO ===")
    print(f"\nPiloto 1 confirma participação para Equipe 1...")
    
    # Obter candidato_id do Piloto 1 para Equipe 1
    conn = db._get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT id, piloto_id FROM candidatos_piloto_etapa
        WHERE etapa_id = %s AND equipe_id = %s AND piloto_id = %s
    ''', (etapa_id, equipe_1_id, piloto_ids[0][0]))
    
    candidato = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if candidato:
        candidato_id = candidato['id']
        resultado = db.confirmar_candidatura_piloto_etapa(candidato_id, piloto_ids[0][0])
        
        if resultado['sucesso']:
            print(f"  ✓ Piloto 1 confirmado para Equipe 1!")
        else:
            print(f"  ✗ Erro: {resultado['erro']}")
    
    # ===== 7. TENTAR ADICIONAR MAIS CANDIDATOS PARA EQUIPE 1 =====
    print("\n[TEST] === TESTANDO RESTRIÇÃO (Equipe com piloto confirmado) ===")
    print(f"\nTentando candidatar Piloto 2 para Equipe 1 (que já tem piloto confirmado)...")
    
    resultado = db.inscrever_piloto_candidato_etapa(etapa_id, equipe_1_id, piloto_ids[1][0], piloto_ids[1][1])
    
    if resultado['sucesso']:
        print(f"  ✗ ERRO: Deveria ter bloqueado! {resultado['mensagem']}")
    else:
        print(f"  ✓ Bloqueado corretamente: {resultado['erro']}")
    
    # ===== 8. LISTAR ESTADO FINAL =====
    print("\n[TEST] === ESTADO FINAL DO BANCO DE DADOS ===")
    
    conn = db._get_conn()
    cursor = conn.cursor(dictionary=True)
    
    # Candidatos por equipe
    print("\n📋 Candidatos por Equipe:")
    cursor.execute('''
        SELECT e.nome as equipe, p.nome as piloto, c.status, c.id
        FROM candidatos_piloto_etapa c
        JOIN equipes e ON c.equipe_id = e.id
        JOIN pilotos p ON c.piloto_id = p.id
        WHERE c.etapa_id = %s
        ORDER BY e.nome, c.status DESC
    ''', (etapa_id,))
    
    resultado_query = cursor.fetchall()
    
    equipe_atual = None
    for row in resultado_query:
        if row['equipe'] != equipe_atual:
            equipe_atual = row['equipe']
            print(f"\n  {equipe_atual}:")
        
        status_icon = "✓" if row['status'] == 'confirmado' else "⏳" if row['status'] == 'designado' else "○"
        print(f"    {status_icon} {row['piloto']} ({row['status']})")
    
    cursor.close()
    conn.close()
    
    print("\n[TEST] ✅ Teste completado com sucesso!")
    print("\nAgora você pode:")
    print("  1. Acessar http://localhost:5000/campeonato")
    print("  2. Fazer login com os pilotos (nome/senha: Piloto Teste X / senha123)")
    print("  3. Ver a etapa de teste e as candidaturas")
    print("  4. Testar as confirmações e restrições")

if __name__ == '__main__':
    main()
