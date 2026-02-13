#!/usr/bin/env python3
"""Debug script para verificar candidatos piloto com equipe_nome undefined"""

import sys
import os
sys.path.insert(0, r'c:\Users\Gustavo Marquardt\Documents\GRANPIX')
os.chdir(r'c:\Users\Gustavo Marquardt\Documents\GRANPIX')

# Adicione à PYTHONPATH os diretórios necessários
from app import app, api

# Usar o contexto do app
with app.app_context():
    db = api.db
    
    # Listar todas as etapas
    print("=" * 80)
    print("LISTANDO ETAPAS:")
    print("=" * 80)
    try:
        conn = db._get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nome FROM etapas LIMIT 10")
        etapas = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for etapa in etapas:
            print(f"  - {etapa['id']}: {etapa['nome']}")
    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

    # Para cada etapa, buscar candidatos com debug
    print("\n" + "=" * 80)
    print("VERIFICANDO CANDIDATOS POR ETAPA:")
    print("=" * 80)

    try:
        conn = db._get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM etapas LIMIT 1")
        etapa = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if etapa:
            etapa_id = etapa['id']
            print(f"\nEtapa: {etapa_id}")
            print("-" * 80)
            
            # Buscar candidatos usando a função do DB
            candidatos_agrupados = db.obter_candidatos_piloto_etapa(etapa_id)
            
            print(f"Total de grupos de equipe: {len(candidatos_agrupados)}")
            
            for grupo in candidatos_agrupados:
                print(f"\nGrupo Equipe:")
                print(f"  - equipe_id: {grupo.get('equipe_id')}")
                print(f"  - equipe_nome: {grupo.get('equipe_nome')} {'⚠️ UNDEFINED!' if grupo.get('equipe_nome') is None else '✓'}")
                print(f"  - tipo_participacao: {grupo.get('tipo_participacao')}")
                print(f"  - candidatos: {len(grupo.get('candidatos', []))}")
                for idx, c in enumerate(grupo.get('candidatos', []), 1):
                    print(f"    {idx}. {c.get('piloto_nome')} (status: {c.get('status')})")

    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

    # Verificar equipes com candidatos pendentes
    print("\n" + "=" * 80)
    print("EQUIPES COM CANDIDATOS PENDENTES:")
    print("=" * 80)

    try:
        conn = db._get_conn()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT DISTINCT
                cpe.etapa_id,
                cpe.equipe_id,
                e.nome as equipe_nome,
                COUNT(cpe.id) as total_candidatos
            FROM candidatos_piloto_etapa cpe
            LEFT JOIN equipes e ON cpe.equipe_id = e.id
            WHERE cpe.status = 'pendente'
            GROUP BY cpe.etapa_id, cpe.equipe_id, e.nome
            ORDER BY cpe.etapa_id, e.nome
        ''')
        
        equipes = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if equipes:
            for eq in equipes:
                print(f"\nEtapa: {eq['etapa_id']}")
                print(f"  Equipe: {eq['equipe_nome'] or 'UNDEFINED'} {'⚠️' if eq['equipe_nome'] is None else '✓'}")
                print(f"  Total candidatos pendentes: {eq['total_candidatos']}")
        else:
            print("Nenhuma equipe com candidatos pendentes")

    except Exception as e:
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
