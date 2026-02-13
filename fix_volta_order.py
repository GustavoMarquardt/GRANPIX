#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor(dictionary=True)

# Encontrar etapa em andamento
c.execute('''
    SELECT id FROM etapas WHERE status = "em_andamento" LIMIT 1
''')

etapa = c.fetchone()
if etapa:
    etapa_id = etapa['id']
    print(f"Etapa em andamento: {etapa_id[:8]}")
    
    # Deletar todas as voltas dessa etapa
    c.execute('DELETE FROM volta WHERE id_etapa = %s', (etapa_id,))
    conn.commit()
    print("✓ Voltas antigas deletadas")
    
    # Recriar voltas na ordem correta
    c.execute('''
        SELECT pe.piloto_id, pe.equipe_id, pe.ordem_qualificacao
        FROM participacoes_etapas pe
        WHERE pe.etapa_id = %s
        ORDER BY 
            CASE WHEN pe.ordem_qualificacao IS NULL THEN 1 ELSE 0 END,
            pe.ordem_qualificacao ASC
    ''', (etapa_id,))
    
    participacoes = c.fetchall()
    print(f"\nRecriando {len(participacoes)} voltas na ordem correta:")
    
    for idx, part in enumerate(participacoes):
        piloto_id = part['piloto_id']
        equipe_id = part['equipe_id']
        status = 'em_andamento' if idx == 0 else 'agendada'
        
        c.execute('''
            INSERT INTO volta (id_piloto, id_equipe, id_etapa, status)
            VALUES (%s, %s, %s, %s)
        ''', (piloto_id, equipe_id, etapa_id, status))
        
        print(f"  {idx + 1}. QUAL {part['ordem_qualificacao']}: status={status}")
    
    conn.commit()
    print("\n✓ Voltas recriadas com sucesso na ordem correta!")
else:
    print("Nenhuma etapa em andamento encontrada")

c.close()
conn.close()
