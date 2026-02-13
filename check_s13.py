import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor()

# Buscar carro s13 (número 1)
cursor.execute('SELECT id, apelido, numero_carro, modelo, motor_id, cambio_id, suspensao_id, kit_angulo_id FROM carros WHERE numero_carro = 1')
carro = cursor.fetchone()

if carro:
    carro_id = carro[0]
    print("=" * 100)
    print(f"CARRO: {carro[1] or 'Sem apelido'} - Número: {carro[2]} - Modelo: {carro[3]}")
    print("=" * 100)
    print(f"Motor ID: {carro[4]}")
    print(f"Câmbio ID: {carro[5]}")
    print(f"Suspensão ID: {carro[6]}")
    print(f"Kit Ângulo ID: {carro[7]}")
    
    print("\n[TABELA PECAS - instalado=1]:")
    cursor.execute('''
        SELECT id, nome, tipo, carro_id, instalado, peca_loja_id
        FROM pecas WHERE carro_id = %s AND instalado = 1
        ORDER BY tipo
    ''', (carro_id,))
    
    pecas = cursor.fetchall()
    for peca in pecas:
        print(f"  ID: {peca[0][:30]}...")
        print(f"    Nome: {peca[1]}")
        print(f"    Tipo: {peca[2]}")
        print(f"    Carro ID: {peca[3][:30]}...")
        print(f"    Peca Loja ID: {peca[5]}")
    
    print("\n[PEÇAS ORPHANED - carro_id IS NULL, instalado=0]:")
    cursor.execute('''
        SELECT id, nome, tipo, peca_loja_id, instalado
        FROM pecas WHERE carro_id IS NULL AND instalado = 0
        LIMIT 10
    ''')
    
    orphan = cursor.fetchall()
    if orphan:
        for peca in orphan:
            print(f"  Nome: {peca[1]} | Tipo: {peca[2]} | Loja ID: {peca[3]} | Instalado: {peca[4]}")
    else:
        print("  Nenhuma peça orphaned")

conn.close()
