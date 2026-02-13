#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test script for campeonato functionality"""

import json
import sys
sys.path.insert(0, r'c:\Users\Gustavo Marquardt\Documents\GRANPIX')

from src.database import DatabaseManager
import uuid

db = DatabaseManager()

print("\n" + "="*60)
print("TESTE DO SISTEMA DE CAMPEONATOS")
print("="*60)

# Test 1: Criar campeonato
print("\n[TEST 1] Criando campeonato...")
try:
    camp1 = db.criar_campeonato(
        nome="Campeonato Test 2025",
        descricao="Teste do sistema",
        serie="A",
        numero_etapas=5
    )
    print(f"✅ Campeonato criado: {camp1}")
except Exception as e:
    print(f"❌ Erro ao criar campeonato: {e}")
    camp1 = None

# Test 2: Listar campeonatos
print("\n[TEST 2] Listando campeonatos...")
try:
    campeonatos = db.listar_campeonatos()
    print(f"✅ {len(campeonatos)} campeonatos encontrados:")
    for c in campeonatos:
        print(f"   - {c['nome']} (Série {c['serie']}): {c['numero_etapas']} etapas")
except Exception as e:
    print(f"❌ Erro ao listar campeonatos: {e}")

# Test 3: Obter campeonato específico
if camp1:
    print(f"\n[TEST 3] Obtendo campeonato {camp1}...")
    try:
        campeonato = db.obter_campeonato(camp1)
        print(f"✅ Campeonato obtido: {campeonato['nome']} - {campeonato['numero_etapas']} etapas")
    except Exception as e:
        print(f"❌ Erro ao obter campeonato: {e}")

# Test 4: Deletar campeonato
if camp1:
    print(f"\n[TEST 4] Deletando campeonato {camp1}...")
    try:
        resultado = db.deletar_campeonato(camp1)
        print(f"✅ Campeonato deletado: {resultado}")
    except Exception as e:
        print(f"❌ Erro ao deletar campeonato: {e}")

# Test 5: Criar etapa com campeonato
print("\n[TEST 5] Criando etapa com campeonato...")
try:
    # Primeiro criar um novo campeonato
    camp2 = db.criar_campeonato(
        nome="Campeonato com Etapas",
        descricao="Para testar etapas",
        serie="B",
        numero_etapas=3
    )
    print(f"   Campeonato criado: {camp2}")
    
    # Agora criar uma etapa associada
    etapa_id = db.cadastrar_etapa(
        campeonato_id=camp2,
        numero=1,
        nome="Etapa 1 - Teste",
        descricao="Primeira etapa",
        data_etapa="2025-03-01",
        hora_etapa="10:00:00",
        serie="B"
    )
    print(f"✅ Etapa criada: {etapa_id}")
except Exception as e:
    print(f"❌ Erro ao criar etapa: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("TESTES CONCLUÍDOS")
print("="*60)
