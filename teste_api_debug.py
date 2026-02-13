import mysql.connector
import json
import requests
import time

# Conectar ao banco
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='granpix'
)
cursor = conn.cursor(dictionary=True)

# Ver etapas
cursor.execute('SELECT id, nome, qualificacao_finalizada FROM etapas ORDER BY id')
etapas = cursor.fetchall()

print('Etapas encontradas:')
for etapa in etapas:
    print(f'ID: {etapa["id"]}, Nome: {etapa["nome"]}, Finalizada: {etapa["qualificacao_finalizada"]}')

if etapas:
    etapa_id = etapas[0]['id']
    print(f'\nTestando API com etapa ID {etapa_id}...')

    time.sleep(1)

    resp = requests.get(f'http://localhost:5000/api/etapas/{etapa_id}/evento')
    if resp.status_code == 200:
        data = resp.json()
        if 'evento' in data and 'etapa' in data['evento']:
            etapa = data['evento']['etapa']
            print('qualificacao_finalizada na API:', etapa.get('qualificacao_finalizada'))
            print('Tipo:', type(etapa.get('qualificacao_finalizada')))
        else:
            print('Estrutura da resposta:', json.dumps(data, indent=2))
    else:
        print('Erro na API:', resp.status_code)

cursor.close()
conn.close()