import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', passwd='', db='granpix', charset='utf8mb4')
cursor = conn.cursor()

# Listar TODAS as peças por nome
print("TODAS AS PECAS EM pecas_loja:\n")
cursor.execute('SELECT id, nome, tipo, preco, data_criacao FROM pecas_loja ORDER BY nome, data_criacao DESC;')
pecas = cursor.fetchall()

peças_por_nome = {}
for id, nome, tipo, preco, data in pecas:
    if nome not in peças_por_nome:
        peças_por_nome[nome] = []
    peças_por_nome[nome].append({'id': id, 'tipo': tipo, 'preco': preco, 'data': data})

for nome in sorted(peças_por_nome.keys()):
    items = peças_por_nome[nome]
    if len(items) > 1:
        print(f"DUPLICADA - {nome}: {len(items)}x")
        for item in items:
            print(f"   ID: {item['id']}, Tipo: {item['tipo']}, Preco: {item['preco']}, Data: {item['data']}")
    else:
        item = items[0]
        print(f"OK - {nome}: ID: {item['id']}, Tipo: {item['tipo']}, Data: {item['data']}")

conn.close()
