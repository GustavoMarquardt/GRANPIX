#!/usr/bin/env python3
"""
Teste simplificado para verificar associações de peças
"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def teste_basico():
    print("🔍 Teste básico do sistema...")

    # Verificar se servidor está funcionando
    try:
        response = requests.get(f'{BASE_URL}/')
        print(f"✅ Servidor responde: {response.status_code}")
    except Exception as e:
        print(f"❌ Servidor não responde: {e}")
        return

    # Criar equipe de teste
    equipe_data = {
        'nome': 'TestePecas',
        'senha': 'teste123',
        'serie': 'A',
        'doricoins': 10000
    }

    try:
        response = requests.post(f'{BASE_URL}/api/admin/cadastrar-equipe', json=equipe_data)
        if response.status_code == 200:
            result = response.json()
            equipe_id = result['equipe']['id']
            print(f"✅ Equipe criada: {equipe_id}")

            # Verificar garagem vazia
            headers = {'X-Equipe-ID': equipe_id}
            response = requests.get(f'{BASE_URL}/api/garagem/{equipe_id}', headers=headers)
            if response.status_code == 200:
                garagem = response.json()
                carros = garagem.get('carros', [])
                print(f"✅ Garagem inicial: {len(carros)} carros")

                # Verificar se há carros inesperados
                if len(carros) > 0:
                    print("⚠️  AVISO: Equipe nova já tem carros!")
                    for carro in carros:
                        print(f"   - {carro.get('marca')} {carro.get('modelo')} (ID: {carro.get('id')})")
                else:
                    print("✅ Garagem está vazia como esperado")

            # Testar obtenção de carros da loja
            response = requests.get(f'{BASE_URL}/api/loja/carros', headers=headers)
            if response.status_code == 200:
                carros_loja = response.json()
                print(f"✅ Loja tem {len(carros_loja)} carros disponíveis")
            else:
                print(f"❌ Erro ao obter carros da loja: {response.status_code}")

        else:
            print(f"❌ Erro ao criar equipe: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ Erro durante teste: {e}")

if __name__ == '__main__':
    teste_basico()