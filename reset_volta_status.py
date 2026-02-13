#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor(dictionary=True)

# Buscar todas as etapas em andamento
c.execute('SELECT id FROM etapas WHERE status = "em_andamento"')
etapas = c.fetchall()

if not etapas:
    print("Nenhuma etapa em andamento")
    c.close()
    conn.close()
    exit()

for etapa in etapas:
    etapa_id = etapa['id']
    print(f"\n=== Resetando etapa {etapa_id[:8]} ===")
    
    # Buscar todas as voltas dessa etapa e ordenar por ordem_qualificacao
    c.execute('''
        SELECT v.id, v.id_piloto, v.id_equipe, pe.ordem_qualificacao
        FROM volta v
        JOIN participacoes_etapas pe ON pe.piloto_id = v.id_piloto AND pe.equipe_id = v.id_equipe
        WHERE v.id_etapa = %s
        ORDER BY pe.ordem_qualificacao ASC
    ''', (etapa_id,))
    
    voltas = c.fetchall()
    
    for idx, volta in enumerate(voltas):
        ordem = volta['ordem_qualificacao']
        
        # Determinar novo status: 1º=andando, 2º=próximo, demais=aguardando
        if ordem == 1:
            novo_status = 'andando'
        elif ordem == 2:
            novo_status = 'proximo'
        else:
            novo_status = 'aguardando'
        
        c.execute('UPDATE volta SET nota_linha=0, nota_angulo=0, nota_estilo=0, status=%s WHERE id=%s',
                 (novo_status, volta['id']))
        print(f"  Volta {ordem}: status = {novo_status}, notas resetadas")
    
    conn.commit()

print("\n✓ Resetado com sucesso!")
c.close()
conn.close()
