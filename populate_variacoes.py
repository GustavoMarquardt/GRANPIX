#!/usr/bin/env python3
"""Script para popular variacoes_carros a partir de modelos_carro_loja"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mysql.connector
import uuid

# Conectar direto ao banco
config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'granpix'
}

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("POPULANDO variacoes_carros a partir de modelos_carro_loja")
    print("="*70)
    
    # 1. Ler todos os modelos
    cursor.execute('''
        SELECT id, marca, modelo, classe, preco, descricao
        FROM modelos_carro_loja
    ''')
    modelos = cursor.fetchall()
    
    print(f"\n[INFO] {len(modelos)} modelos encontrados")
    
    if len(modelos) == 0:
        print("[AVISO] Nenhum modelo cadastrado!")
        conn.close()
        sys.exit(1)
    
    # 2. Para cada modelo, criar uma variação padrão
    variacoes_criadas = 0
    for modelo_id, marca, modelo, classe, preco, descricao in modelos:
        variacao_id = str(uuid.uuid4())
        
        # Inserir variação com todas as peças NULL (padrão)
        cursor.execute('''
            INSERT INTO variacoes_carros 
            (id, modelo_carro_loja_id, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id)
            VALUES (%s, %s, NULL, NULL, NULL, NULL, NULL)
        ''', (variacao_id, modelo_id))
        
        variacoes_criadas += 1
        print(f"  ✓ {marca} {modelo} (Variação: Padrão)")
    
    conn.commit()
    print(f"\n[SUCESSO] {variacoes_criadas} variações criadas!")
    
    # 3. Listar resultado
    print("\n[INFO] Resumo de variações:")
    cursor.execute('''
        SELECT m.marca, m.modelo, COUNT(v.id) as variacao_count
        FROM modelos_carro_loja m
        LEFT JOIN variacoes_carros v ON m.id = v.modelo_carro_loja_id
        GROUP BY m.id
    ''')
    
    for marca, modelo, var_count in cursor.fetchall():
        print(f"  {marca} {modelo}: {var_count} variação(ões)")
    
    conn.close()
    print("\n" + "="*70 + "\n")
    
except Exception as e:
    print(f"[ERRO] {e}")
    import traceback
    traceback.print_exc()
