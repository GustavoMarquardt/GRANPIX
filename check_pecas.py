import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor()

# Mostrar peças com compatibilidade como texto (não UUID)
cursor.execute('SELECT id, nome, compatibilidade FROM pecas_loja;')
pecas = cursor.fetchall()

print('PEÇAS ATUAIS:')
for id, nome, compatibilidade in pecas:
    print(f'  ID: {id}, Nome: {nome}, Compatibilidade: {compatibilidade}')
    # Verificar se é UUID válido
    if compatibilidade and len(compatibilidade) != 36:  # UUID tem 36 caracteres
        print(f'    ⚠️  COMPATIBILIDADE INVÁLIDA (não é UUID)')
    elif not compatibilidade:
        print(f'    ⚠️  COMPATIBILIDADE VAZIA')

# Mostrar modelos disponíveis
print('\nMODELOS DISPONÍVEIS:')
cursor.execute('SELECT id, marca, modelo FROM modelos_carro_loja;')
modelos = cursor.fetchall()
for id, marca, modelo in modelos:
    print(f'  ID: {id}, Modelo: {marca} {modelo}')

conn.close()
