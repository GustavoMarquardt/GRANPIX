import requests

# Testar a classificação final
resp = requests.get('http://localhost:5000/api/etapas/9ade8576-dec0-43d4-a056-8d2adf5924bc/classificacao-final')
if resp.status_code == 200:
    data = resp.json()
    print('Classificação final:')
    print('Sucesso:', data.get('sucesso'))
    if 'classificacao' in data:
        for i, equipe in enumerate(data['classificacao'][:3], 1):  # Mostrar top 3
            equipe_nome = equipe.get('equipe_nome', 'N/A')
            total = equipe.get('total_notas', 0)
            print(f'{i}. {equipe_nome} - Total: {total}')
else:
    print('Erro na API:', resp.status_code)
    print('Resposta:', resp.text)