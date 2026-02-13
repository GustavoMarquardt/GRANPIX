import requests

# Verificar se a API de etapas retorna o status correto
resp = requests.get('http://localhost:5000/api/loja/etapas')
if resp.status_code == 200:
    etapas = resp.json()
    print('Etapas encontradas:')
    for etapa in etapas:
        if etapa.get('id') == '9ade8576-dec0-43d4-a056-8d2adf5924bc':
            print(f'ID: {etapa["id"]}')
            print(f'Status: {etapa.get("status")}')
            print(f'Qualificação finalizada: {etapa.get("qualificacao_finalizada")}')
            break
else:
    print('Erro na API:', resp.status_code)