#!/usr/bin/env python3
"""
Teste de compra simples
"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def teste_compra():
    print("🛒 Teste de compra...")

    # Criar equipe
    equipe_data = {
        'nome': 'TesteCompraSimples',
        'senha': 'teste123',
        'serie': 'A',
        'doricoins': 50000
    }

    response = requests.post(f'{BASE_URL}/api/admin/cadastrar-equipe', json=equipe_data)
    equipe_id = response.json()['equipe']['id']
    print(f"✅ Equipe criada: {equipe_id}")

    # Login
    login_data = {'tipo': 'equipe', 'equipe_id': equipe_id, 'senha': 'teste123'}
    response = requests.post(f'{BASE_URL}/login', json=login_data)
    print(f"✅ Login realizado")

    # Verificar garagem inicial
    headers = {'X-Equipe-ID': equipe_id}
    response = requests.get(f'{BASE_URL}/api/garagem/{equipe_id}', headers=headers)
    garagem = response.json()
    print(f"📊 Garagem inicial: {len(garagem['carros'])} carros")

    # Obter carros da loja
    response = requests.get(f'{BASE_URL}/api/loja/carros', headers=headers)
    carros_loja = response.json()
    print(f"🏪 Loja: {len(carros_loja)} carros disponíveis")

    if carros_loja:
        # Pegar primeiro carro
        carro = carros_loja[0]
        carro_id = carro['id']
        variacao_id = carro.get('variacoes', [{}])[0].get('id') if carro.get('variacoes') else None

        print(f"🛒 Comprando: {carro['marca']} {carro['modelo']}")

        # Comprar carro
        compra_data = {'tipo': 'carro', 'item_id': carro_id}
        if variacao_id:
            compra_data['variacao_id'] = variacao_id

        response = requests.post(f'{BASE_URL}/api/comprar', json=compra_data, headers=headers)
        if response.status_code == 200:
            print("✅ Carro comprado com sucesso!")

            # Verificar garagem após compra
            response = requests.get(f'{BASE_URL}/api/garagem/{equipe_id}', headers=headers)
            garagem = response.json()
            print(f"📊 Garagem após compra: {len(garagem['carros'])} carros")

            for carro in garagem['carros']:
                pecas = carro.get('pecas_instaladas', [])
                print(f"   🚗 {carro['marca']} {carro['modelo']}: {len(pecas)} peças instaladas")

            # Obter peças da loja
            response = requests.get(f'{BASE_URL}/api/loja/pecas', headers=headers)
            pecas_loja = response.json()
            print(f"🔧 Loja: {len(pecas_loja)} peças disponíveis")

            if pecas_loja:
                # Comprar primeira peça
                peca = pecas_loja[0]
                peca_id = peca['id']
                carro_id_instalar = garagem['carros'][0]['id']

                print(f"🛠️ Comprando peça: {peca['nome']} ({peca['tipo']})")

                compra_data = {
                    'tipo': 'peca',
                    'item_id': peca_id,
                    'carro_id': carro_id_instalar
                }

                response = requests.post(f'{BASE_URL}/api/comprar', json=compra_data, headers=headers)
                if response.status_code == 200:
                    print("✅ Peça comprada e instalada!")

                    # Verificar garagem final
                    response = requests.get(f'{BASE_URL}/api/garagem/{equipe_id}', headers=headers)
                    garagem = response.json()
                    print("📊 Garagem final:")
                    print(f"   Carros: {len(garagem['carros'])}")
                    print(f"   Peças no armazém: {len(garagem.get('armazem', {}).get('pecas_guardadas', []))}")

                    for carro in garagem['carros']:
                        pecas = carro.get('pecas_instaladas', [])
                        print(f"   🚗 {carro['marca']} {carro['modelo']}: {len(pecas)} peças")
                        for peca in pecas:
                            print(f"      ✓ {peca['nome']} ({peca['tipo']})")

                    print("🎉 Teste concluído com sucesso!")
                else:
                    print(f"❌ Erro ao comprar peça: {response.text}")
        else:
            print(f"❌ Erro ao comprar carro: {response.text}")

if __name__ == '__main__':
    teste_compra()