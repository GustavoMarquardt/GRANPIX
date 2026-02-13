#!/usr/bin/env python3
from src.mysql_utils import get_connection

conn = get_connection()
c = conn.cursor(dictionary=True)

print("Alterando ENUM da coluna status...")

# Alterar o ENUM para novos valores
c.execute("""
    ALTER TABLE volta 
    MODIFY COLUMN status ENUM('andando', 'proximo', 'aguardando')
""")

conn.commit()
print("✓ ENUM atualizado para: 'andando', 'proximo', 'aguardando'")

# Agora resetar os valores
print("\nResetando voltascom novos status...")
c.execute("SELECT id FROM etapas WHERE status = 'em_andamento'")
etapas = c.fetchall()

for etapa in etapas:
    etapa_id = etapa['id']
    
    c.execute('''
        SELECT v.id, v.id_piloto, v.id_equipe, pe.ordem_qualificacao
        FROM volta v
        JOIN participacoes_etapas pe ON pe.piloto_id = v.id_piloto AND pe.equipe_id = v.id_equipe
        WHERE v.id_etapa = %s
        ORDER BY pe.ordem_qualificacao ASC
    ''', (etapa_id,))
    
    voltas = c.fetchall()
    
    for volta in voltas:
        ordem = volta['ordem_qualificacao']
        
        if ordem == 1:
            novo_status = 'andando'
        elif ordem == 2:
            novo_status = 'proximo'
        else:
            novo_status = 'aguardando'
        
        c.execute('UPDATE volta SET status=%s WHERE id=%s', (novo_status, volta['id']))
        print(f"  Volta QUAL {ordem}: status = {novo_status}")

conn.commit()
print("\n✓ Voltas atualizadas com sucesso!")

c.close()
conn.close()
