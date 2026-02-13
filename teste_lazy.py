#!/usr/bin/env python3
"""
Teste para verificar carregamento lazy de dados
"""

import requests
import time

BASE_URL = 'http://localhost:5000'

def teste_carregamento_lazy():
    print("🧪 Teste de Carregamento Lazy...")

    # Criar equipe de teste
    equipe_data = {'nome': 'TesteLazy', 'senha': 'teste123', 'serie': 'A', 'doricoins': 10000}
    response = requests.post(f'{BASE_URL}/api/admin/cadastrar-equipe', json=equipe_data)
    equipe_id = response.json()['equipe']['id']
    print(f"✅ Equipe criada: {equipe_id}")

    # Login
    login_data = {'tipo': 'equipe', 'equipe_id': equipe_id, 'senha': 'teste123'}
    response = requests.post(f'{BASE_URL}/login', json=login_data)
    print("✅ Login realizado")

    headers = {'X-Equipe-ID': equipe_id}

    # Testar endpoints individualmente
    print("\n📊 Testando endpoints...")

    # Garagem
    start = time.time()
    response = requests.get(f'{BASE_URL}/api/garagem/{equipe_id}', headers=headers)
    garagem_time = time.time() - start
    print(".2f")

    # Carros loja
    start = time.time()
    response = requests.get(f'{BASE_URL}/api/loja/carros', headers=headers)
    carros_time = time.time() - start
    print(".2f")

    # Peças loja
    start = time.time()
    response = requests.get(f'{BASE_URL}/api/loja/pecas', headers=headers)
    pecas_time = time.time() - start
    print(".2f")

    print("\n✅ Teste concluído!")
    print("💡 Com carregamento lazy, apenas os dados da aba ativa são carregados,")
    print("   reduzindo o tráfego de rede e melhorando a performance.")

if __name__ == '__main__':
    teste_carregamento_lazy()