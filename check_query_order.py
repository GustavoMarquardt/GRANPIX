#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor(dictionary=True)

# Carregando uma etapa com dados
c.execute('''
    SELECT id FROM etapas WHERE status = "em_andamento" LIMIT 1
''')

etapa = c.fetchone()
if not etapa:
    print("Nenhuma etapa em andamento encontrada. Buscando qualquer etapa...")
    c.execute('SELECT id FROM etapas LIMIT 1')
    etapa = c.fetchone()

if etapa:
    etapa_id = etapa['id']
    print(f"Etapa ID: {etapa_id}")
    
    # Executar a query de busca de participações
    c.execute('''
        SELECT pe.piloto_id, pe.equipe_id, pe.ordem_qualificacao
        FROM participacoes_etapas pe
        WHERE pe.etapa_id = %s
        ORDER BY 
            CASE WHEN pe.ordem_qualificacao IS NULL THEN 1 ELSE 0 END,
            pe.ordem_qualificacao ASC
    ''', (etapa_id,))
    
    rows = c.fetchall()
    print(f"\nParticipações para etapa {etapa_id[:8]}:")
    for i, row in enumerate(rows, 1):
        print(f"  {i}. ordem_qualificacao={row['ordem_qualificacao']}, equipe={row['equipe_id'][:8]}")
else:
    print("Nenhuma etapa encontrada!")

c.close()
conn.close()
