#!/usr/bin/env python3
"""Debug script para verificar o erro ao alocar piloto"""

import sys
import os
sys.path.insert(0, r'c:\Users\Gustavo Marquardt\Documents\GRANPIX')
os.chdir(r'c:\Users\Gustavo Marquardt\Documents\GRANPIX')

from app import app, api

with app.app_context():
    # Testar a query
    conn = api.db._get_conn()
    cursor = conn.cursor(dictionary=True)
    
    # Ver se há participações_etapas
    cursor.execute('SELECT * FROM participacoes_etapas LIMIT 10')
    participacoes = cursor.fetchall()
    
    print('Participações Etapas:')
    for p in participacoes:
        print(f'  Etapa: {p.get("etapa_id")}, Equipe: {p.get("equipe_id")}, Piloto: {p.get("piloto_id")}, Status: {p.get("status")}, Tipo: {p.get("tipo_participacao")}')
    
    # Ver candidatos_piloto_etapa
    print('\n\nCandidatos Piloto Etapa:')
    cursor.execute('SELECT * FROM candidatos_piloto_etapa LIMIT 10')
    candidatos = cursor.fetchall()
    
    for c in candidatos:
        print(f'  Candidato: {c.get("id")}, Etapa: {c.get("etapa_id")}, Equipe: {c.get("equipe_id")}, Piloto: {c.get("piloto_id")}, Status: {c.get("status")}')
    
    # Testes com dados específicos
    etapa_id = '542612d0-40e1-4f72-9558-ca332d9444d8'
    equipe_id = '2b3f99ac-407e-4650-a559-6971ced6ee89'
    
    # Buscar o piloto correto do candidato
    cursor.execute('''
        SELECT piloto_id FROM candidatos_piloto_etapa
        WHERE etapa_id = %s AND equipe_id = %s AND status = 'pendente'
        LIMIT 1
    ''', (etapa_id, equipe_id))
    
    candidato_row = cursor.fetchone()
    if candidato_row:
        piloto_id = candidato_row.get('piloto_id')
    else:
        piloto_id = None
    
    print(f'\n\nTestando alocação:')
    print(f'  Etapa: {etapa_id}')
    print(f'  Equipe: {equipe_id}')
    print(f'  Piloto: {piloto_id}')
    
    # Verificar se participação existe
    cursor.execute('''
        SELECT * FROM participacoes_etapas
        WHERE etapa_id = %s AND equipe_id = %s
    ''', (etapa_id, equipe_id))
    
    participacao = cursor.fetchone()
    if participacao:
        print(f'\n  Participação encontrada:')
        print(f'    ID: {participacao.get("id")}')
        print(f'    Status: {participacao.get("status")}')
        print(f'    Piloto ID: {participacao.get("piloto_id")}')
        print(f'    Tipo: {participacao.get("tipo_participacao")}')
    else:
        print(f'\n  ❌ Participação NÃO encontrada!')
    
    # Tentar executar a alocação
    print(f'\n\nTentando alocar...')
    resultado = api.db.alocar_piloto_reserva_para_equipe(etapa_id, equipe_id, piloto_id)
    print(f'Resultado: {resultado}')
    
    # Verificar se foi alocado
    cursor.execute('''
        SELECT piloto_id FROM participacoes_etapas
        WHERE etapa_id = %s AND equipe_id = %s
    ''', (etapa_id, equipe_id))
    
    participacao_atualizada = cursor.fetchone()
    print(f'\nVerificacao pos-alocacao:')
    print(f'  Piloto ID na participacao: {participacao_atualizada.get("piloto_id")}')
    
    cursor.close()
    conn.close()
