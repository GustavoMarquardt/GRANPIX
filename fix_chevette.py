import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor()

# ID do Chevette
carro_id = 'cf6acda4-06c5-40ea-9698-5603e62067de'

# IDs das peças corretas
ap_20_id = '5429d6c3-52cf-48aa-a2c7-0f22d27563bb'  # AP 2.0
gtrag_id = '2fd1a0e7-ed66-4272-9dc1-2d691c061dc1'  # GTRAG (câmbio)

# Deletar peças antigas do Chevette
cursor.execute('DELETE FROM pecas WHERE carro_id = %s', (carro_id,))
print(f'Deletadas peças antigas do Chevette')

# Inserir novas peças com ID único
# Motor AP 2.0
peca_motor_id = f"{carro_id}_{ap_20_id}"
cursor.execute('''
    INSERT INTO pecas 
    (id, carro_id, peca_loja_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
''', (peca_motor_id, carro_id, ap_20_id, 'ap 2.0', 'motor', 100.0, 100.0, 0.0, 1.0))
print(f'Motor AP 2.0 inserido com sucesso')

# Câmbio GTRAG
peca_cambio_id = f"{carro_id}_{gtrag_id}"
cursor.execute('''
    INSERT INTO pecas 
    (id, carro_id, peca_loja_id, nome, tipo, durabilidade_maxima, durabilidade_atual, preco, coeficiente_quebra, instalado)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
''', (peca_cambio_id, carro_id, gtrag_id, 'gtrag', 'cambio', 100.0, 100.0, 0.0, 1.0))
print(f'Câmbio GTRAG inserido com sucesso')

conn.commit()
conn.close()

print('\nChevette corrigido com sucesso!')
