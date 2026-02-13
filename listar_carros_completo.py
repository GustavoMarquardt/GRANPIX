import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor()

# Buscar carro com apelido TESÃO
cursor.execute('SELECT id, apelido, numero_carro, modelo, status, motor_id, cambio_id FROM carros ORDER BY numero_carro')
carros = cursor.fetchall()

print("TODOS OS CARROS NA EQUIPE:")
print("=" * 120)
for carro in carros:
    carro_id, apelido, numero, modelo, status, motor_id, cambio_id = carro
    print(f"ID: {carro_id}")
    print(f"  Apelido: {apelido}")
    print(f"  Número: {numero}, Modelo: {modelo}, Status: {status}")
    print(f"  Motor ID: {motor_id}, Câmbio ID: {cambio_id}")
    
    # Verificar peças instaladas na tabela pecas
    cursor.execute('''
        SELECT id, nome, tipo, instalado, carro_id
        FROM pecas WHERE carro_id = %s AND instalado = 1
    ''', (carro_id,))
    
    pecas = cursor.fetchall()
    if pecas:
        print(f"  Peças instaladas (instalado=1):")
        for peca in pecas:
            print(f"    - {peca[1]} (tipo: {peca[2]}, id: {peca[0]})")
    print()

conn.close()
