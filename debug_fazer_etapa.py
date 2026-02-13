#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor(dictionary=True)

# Buscar etapa em andamento
c.execute('''
    SELECT id FROM etapas WHERE status = "em_andamento" LIMIT 1
''')

etapa = c.fetchone()
if etapa:
    etapa_id = etapa['id']
    print(f"Etapa: {etapa_id[:8]}\n")
    
    # Verificar a query EXATAMENTE como está no fazer_etapa
    c.execute('''
        SELECT pe.piloto_id, pe.equipe_id, pe.ordem_qualificacao
        FROM participacoes_etapas pe
        WHERE pe.etapa_id COLLATE utf8mb4_unicode_ci = %s COLLATE utf8mb4_unicode_ci
        ORDER BY 
            CASE WHEN pe.ordem_qualificacao IS NULL THEN 1 ELSE 0 END,
            pe.ordem_qualificacao ASC
    ''', (etapa_id,))
    
    participacoes = c.fetchall()
    print("Query resultado (como retorna do MySQL):")
    for idx, p in enumerate(participacoes):
        print(f"  [idx={idx}] ordem={p['ordem_qualificacao']}, equipe={p['equipe_id'][:8]}")
    
    print("\nVoltas na tabela:")
    c.execute('''
        SELECT v.id_equipe, v.status, v.id_piloto,
               pe.ordem_qualificacao
        FROM volta v
        JOIN participacoes_etapas pe ON pe.piloto_id = v.id_piloto 
            AND pe.equipe_id = v.id_equipe
        WHERE v.id_etapa = %s
        ORDER BY pe.ordem_qualificacao
    ''', (etapa_id,))
    
    voltas = c.fetchall()
    for v in voltas:
        print(f"  QUAL {v['ordem_qualificacao']}: {v['id_equipe'][:8]} - status={v['status']}")

else:
    print("Nenhuma etapa em andamento")

c.close()
conn.close()
