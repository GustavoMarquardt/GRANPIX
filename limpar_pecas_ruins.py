import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor(buffered=True)

print("=" * 100)
print("LIMPEZA DE PEÇAS COM peca_loja_id INVÁLIDO")
print("=" * 100)

# Buscar peças com peca_loja_id que parecem IDs de carro concatenados
cursor.execute('''
    SELECT id, carro_id, nome, tipo, peca_loja_id
    FROM pecas
    WHERE peca_loja_id LIKE '%_%_%_%_%' AND LENGTH(peca_loja_id) > 50
''')

pecas_ruins = cursor.fetchall()

print(f"\nEncontradas {len(pecas_ruins)} peças com peca_loja_id inválido:")

for peca_id, carro_id, nome, tipo, peca_loja_id in pecas_ruins:
    print(f"\n  ID: {peca_id[:30]}...")
    print(f"  Nome: {nome}")
    print(f"  Tipo: {tipo}")
    print(f"  Carro ID: {carro_id[:30]}...")
    print(f"  Peca Loja ID (INVÁLIDO): {peca_loja_id[:50]}...")
    
    # Deletar peça ruim
    print(f"  ⚠️ DELETANDO...")
    cursor2 = conn.cursor(buffered=True)
    cursor2.execute('DELETE FROM pecas WHERE id = %s', (peca_id,))
    cursor2.close()
    conn.commit()

print("\n" + "=" * 100)
print("LIMPEZA CONCLUÍDA")
print("=" * 100)

conn.close()
