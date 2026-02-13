import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor(buffered=True)

print("=" * 100)
print("LIMPEZA E SINCRONIZAÇÃO DO BANCO DE DADOS")
print("=" * 100)

# 1. Buscar todos os carros
cursor.execute('SELECT id, numero_carro, apelido, modelo, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id FROM carros')
carros = cursor.fetchall()

for carro in carros:
    carro_id, numero, apelido, modelo, motor_id, cambio_id, suspensao_id, kit_angulo_id, diferencial_id = carro
    print(f"\n[CARRO {numero}] {apelido or 'Sem apelido'} ({modelo})")
    
    # Mapear tipos de peças para IDs da tabela carros
    tipo_to_id = {
        'motor': motor_id,
        'cambio': cambio_id,
        'suspensao': suspensao_id,
        'kit_angulo': kit_angulo_id,
        'diferencial': diferencial_id
    }
    
    # Para cada tipo de peça esperada
    for tipo, peca_loja_id in tipo_to_id.items():
        if peca_loja_id and peca_loja_id.strip():  # Se tem um ID
            print(f"  [{tipo}] ID: {peca_loja_id}")
            
            # Criar novo cursor para cada query
            cursor2 = conn.cursor(buffered=True)
            cursor2.execute('''
                SELECT id, peca_loja_id, nome 
                FROM pecas 
                WHERE carro_id = %s AND tipo = %s AND instalado = 1
            ''', (carro_id, tipo))
            
            peca = cursor2.fetchone()
            cursor2.close()
            
            if peca:
                peca_id, peca_loja_atual, nome = peca
                
                # Verificar se o peca_loja_id está correto
                if peca_loja_atual != peca_loja_id:
                    print(f"    ⚠️ CORRIGINDO peca_loja_id")
                    cursor3 = conn.cursor(buffered=True)
                    cursor3.execute('''
                        UPDATE pecas SET peca_loja_id = %s WHERE id = %s
                    ''', (peca_loja_id, peca_id))
                    cursor3.close()
                    conn.commit()
                else:
                    print(f"    ✓ OK - {nome}")
            else:
                print(f"    ⚠️ NENHUMA peça {tipo} instalada!")

conn.close()

print("\n" + "=" * 100)
print("SINCRONIZAÇÃO CONCLUÍDA")
print("=" * 100)
